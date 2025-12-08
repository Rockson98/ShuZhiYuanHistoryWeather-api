# ShuZhiYuanHistoryWeather-api

用于获取某项目指定日期的历史逐小时气象数据，并派生光伏预测所需的基础特征（温度/湿度/风速/“日照度”与简易辐照度估算）。基于 FastAPI，可部署到 Render。

## 主要特性
- 历史天气（小时级）：通过和风天气历史接口（需 `QWEATHER_API_KEY` 付费版权限）。
- 简易辐照度估算：用云量 + 昼夜窗口估算水平/倾斜辐照度；如需精确辐照度请用专业辐照度服务替换。
- 产出字段可直接用于 power-prediction-api 的 `HorizonPredictionRequest`：
  - timestamp, temperature, humidity, wind_speed
  - real_time_irradiance / horizontal_irradiance / tilted_irradiance
  - daily_avg_irradiance（当日均值）、sunshine（1 - cloud/100 的近似）

## 环境变量
- `QWEATHER_API_KEY`：必填，和风天气 API Key（需有历史接口权限）。
- `QWEATHER_API_HOST`：可选，自定义 Host（默认 `devapi.qweather.com`）。
- `WEATHER_DEFAULT_LOCATION`：可选，默认 Location ID 或城市名，用于未传 location 时的兜底。

## 运行
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

## 部署到 Render
仓库包含 `render.yaml` 与 `Procfile`，创建 Web Service 即可：
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment: 配置 `QWEATHER_API_KEY`（必填），可选 `QWEATHER_API_HOST`、`WEATHER_DEFAULT_LOCATION`。

## API
### GET /health
返回服务状态与 Host 配置。

### GET /weather/history
查询历史逐小时天气，并派生光伏特征。

查询参数：
- `location`：Location ID 或城市名（优先）。若未提供，则使用 `WEATHER_DEFAULT_LOCATION`。
- `latitude`、`longitude`：可选，用于辐照度昼夜判定与后续精细化（当前仅用来判定日夜窗口）。
- `date`：YYYY-MM-DD，默认昨天。

响应示例（精简）：
```json
{
  "location": "101281101",
  "date": "2025-11-28",
  "count": 24,
  "items": [
    {
      "timestamp": "2025-11-28T08:00:00+08:00",
      "temperature": 18.4,
      "humidity": 0.65,
      "wind_speed": 3.1,
      "cloud": 40,
      "real_time_irradiance": 600.0,
      "daily_avg_irradiance": 480.0,
      "horizontal_irradiance": 600.0,
      "tilted_irradiance": 600.0,
      "sunshine": 0.6
    }
  ],
  "daily_avg_irradiance": 320.5
}
```

## 与 Dify 工作流集成
1) 部署本服务到 Render，拿到公网 URL（如 `https://shuzhiyuan-history-weather.onrender.com`）。  
2) 在工作流中新增一个自定义 HTTP / Code 节点，调用：  
   `GET https://.../weather/history?location=101281101&date=2025-11-28`  
3) 将响应的 `items` 映射/压缩为 power-prediction-api 需要的字段（如选取当天 24 条，用 `real_time_irradiance` → HorizonPredictionRequest.data[*].real_time_irradiance 等）。

> 注意：辐照度为经验近似。若有可靠辐照度源，请在代码中替换 `_estimate_irradiance` 逻辑或对接专业 API。

