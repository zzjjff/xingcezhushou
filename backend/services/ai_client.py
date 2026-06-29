"""大模型调用封装（OpenAI 兼容 /chat/completions 格式）。

无 AI_API_KEY 时 call_llm 抛 AIConfigError，由上层走降级路径。
用标准库 urllib，不引入 requests 等额外依赖。
"""
import json
import urllib.request
import urllib.error

from config import AI_API_KEY, AI_BASE_URL, AI_MODEL, has_ai_key


class AIConfigError(RuntimeError):
    """未配置 AI_API_KEY，无法调用大模型。"""


def call_llm(messages, temperature=0.2, json_mode=True, timeout=60):
    """调用大模型，返回 message.content 文本。

    messages: OpenAI 格式 [{"role":..., "content":...}, ...]
    json_mode=True 时请求 JSON 输出（需模型支持，DeepSeek/智谱均支持）。
    """
    if not has_ai_key():
        raise AIConfigError('未配置 AI_API_KEY，请在 backend/.env 中填入')

    url = AI_BASE_URL.rstrip('/') + '/chat/completions'
    body = {
        'model': AI_MODEL,
        'messages': messages,
        'temperature': temperature,
    }
    if json_mode:
        body['response_format'] = {'type': 'json_object'}

    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {AI_API_KEY}',
    }, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        return result['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'AI 调用失败 HTTP {e.code}: {detail[:200]}') from e