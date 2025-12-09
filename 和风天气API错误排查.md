# 和风天气API 400错误排查指南

## 错误现象

```
ERROR:main:和风历史接口HTTP错误: status=400, response={'error': {'status': 400, 'type': 'https://dev.qweather.com/docs/resource/error-code/#invalid-parameter', 'title': 'Invalid Parameter', 'detail': 'Invalid parameter, please check your request.', 'invalidParams': ['date']}}
```

## 可能原因

### 1. 日期超出API支持范围 ⚠️ **最可能的原因**

和风天气历史天气API通常只支持查询**最近30天**的历史数据。

**解决方案**：
- 确保查询的日期在最近30天内
- 例如：如果今天是2025年1月15日，只能查询2024年12月16日之后的数据

### 2. API权限不足

和风天气历史天气API需要**付费订阅**才能使用。

**检查方法**：
1. 登录和风天气开发者控制台
2. 查看你的API Key的订阅级别
3. 确认是否包含"历史天气"功能

**解决方案**：
- 升级API订阅级别
- 或联系和风天气客服开通历史天气功能

### 3. 日期格式问题

虽然代码已经将 `YYYY-MM-DD` 转换为 `YYYYMMDD`，但可能仍有问题。

**检查方法**：
查看日志中的 `date` 参数值，应该是8位数字，如 `20251128`

### 4. Location ID 无效

Location ID 可能不正确或已过期。

**检查方法**：
- 确认 `location_id` 是否正确
- 可以使用和风天气的"城市搜索"API验证Location ID

## 诊断步骤

### 步骤1：检查日期范围

```bash
# 计算30天前的日期
# 如果今天是 2025-01-15，30天前是 2024-12-16
# 只能查询 2024-12-16 到 2025-01-15 之间的日期
```

### 步骤2：测试API调用

使用curl测试和风天气API：

```bash
curl "https://devapi.qweather.com/v7/historical/weather?location=101281101&date=20241128&key=你的API_KEY"
```

**注意**：
- `date` 参数必须是 `YYYYMMDD` 格式（8位数字，无横线）
- 日期必须在最近30天内

### 步骤3：检查API响应

如果API返回400错误，查看响应中的 `error` 字段：

```json
{
  "error": {
    "status": 400,
    "type": "...",
    "title": "Invalid Parameter",
    "detail": "Invalid parameter, please check your request.",
    "invalidParams": ["date"]
  }
}
```

## 解决方案

### 方案1：使用最近30天内的日期（推荐）

修改工作流中的日期参数，使用最近30天内的日期：

```python
# 在Dify工作流中，使用动态日期
from datetime import datetime, timedelta

# 获取30天前的日期
target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
```

### 方案2：检查API订阅级别

1. 登录和风天气开发者控制台
2. 查看API Key的订阅信息
3. 确认是否包含"历史天气"功能
4. 如果不包含，需要升级订阅

### 方案3：使用测试日期

如果API支持，可以使用一个已知有效的日期进行测试：

```bash
# 测试昨天的日期
curl "https://devapi.qweather.com/v7/historical/weather?location=101281101&date=20250114&key=你的API_KEY"
```

## 代码改进

已改进的错误处理会：
1. 检测日期参数错误
2. 提供更详细的错误信息
3. 记录完整的API请求和响应

## 联系支持

如果问题仍然存在，建议：
1. 查看和风天气API文档：https://dev.qweather.com/docs/api/historical-weather/
2. 联系和风天气技术支持
3. 检查API Key的订阅状态和额度

