import json
import os
from pathlib import Path
from typing import List, Dict, Any

# 默认项目清单，可根据需要修改或用环境变量覆盖
# 项目信息与 README.md 中的配置保持一致
DEFAULT_PROJECTS: List[Dict[str, Any]] = [
    {
        "project_id": "1",
        "name": "台山海宴渔光互补项目",
        "latitude": 21.755591,
        "longitude": 112.565857,
        "city": "江门市台山市",  # 城市名称（用于显示）
    },
    {
        "project_id": "2",
        "name": "肇庆四会屋顶项目",
        "latitude": 23.376972,
        "longitude": 112.705725,
        "city": "肇庆市四会市",  # 城市名称（用于显示）
    },
    {
        "project_id": "3",
        "name": "珠海香洲近海光伏",
        "latitude": 22.270715,
        "longitude": 113.576722,
        "city": "珠海市香洲区",  # 城市名称（用于显示）
    },
]


def _load_from_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_project_catalog() -> List[Dict[str, Any]]:
    """
    优先级：
    1) WEATHER_PROJECTS_FILE 指定的 JSON 文件
    2) WEATHER_PROJECTS_JSON 环境变量（JSON 数组）
    3) DEFAULT_PROJECTS
    """
    file_path = os.getenv("WEATHER_PROJECTS_FILE", "").strip()
    if file_path:
        projects = _load_from_file(Path(file_path))
        if projects:
            return projects

    env_json = os.getenv("WEATHER_PROJECTS_JSON", "").strip()
    if env_json:
        try:
            projects = json.loads(env_json)
            if isinstance(projects, list) and projects:
                return projects
        except Exception:
            pass

    return DEFAULT_PROJECTS

