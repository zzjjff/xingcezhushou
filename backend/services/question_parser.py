"""题目结构化切分 - 从提取的纯文本切成单道题目。

当前为正则粗切版本（无 AI 依赖）：
- 识别"一、二、..."大模块标题作为 module
- 纯数字行作为题号边界
- "A、B、C、D、" 开头的行为选项
- answer/explanation 留空，待 AI 补全接口接入后填充
"""
import re
from typing import List
from schemas import QuestionCreate


# 大模块标题：一、政治理论。... / 二、常识判断。...
MODULE_HEADER_RE = re.compile(r'^[一二三四五六七八九十]+、(.+?)[。，]')

# 纯数字行（题号）：如 "1" "135"
QUESTION_NUM_RE = re.compile(r'^\d+$')

# 选项行：A、xxx  /  A. xxx （兼容顿号和点号）
OPTION_RE = re.compile(r'^([A-E])[、.．]\s*(.*)$')

# 需要丢弃的水印/噪声行
NOISE_RE = re.compile(r'(欢迎使用公开真题库|本文档由系统自动生成|^来源：|^分类：)')


def _clean(line: str) -> str:
    """去掉行首尾空白与不间断空格，便于匹配。"""
    return line.replace('\xa0', ' ').replace('\u3000', ' ').strip()


def parse_text_to_questions(text: str) -> List[QuestionCreate]:
    """把整篇文本切成 QuestionCreate 列表（仅正则，无 AI）。

    返回的题目 answer/explanation 均为 None，source_file 为 None。
    """
    lines = [_clean(l) for l in text.split('\n')]

    questions: List[QuestionCreate] = []
    current_module: str = None

    cur = None  # {num, content_lines, options}

    def _flush():
        nonlocal cur
        if not cur:
            return
        content = '\n'.join(cur['content_lines']).strip()
        opts = cur['options']
        # 至少要有题干 + 至少 2 个选项才算一道有效题
        if content and len(opts) >= 2:
            questions.append(QuestionCreate(
                content=content,
                option_a=opts.get('A'),
                option_b=opts.get('B'),
                option_c=opts.get('C'),
                option_d=opts.get('D'),
                option_e=opts.get('E'),
                answer=None,
                explanation=None,
                module=current_module,
                sub_type=None,
                difficulty=3,
                source_file=None,
            ))
        cur = None

    for line in lines:
        if not line:
            continue
        if NOISE_RE.search(line):
            continue

        # 大模块标题
        m = MODULE_HEADER_RE.match(line)
        if m:
            _flush()
            current_module = m.group(1).strip()
            continue

        # 纯数字题号 = 新题起点
        if QUESTION_NUM_RE.match(line):
            _flush()
            cur = {'num': line, 'content_lines': [], 'options': {}}
            continue

        # 选项行
        om = OPTION_RE.match(line)
        if om and cur is not None:
            cur['options'][om.group(1)] = om.group(2).strip()
            continue

        # 普通正文行：归入当前题干
        if cur is not None:
            cur['content_lines'].append(line)

    _flush()
    return questions


if __name__ == '__main__':
    from services.parser import parse_file
    import sys, os
    from collections import Counter
    path = sys.argv[1] if len(sys.argv) > 1 else r'E:\study\2026年国家公务员录用考试_行测_题_副省级网友回忆版_.docx'
    text = parse_file(path)
    qs = parse_text_to_questions(text)
    c = Counter(q.module for q in qs)
    out = []
    out.append(f'切出题目数: {len(qs)}')
    for k, v in c.items():
        out.append(f'  {k}: {v}')
    out.append('')
    out.append('=== 前 2 题 ===')
    for q in qs[:2]:
        out.append(f'[module={q.module}] {q.content[:80]}')
        out.append(f'  A={q.option_a} | B={q.option_b} | C={q.option_c} | D={q.option_d}')
        out.append(f'  answer={q.answer} explanation={q.explanation}')
        out.append('')
    out.append('=== 最后 1 题 ===')
    if qs:
        q = qs[-1]
        out.append(f'[module={q.module}] {q.content[:80]}')
        out.append(f'  A={q.option_a} | B={q.option_b} | C={q.option_c} | D={q.option_d}')
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tmp', 'parse_result.txt')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('result written to', out_path, 'questions:', len(qs))