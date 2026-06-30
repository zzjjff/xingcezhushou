"""配置读取 - 从环境变量或 backend/.env 加载 AI 配置。

不引入额外依赖：用标准库 os 读取。.env 仅作本地默认值，已被环境变量覆盖时以环境变量为准。
填好 .env 中的 AI_API_KEY 后即可启用 AI 补全，无需改代码。
"""
import os


def _load_env_file():
    """简单加载 .env 到 os.environ（不覆盖已存在的环境变量）。"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


_load_env_file()

AI_API_KEY = os.getenv('AI_API_KEY', '').strip()
AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://api.deepseek.com/v1').strip()
AI_MODEL = os.getenv('AI_MODEL', 'deepseek-chat').strip()


def has_ai_key() -> bool:
    return bool(AI_API_KEY)

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '').strip()
