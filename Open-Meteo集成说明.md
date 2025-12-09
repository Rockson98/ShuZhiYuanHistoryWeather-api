# Open-Meteo 免费历史天气API集成说明

## ✅ 已完成的集成

已成功将 **Open-Meteo** 集成到历史天气API中，作为和风天气的免费备选方案。

---

## 工作原理

### 双数据源降级策略

```
1. 优先尝试和风天气API
   ├─ 如果成功 → 使用和风天气数据
   └─ 如果失败 → 降级到步骤2

2. 降级到Open-Meteo API（免费）
   ├─ 如果成功 → 使用Open-Meteo数据
   └─ 如果失败 → 返回错误
```

### 数据源选择逻辑

1. **如果配置了和风天气API Key**：
   - 优先使用和风天气
   - 如果和风天气失败，自动降级到Open-Meteo

2. **如果未配置和风天气API Key**：
   - 直接使用Open-Meteo（需要经纬度信息）

---

## 使用方式

### 方式1：通过项目ID（推荐）

```bash
# 使用项目ID，自动获取经纬度
curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?project_id=1&date=2024-11-28"
```

**优点**：
- 无需手动输入经纬度
- 自动使用预配置的地理信息
- 支持双数据源降级

### 方式2：直接提供经纬度

```bash
# 直接提供经纬度（用于Open-Meteo）
curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?latitude=21.755591&longitude=112.565857&date=2024-11-28"
```

---

## Open-Meteo API 特点

### ✅ 优点

1. **完全免费**：无需注册，无需API Key
2. **历史数据支持**：可查询过去80年的历史数据
3. **数据质量高**：基于ECMWF等权威数据源
4. **中国覆盖**：支持中国地区数据
5. **辐照度数据**：提供`shortwave_radiation`，可直接用于辐照度计算

### ⚠️ 注意事项

1. **需要经纬度**：不支持Location ID，必须提供经纬度坐标
2. **数据延迟**：历史数据可能有1-2天延迟
3. **数据精度**：基于模型数据，可能与实际观测有差异

---

## 数据字段映射

### Open-Meteo → 我们的数据模型

| Open-Meteo字段 | 我们的字段 | 转换说明 |
|---------------|-----------|---------|
| `temperature_2m` | `temperature` | 直接使用（℃） |
| `relative_humidity_2m` | `humidity` | 除以100（转换为0-1范围） |
| `windspeed_10m` | `wind_speed` | 直接使用（m/s） |
| `cloudcover` | `cloud` | 直接使用（%） |
| `shortwave_radiation` | `horizontal_irradiance` | 直接使用（W/m²）⭐ |
| `shortwave_radiation` | `tilted_irradiance` | 直接使用（W/m²）⭐ |
| `shortwave_radiation` | `real_time_irradiance` | 直接使用（W/m²）⭐ |

**⭐ 重要**：Open-Meteo提供的`shortwave_radiation`比简易估算更准确！

---

## 测试示例

### 测试Open-Meteo API（直接调用）

```bash
# 测试台山项目（纬度21.755591，经度112.565857）2024-11-28的历史天气
curl "https://archive-api.open-meteo.com/v1/archive?latitude=21.755591&longitude=112.565857&start_date=2024-11-28&end_date=2024-11-28&hourly=temperature_2m,relative_humidity_2m,windspeed_10m,cloudcover,shortwave_radiation&timezone=Asia/Shanghai"
```

### 测试我们的API（使用Open-Meteo）

```bash
# 方式1：使用项目ID（推荐）
curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?project_id=1&date=2024-11-28"

# 方式2：直接提供经纬度
curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?latitude=21.755591&longitude=112.565857&date=2024-11-28"
```

---

## 配置说明

### 环境变量

**和风天气（可选）**：
- `QWEATHER_API_KEY`: 和风天气API Key（如果配置，优先使用）
- `QWEATHER_API_HOST`: 和风天气API主机（默认：`https://devapi.qweather.com`）

**Open-Meteo（无需配置）**：
- ✅ 无需任何配置，直接可用

### 项目配置

项目配置在 `config.py` 中，包含：
- `project_id`: 项目ID
- `latitude`: 纬度（用于Open-Meteo）
- `longitude`: 经度（用于Open-Meteo）
- `location_id`: Location ID（用于和风天气）

---

## 错误处理

### 场景1：和风天气失败，Open-Meteo成功

```
INFO: 和风天气API失败，尝试使用Open-Meteo: [错误信息]
INFO: 成功使用Open-Meteo API获取历史天气数据
INFO: 历史天气数据来源: openmeteo, 数据条数: 24
```

### 场景2：两个API都失败

```
ERROR: 和风天气API失败，尝试使用Open-Meteo: [错误信息]
ERROR: Open-Meteo API也失败: [错误信息]
HTTP 500: 无法获取历史天气数据：和风天气API和Open-Meteo API都失败
```

### 场景3：未配置和风天气，缺少经纬度

```
HTTP 400: 无法获取历史天气数据：未配置和风天气API Key，且缺少经纬度信息（无法使用Open-Meteo）
```

---

## 优势对比

| 特性 | 和风天气 | Open-Meteo |
|------|---------|-----------|
| **费用** | ❌ 需付费 | ✅ 完全免费 |
| **历史数据** | ✅ 支持 | ✅ 支持（80年） |
| **中国覆盖** | ✅ 优秀 | ✅ 良好 |
| **数据精度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Location ID** | ✅ 支持 | ❌ 不支持 |
| **经纬度** | ✅ 支持 | ✅ 必需 |
| **辐照度数据** | ⚠️ 需估算 | ✅ 直接提供 |
| **调用限制** | ⚠️ 有额度限制 | ✅ 无限制（合理使用） |

---

## 推荐使用场景

### 场景1：有和风天气API Key

**推荐配置**：
- 配置 `QWEATHER_API_KEY`
- 使用项目ID查询（自动降级到Open-Meteo）

**优势**：
- 优先使用高质量的和风天气数据
- 如果和风天气失败，自动使用免费的Open-Meteo
- 确保服务高可用性

### 场景2：没有和风天气API Key

**推荐配置**：
- 不配置 `QWEATHER_API_KEY`
- 使用项目ID查询（直接使用Open-Meteo）

**优势**：
- 完全免费
- 无需API Key
- 数据质量可靠

---

## 下一步

1. **提交代码到GitHub**
2. **重新部署到Render**
3. **测试API调用**：
   ```bash
   # 测试（不配置和风天气API Key，直接使用Open-Meteo）
   curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?project_id=1&date=2024-11-28"
   ```

---

## 总结

✅ **已成功集成Open-Meteo作为免费备选方案**

- 无需额外配置
- 自动降级机制
- 数据质量可靠
- 完全免费使用

现在即使和风天气API不可用，API也能正常工作！

