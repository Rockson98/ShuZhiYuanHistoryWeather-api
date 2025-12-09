import os
import logging
from typing import Any, Dict, List, Optional
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
QWEATHER_API_KEY = os.getenv("QWEATHER_API_KEY", "").strip()
QWEATHER_API_HOST = os.getenv("QWEATHER_API_HOST", "").strip() or "https://devapi.qweather.com"
WEATHER_DEFAULT_LOCATION = os.getenv("WEATHER_DEFAULT_LOCATION", "").strip()
# 项目清单（可通过 WEATHER_PROJECTS_JSON / WEATHER_PROJECTS_FILE 覆盖）
PROJECT_CATALOG: List[Dict[str, Any]] = get_project_catalog()

if not QWEATHER_API_KEY:
    logger.warning("QWEATHER_API_KEY 未设置，历史天气查询将失败。请在环境变量中配置。")

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


def _ensure_location(location: Optional[str], project: Optional[Dict[str, Any]]) -> str:
    if project:
        loc_id = project.get("location_id")
        loc_name = project.get("location_name") or project.get("city") or project.get("name")
        if loc_id:
            return str(loc_id)
        if loc_name:
            return str(loc_name)
    if location:
        return location
    if WEATHER_DEFAULT_LOCATION:
        return WEATHER_DEFAULT_LOCATION
    raise HTTPException(status_code=400, detail="location 不能为空，且未设置 WEATHER_DEFAULT_LOCATION")


def _fetch_history_from_qweather(location: str, date_str: str) -> List[Dict[str, Any]]:
    """
    调用和风天气历史接口，返回原始小时数据列表。
    说明：和风历史接口需付费权限，路径示例：
    https://devapi.qweather.com/v7/historical/weather?location=xxx&date=YYYYMMDD
    """
    if not QWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="未配置 QWEATHER_API_KEY，无法查询历史天气")

    base = QWEATHER_API_HOST.rstrip("/")
    # 确保 URL 包含协议前缀
    if not base.startswith("http://") and not base.startswith("https://"):
        base = f"https://{base}"
    url = f"{base}/v7/historical/weather"
    params = {
        "location": location,
        "date": date_str.replace("-", ""),  # YYYYMMDD
        "key": QWEATHER_API_KEY,  # 兼容部分部署方式，若服务端要求 Header，可调整为 X-QW-Api-Key
    }

    resp = requests.get(url, params=params, timeout=15)
    try:
        data = resp.json()
    except Exception as e:
        logger.error(f"和风API响应解析失败: {e}, status={resp.status_code}, text={resp.text[:200]}")
        raise HTTPException(status_code=500, detail=f"和风API响应解析失败: {str(e)}")

    if resp.status_code != 200:
        msg = data.get("message") or data.get("code") or f"http {resp.status_code}"
        logger.error(f"和风历史接口HTTP错误: status={resp.status_code}, response={data}")
        raise HTTPException(status_code=500, detail=f"和风历史接口失败: {msg}")

    api_code = str(data.get("code", ""))
    if api_code != "200":
        msg = data.get("message") or data.get("refer", {}) or f"code={api_code}"
        logger.error(f"和风历史接口返回异常: code={api_code}, response={data}")
        raise HTTPException(status_code=500, detail=f"和风历史接口返回异常: code={api_code}, message={msg}")

    hourly = data.get("hourly") or []
    return hourly


def _estimate_irradiance(hour_local: int, cloud: Optional[float]) -> float:
    """
    简易辐照度估算：
    - 仅在 6~18 点有辐照度
    - 基准 1000 W/m2，按云量折减 (1 - cloud/100)
    """
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

        irr = _estimate_irradiance(hour_local, cloud)
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
app = FastAPI(title="ShuZhiYuan History Weather API", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "qweather_key": bool(QWEATHER_API_KEY),
        "host": QWEATHER_API_HOST,
        "default_location": WEATHER_DEFAULT_LOCATION or None,
        "note": "提供历史逐小时天气 + 简易辐照度估算（6~18点按云量折减）"
    }


@app.get("/weather/history", response_model=HistoryResponse)
def weather_history(
    location: Optional[str] = Query(None, description="Location ID 或 城市名；若不传则用 WEATHER_DEFAULT_LOCATION"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD；默认昨天"),
    latitude: Optional[float] = Query(None, description="可选，用于后续精细估算"),
    longitude: Optional[float] = Query(None, description="可选，用于后续精细估算"),
    project_id: Optional[str] = Query(None, description="可选，传入项目ID/名称以使用预置经纬度和 location_id"),
):
    try:
        proj = _find_project(project_id)

        loc = _ensure_location(location, proj)
        lat = latitude if latitude is not None else (proj.get("latitude") if proj else None)
        lon = longitude if longitude is not None else (proj.get("longitude") if proj else None)

        if not date:
            date = (datetime.now(timezone.utc) + timedelta(hours=8) - timedelta(days=1)).strftime("%Y-%m-%d")

        logger.info(f"查询历史天气: location={loc}, date={date}, project_id={project_id}")

        hourly = _fetch_history_from_qweather(loc, date)
        resp = _convert_hourly(hourly, lat, lon)
        resp.location = loc
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

