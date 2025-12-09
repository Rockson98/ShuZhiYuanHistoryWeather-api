# ShuZhiYuanHistoryWeather-api Render 部署指南

## 前置条件
1. 已创建 GitHub 仓库：`ShuZhiYuanHistoryWeather-api-1`
2. 已拥有 Render 账号（https://render.com）
3. ✅ **无需API Key**：使用Open-Meteo免费API，完全免费

## 部署步骤

### 方法一：使用 render.yaml 自动部署（推荐）

1. **登录 Render Dashboard**
   - 访问 https://dashboard.render.com
   - 使用 GitHub 账号登录

2. **创建新的 Web Service**
   - 点击 "New +" → 选择 "Blueprint"
   - 在 "Public Git repository" 输入框中输入你的 GitHub 仓库地址：
     ```
     https://github.com/你的用户名/ShuZhiYuanHistoryWeather-api-1
     ```
   - 点击 "Apply"

3. **Render 会自动读取 render.yaml 配置**
   - Render 会自动检测到 `render.yaml` 文件
   - 服务名称：`shuzhiyuan-history-weather`
   - 构建命令和启动命令会自动应用

4. **配置环境变量（可选）**
   - 在 Render Dashboard 中，进入你的服务页面
   - 点击左侧 "Environment" 标签
   - 以下环境变量为**可选**，通常不需要配置：
   
   **可选环境变量：**
   - `WEATHER_PROJECTS_JSON`: 项目配置 JSON 字符串（可选，覆盖 `config.py` 中的默认项目）
   - `WEATHER_PROJECTS_FILE`: 项目配置 JSON 文件路径（可选，优先级高于 `WEATHER_PROJECTS_JSON`）
   
   **预配置项目（无需额外配置）：**
   
   以下三个项目已预配置在 `config.py` 中，可直接使用 `project_id` 参数查询，自动获取经纬度信息：
   
   | project_id | 项目名称 | 纬度 | 经度 |
   |-----------|---------|------|------|
   | 1 | 台山海宴渔光互补项目 | 21.755591 | 112.565857 |
   | 2 | 肇庆四会屋顶项目 | 23.376972 | 112.705725 |
   | 3 | 珠海香洲近海光伏 | 22.270715 | 113.576722 |
   
   **使用示例：**
   ```bash
   # 方式1：使用 project_id 查询（推荐，自动使用预配置的经纬度）
   curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?project_id=1&date=2024-11-28"
   
   # 方式2：直接提供经纬度
   curl "https://shuzhiyuanhistoryweather-api.onrender.com/weather/history?latitude=21.755591&longitude=112.565857&date=2024-11-28"
   ```
   
   **WEATHER_PROJECTS_JSON 格式示例（如需覆盖默认配置）：**
   ```json
   [
     {
       "project_id": "1",
       "name": "台山海宴渔光互补项目",
       "latitude": 21.755591,
       "longitude": 112.565857,
       "city": "江门市台山市"
     },
     {
       "project_id": "2",
       "name": "肇庆四会屋顶项目",
       "latitude": 23.376972,
       "longitude": 112.705725
     }
   ]
   ```
   > 注意：
   > - 如果使用环境变量，需要将整个 JSON 数组压缩为一行，去掉换行和多余空格
   > - `location_id` 和 `location_name` 字段已不再需要（Open-Meteo不需要）
   > - 只需要 `latitude` 和 `longitude` 字段

5. **部署**
   - 点击 "Save Changes"
   - Render 会自动开始构建和部署
   - 等待部署完成（通常 2-5 分钟）

6. **验证部署**
   - 部署完成后，Render 会提供一个 URL，例如：`https://shuzhiyuan-history-weather.onrender.com`
   - 访问健康检查端点：`https://你的服务URL/health`
   - 应该看到类似以下响应：
     ```json
     {
       "status": "ok",
       "data_source": "Open-Meteo",
       "note": "使用Open-Meteo免费API提供历史逐小时天气数据，包括温度、湿度、风速、云量、短波辐射等",
       "projects_configured": 3
       "note": "提供历史逐小时天气 + 简易辐照度估算（6~18点按云量折减）"
     }
     ```

### 方法二：手动创建 Web Service

如果不想使用 Blueprint，也可以手动创建：

1. **创建新的 Web Service**
   - 点击 "New +" → 选择 "Web Service"
   - 连接你的 GitHub 仓库：`ShuZhiYuanHistoryWeather-api-1`
   - 选择仓库和分支

2. **配置服务**
   - **Name**: `shuzhiyuan-history-weather`
   - **Environment**: `Python 3`
   - **Region**: 选择离你最近的区域（如 `Singapore`）
   - **Branch**: `main` 或 `master`
   - **Root Directory**: 如果代码在子目录，填写 `ShuZhiYuanHistoryWeather-api-1`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **配置环境变量**（同方法一的第 4 步）

4. **创建服务并部署**

## 测试 API

部署成功后，可以使用以下方式测试：

### 1. 健康检查
```bash
curl https://你的服务URL/health
```

### 2. 查询历史天气（使用 project_id，推荐）
```bash
curl "https://你的服务URL/weather/history?project_id=1&date=2024-11-28"
```

### 3. 查询历史天气（直接提供经纬度）
```bash
curl "https://你的服务URL/weather/history?latitude=21.755591&longitude=112.565857&date=2024-11-28"
```

## 常见问题

### 1. 部署失败：SyntaxError
- 检查代码是否有语法错误
- 确保 `main.py` 和 `config.py` 文件格式正确

### 2. API 返回 500 错误
- 检查是否提供了有效的经纬度（latitude 和 longitude）
- 检查日期格式是否正确（YYYY-MM-DD）
- 检查日期是否在合理范围内（Open-Meteo支持过去80年的历史数据）
- 查看 Render 的日志（Logs 标签）获取详细错误信息

### 3. 找不到项目（project_id 无效）
- 检查 `WEATHER_PROJECTS_JSON` 环境变量格式是否正确
- 或确认 `config.py` 中的 `DEFAULT_PROJECTS` 包含你使用的 `project_id`

### 4. 服务启动后立即停止
- 检查 `Procfile` 或 `startCommand` 是否正确
- 确保 `main.py` 中的 FastAPI 应用名为 `app`

## 更新部署

当你更新 GitHub 代码后：
- 如果启用了 `autoDeploy`（render.yaml 中），Render 会自动重新部署
- 或手动在 Render Dashboard 中点击 "Manual Deploy"

## 获取服务 URL

部署完成后，在 Render Dashboard 的服务页面顶部可以看到服务 URL，格式通常为：
```
https://shuzhiyuan-history-weather.onrender.com
```

将此 URL 用于 Dify 工作流中的 HTTP 请求节点。

