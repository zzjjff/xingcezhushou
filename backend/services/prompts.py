"""AI 补全的 prompt 模板，强约束输出 JSON。"""

SYSTEM = '你是行测题目解析专家，擅长判断正确答案并写出解析。严格只输出 JSON，不要任何额外文字或解释。'

# 限制每批最多补全的题数，避免 token 超限
BATCH_SIZE = 10


def build_complete_prompt(numbered_questions):
    """构造补全 prompt。

    numbered_questions: [{"index":0,"content":..,"option_a":..,...}, ...]
    返回 OpenAI messages 列表。AI 应返回 {"results":[{"index":0,"answer":"A","explanation":"..."}]}
    """
    import json
    payload = json.dumps(numbered_questions, ensure_ascii=False)
    user = (
        '请为下面每道单选题判断正确答案并写出简短解析。\n'
        '输出格式：{"results":[{"index":0,"answer":"A","explanation":"解析文本"}, ...]}\n'
        'answer 为单个字母(A-E)；index 必须与输入对应；不要遗漏任何一题。\n\n'
        f'题目列表：\n{payload}'
    )
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}]