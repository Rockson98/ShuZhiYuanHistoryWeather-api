"""
Open-Meteo历史天气数据获取函数
作为和风天气API的免费替代方案
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


def _fetch_history_from_openmeteo(
    latitude: float,
    longitude: float,
    date_str: str
) -> List[Dict[str, Any]]:
    """
    使用Open-Meteo获取历史天气数据（免费）
    
    参数:
        latitude: 纬度
        longitude: 经度
        date_str: 日期字符串，格式 YYYY-MM-DD
    
    返回:
        格式化的历史天气数据列表，格式与和风天气API兼容
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
    
    logger.info(f"调用Open-Meteo API: url={url}, params={params}")
    
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
        # 转换时间格式为ISO格式（兼容和风天气格式）
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


def _estimate_irradiance_from_radiation(
    shortwave_radiation: Optional[float],
    hour_local: int
) -> float:
    """
    从短波辐射估算辐照度
    如果shortwave_radiation可用，直接使用；否则使用简易估算
    """
    if shortwave_radiation is not None and shortwave_radiation >= 0:
        return float(shortwave_radiation)
    
    # 降级到简易估算（仅在6-18点有辐照度）
    if hour_local < 6 or hour_local > 18:
        return 0.0
    
    hour_offset = abs(hour_local - 12)
    return max(0, 1000 - hour_offset * 50)


def _convert_openmeteo_hourly(
    hourly: List[Dict[str, Any]],
    latitude: Optional[float],
    longitude: Optional[float]
) -> List[Dict[str, Any]]:
    """
    将Open-Meteo的数据转换为我们的HistoryItem格式
    """
    from dateutil import parser as date_parser
    
    items = []
    irr_vals = []
    
    for h in hourly:
        ts_raw = h.get("fxTime") or h.get("obsTime")
        if not ts_raw:
            continue
        
        try:
            dt = date_parser.parse(ts_raw)
        except Exception:
            continue
        
        # 统一为本地时间（UTC+8）
        dt_local = dt.astimezone(timezone(timedelta(hours=8)))
        hour_local = dt_local.hour
        
        temp = h.get("temp")
        hum = h.get("humidity")  # 已经是百分比
        wind = h.get("windSpeed")
        cloud = h.get("cloud")
        radiation = h.get("shortwave_radiation")
        
        # 转换数据类型
        try:
            temp = float(temp) if temp is not None else None
        except Exception:
            temp = None
        
        try:
            # humidity已经是百分比，转换为0-1范围
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
        
        # 估算辐照度
        irr = _estimate_irradiance_from_radiation(radiation, hour_local)
        irr_vals.append(irr)
        
        # 创建HistoryItem（需要导入HistoryItem）
        from main import HistoryItem
        
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
    
    # 计算日平均辐照度
    daily_avg = sum(irr_vals) / len(irr_vals) if irr_vals else 0.0
    for it in items:
        it.daily_avg_irradiance = daily_avg
    
    return items

