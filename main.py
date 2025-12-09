import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

import requests
from dateutil import parser as date_parser
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from config import get_project_catalog

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ------------------------------------------------------------------------------
# 配置
# ------------------------------------------------------------------------------
# 项目清单（可通过 WEATHER_PROJECTS_JSON / WEATHER_PROJECTS_FILE 覆盖）
PROJECT_CATALOG: List[Dict[str, Any]] = get_project_catalog()

logger.info("使用Open-Meteo作为历史天气数据源（完全免费，无需API Key）")

# ------------------------------------------------------------------------------
# 数据模型
# ------------------------------------------------------------------------------
class HistoryItem(BaseModel):
    timestamp: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None  # 0~1
    wind_speed: Optional[float] = None
    cloud: Optional[float] = None
    real_time_irradiance: Optional[float] = None
    daily_avg_irradiance: Optional[float] = None
    horizontal_irradiance: Optional[float] = None
    tilted_irradiance: Optional[float] = None
    sunshine: Optional[float] = None  # 简易日照度（1 - cloud/100）


class HistoryResponse(BaseModel):
    location: str
    date: str
    count: int
    items: List[HistoryItem]
    daily_avg_irradiance: Optional[float] = None


# ------------------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------------------
def _find_project(project_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not project_id:
        return None
    pid = str(project_id)
    for p in PROJECT_CATALOG:
        if str(p.get("project_id")) == pid or p.get("name") == project_id:
            return p
    return None


def _ensure_latitude_longitude(
    latitude: Optional[float],
    longitude: Optional[float],
    project: Optional[Dict[str, Any]]
) -> Tuple[float, float]:
    """
    确保有有效的经纬度（Open-Meteo需要经纬度）
    优先级：直接提供的经纬度 > 项目配置的经纬度
    """
    lat = latitude
    lon = longitude
    
    if lat is None or lon is None:
        if project:
            lat = project.get("latitude")
            lon = project.get("longitude")
    
    if lat is None or lon is None:
        raise HTTPException(
            status_code=400,
            detail="必须提供经纬度信息（latitude和longitude）。可以通过project_id自动获取，或直接提供latitude和longitude参数。"
        )
    
    return float(lat), float(lon)


def _fetch_history_from_openmeteo(
    latitude: float,
    longitude: float,
    date_str: str
) -> List[Dict[str, Any]]:
    """
    使用Open-Meteo获取历史天气数据（完全免费，无需API Key）
    
    参数:
        latitude: 纬度
        longitude: 经度
        date_str: 日期字符串，格式 YYYY-MM-DD
    
    返回:
        格式化的历史天气数据列表
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date_str,
        "end_date": date_str,
        "hourly": "temperature_2m,relative_humidity_2m,windspeed_10m,cloudcover,shortwave_radiation",
        "timezone": "Asia/Shanghai",
    }
    
    logger.info(f"调用Open-Meteo API: url={url}, latitude={latitude}, longitude={longitude}, date={date_str}")
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Open-Meteo API请求失败: {e}")
        raise Exception(f"Open-Meteo API请求失败: {str(e)}")
    except Exception as e:
        logger.error(f"Open-Meteo API响应解析失败: {e}")
        raise Exception(f"Open-Meteo API响应解析失败: {str(e)}")
    
    # 检查是否有错误
    if "error" in data:
        error_msg = data.get("error", "Unknown error")
        logger.error(f"Open-Meteo API返回错误: {error_msg}")
        raise Exception(f"Open-Meteo API错误: {error_msg}")
    
    hourly = data.get("hourly", {})
    if not hourly:
        logger.warning("Open-Meteo API返回空数据")
        return []
    
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    hums = hourly.get("relative_humidity_2m", [])
    winds = hourly.get("windspeed_10m", [])
    clouds = hourly.get("cloudcover", [])
    radiations = hourly.get("shortwave_radiation", [])
    
    result = []
    for i, time_str in enumerate(times):
        # 转换时间格式为ISO格式（UTC+8时区）
        try:
            # Open-Meteo返回的时间格式：2024-11-28T00:00
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            # 转换为UTC+8时区
            dt_local = dt.astimezone(timezone(timedelta(hours=8)))
            fx_time = dt_local.isoformat()
        except Exception:
            fx_time = time_str
        
        result.append({
            "fxTime": fx_time,
            "obsTime": fx_time,  # 兼容字段
            "temp": temps[i] if i < len(temps) and temps[i] is not None else None,
            "humidity": (hums[i] * 100) if i < len(hums) and hums[i] is not None else None,  # 转换为百分比
            "windSpeed": winds[i] if i < len(winds) and winds[i] is not None else None,
            "cloud": clouds[i] if i < len(clouds) and clouds[i] is not None else None,
            "shortwave_radiation": radiations[i] if i < len(radiations) and radiations[i] is not None else None,
        })
    
    logger.info(f"Open-Meteo API返回 {len(result)} 条历史天气数据")
    return result


def _estimate_irradiance(shortwave_radiation: Optional[float], hour_local: int, cloud: Optional[float] = None) -> float:
    """
    辐照度估算：
    - 优先使用Open-Meteo提供的shortwave_radiation（短波辐射）
    - 如果不可用，使用简易估算：仅在 6~18 点有辐照度，基准 1000 W/m2，按云量折减
    """
    # 优先使用Open-Meteo提供的短波辐射数据
    if shortwave_radiation is not None and shortwave_radiation >= 0:
        return float(shortwave_radiation)
    
    # 降级到简易估算（通常不会用到，因为Open-Meteo总是提供shortwave_radiation）
    if hour_local < 6 or hour_local > 18:
        return 0.0
    cloud_ratio = 0.0 if cloud is None else min(max(cloud, 0), 100) / 100.0
    base = 1000.0
    return base * (1 - cloud_ratio)


def _convert_hourly(hourly: List[Dict[str, Any]], latitude: Optional[float], longitude: Optional[float]) -> HistoryResponse:
    items: List[HistoryItem] = []
    irr_vals: List[float] = []

    for h in hourly:
        ts_raw = h.get("fxTime") or h.get("obsTime")  # 预报/历史字段兼容
        if not ts_raw:
            continue
        try:
            dt = date_parser.parse(ts_raw)
        except Exception:
            continue
        # 统一为本地时间（若 API 返回 UTC，dateutil 会携带 tz）
        dt_local = dt.astimezone(timezone(timedelta(hours=8)))
        hour_local = dt_local.hour

        temp = h.get("temp")
        hum = h.get("humidity")
        wind = h.get("windSpeed")
        cloud = h.get("cloud")
        radiation = h.get("shortwave_radiation")  # Open-Meteo提供的短波辐射

        try:
            temp = float(temp) if temp is not None else None
        except Exception:
            temp = None
        try:
            hum = float(hum) / 100.0 if hum is not None else None
        except Exception:
            hum = None
        try:
            wind = float(wind) if wind is not None else None
        except Exception:
            wind = None
        try:
            cloud = float(cloud) if cloud is not None else None
        except Exception:
            cloud = None
        try:
            radiation = float(radiation) if radiation is not None else None
        except Exception:
            radiation = None

        irr = _estimate_irradiance(radiation, hour_local, cloud)
        irr_vals.append(irr)

        item = HistoryItem(
            timestamp=dt_local.isoformat(),
            temperature=temp,
            humidity=hum,
            wind_speed=wind,
            cloud=cloud,
            real_time_irradiance=irr,
            daily_avg_irradiance=None,  # 稍后填充
            horizontal_irradiance=irr,
            tilted_irradiance=irr,
            sunshine=None if cloud is None else max(0.0, 1 - min(max(cloud, 0), 100) / 100.0),
        )
        items.append(item)

    daily_avg = sum(irr_vals) / len(irr_vals) if irr_vals else 0.0
    for it in items:
        it.daily_avg_irradiance = daily_avg

    if not items:
        raise HTTPException(status_code=404, detail="历史天气为空")

    date_str = items[0].timestamp[:10]
    return HistoryResponse(
        location="",
        date=date_str,
        count=len(items),
        items=items,
        daily_avg_irradiance=daily_avg,
    )


# ------------------------------------------------------------------------------
# FastAPI
# ------------------------------------------------------------------------------
app = FastAPI(
    title="ShuZhiYuan History Weather API",
    version="1.0.0",
    description="基于Open-Meteo免费API的历史天气数据服务，提供历史逐小时天气数据，包括温度、湿度、风速、云量、短波辐射等"
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "data_source": "Open-Meteo",
        "note": "使用Open-Meteo免费API提供历史逐小时天气数据，包括温度、湿度、风速、云量、短波辐射等",
        "projects_configured": len(PROJECT_CATALOG),
    }


@app.get("/weather/history", response_model=HistoryResponse)
def weather_history(
    date: Optional[str] = Query(None, description="YYYY-MM-DD；默认昨天"),
    latitude: Optional[float] = Query(None, description="纬度（必需，可通过project_id自动获取）"),
    longitude: Optional[float] = Query(None, description="经度（必需，可通过project_id自动获取）"),
    project_id: Optional[str] = Query(None, description="项目ID/名称，自动获取预置的经纬度信息"),
):
    """
    查询历史天气数据（使用Open-Meteo免费API）
    
    必须提供经纬度信息，可以通过以下方式：
    1. 直接提供latitude和longitude参数
    2. 通过project_id自动获取（推荐）
    """
    try:
        proj = _find_project(project_id)
        
        # 确保有有效的经纬度
        lat, lon = _ensure_latitude_longitude(latitude, longitude, proj)

        if not date:
            date = (datetime.now(timezone.utc) + timedelta(hours=8) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 验证日期格式
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"日期格式错误，应为 YYYY-MM-DD，收到: {date}")
        
        # 记录查询信息
        logger.info(f"查询历史天气: date={date}, project_id={project_id}, latitude={lat}, longitude={lon}")

        # 使用Open-Meteo获取历史天气数据
        try:
            hourly = _fetch_history_from_openmeteo(lat, lon, date)
            logger.info(f"成功使用Open-Meteo API获取历史天气数据，共 {len(hourly)} 条")
        except Exception as e:
            logger.error(f"Open-Meteo API失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"无法获取历史天气数据：Open-Meteo API失败: {str(e)}"
            )
        
        resp = _convert_hourly(hourly, lat, lon)
        # 使用项目名称或经纬度作为location标识
        if proj:
            resp.location = proj.get("name", f"{lat},{lon}")
        else:
            resp.location = f"{lat},{lon}"
        resp.date = date
        
        return resp
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询历史天气失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询历史天气失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8001)))

