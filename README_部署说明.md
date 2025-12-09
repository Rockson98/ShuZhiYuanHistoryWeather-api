# ShuZhiYuanHistoryWeather-api Render 部署指南

## 前置条件
1. 已创建 GitHub 仓库：`ShuZhiYuanHistoryWeather-api-1`
2. 已拥有 Render 账号（https://render.com）
3. 已获取和风天气 API Key（需要历史数据额度）

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

4. **配置环境变量**
   - 在 Render Dashboard 中，进入你的服务页面
   - 点击左侧 "Environment" 标签
   - 添加以下环境变量：
   
   **必需环境变量：**
   - `QWEATHER_API_KEY`: 你的和风天气 API Key
   
   **可选环境变量：**
   - `QWEATHER_API_HOST`: 和风天气 API 主机（默认：`https://devapi.qweather.com`）
   - `WEATHER_DEFAULT_LOCATION`: 默认 Location ID（当不传 `project_id` 或 `location` 时使用）
   - `WEATHER_PROJECTS_JSON`: 项目配置 JSON 字符串（可选，覆盖 `config.py` 中的默认项目）
   
   **WEATHER_PROJECTS_JSON 格式示例：**
   ```json
   [
     {
       "project_id": "1001",
       "name": "台山海宴渔光互补项目",
       "latitude": 21.755591,
       "longitude": 112.565857,
       "location_id": "101281101"
     },
     {
       "project_id": "1002",
       "name": "肇庆四会屋顶项目",
       "latitude": 23.376972,
       "longitude": 112.705725,
       "location_id": "101280901"
     }
   ]
   ```
   > 注意：如果使用环境变量，需要将整个 JSON 数组压缩为一行，去掉换行和多余空格。

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
       "qweather_key": true,
       "host": "https://devapi.qweather.com",
       "default_location": null,
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

### 2. 查询历史天气（使用 project_id）
```bash
curl "https://你的服务URL/weather/history?project_id=1001&date=2024-11-28"
```

### 3. 查询历史天气（使用 location）
```bash
curl "https://你的服务URL/weather/history?location=101281101&date=2024-11-28"
```

## 常见问题

### 1. 部署失败：SyntaxError
- 检查代码是否有语法错误
- 确保 `main.py` 和 `config.py` 文件格式正确

### 2. API 返回 500 错误
- 检查 `QWEATHER_API_KEY` 是否正确设置
- 检查是否有历史数据查询额度
- 查看 Render 的日志（Logs 标签）

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

