# API 测试指南

## 服务地址
```
https://shuzhiyuanhistoryweather-api.onrender.com
```

## 1. 健康检查
```bash
curl https://shuzhiyuanhistoryweather-api.onrender.com/health
```

预期响应：
```json
{
  "status": "ok",
  "qweather_key": true,
  "host": "https://devapi.qweather.com",
  "default_location": null,
  "note": "提供历史逐小时天气 + 简易辐照度估算（6~18点按云量折减）"
}
```

## 2. 查询历史天气（使用 project_id）
```bash
curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?project_id=1001&date=2024-11-28"
```

## 3. 查询历史天气（使用 location）
```bash
curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?location=101281101&date=2024-11-28"
```

## 4. 查询历史天气（使用经纬度）
```bash
curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?latitude=21.755591&longitude=112.565857&date=2024-11-28"
```

## 注意事项

1. **环境变量配置**：确保在 Render Dashboard 中已配置 `QWEATHER_API_KEY`
2. **历史数据额度**：确保和风天气账号有历史数据查询额度
3. **日期格式**：日期格式为 `YYYY-MM-DD`，例如 `2024-11-28`
4. **默认日期**：如果不传 `date` 参数，默认查询昨天的数据

## 在 Dify 工作流中使用

在 Dify 的 HTTP 请求节点中：
- **URL**: `https://shuzhiyuanhistoryweather-api.onrender.com/weather/history`
- **Method**: `GET`
- **Query Parameters**:
  - `project_id`: 项目ID（如 `1001`）
  - `date`: 日期（如 `2024-11-28`）

或者使用 `location` 参数：
- `location`: Location ID（如 `101281101`）
- `date`: 日期

