"""薄弱指数计算引擎。

薄弱 = 存量多（未固化题多）+ 近期正确率低。
- 存量比 = 该模块未固化题数 / 该模块总题数
- 近期正确率 = 最近 N 条做题记录的正确率（无记录视为 0.5 中性偏低，鼓励覆盖）
- weakness_score = 0.4 * 存量比 + 0.6 * (1 - 正确率)，0~1，越大越薄弱
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import Question, Mastery, PracticeRecord

RECENT_WINDOW = 20  # 每模块取最近 N 条记录算正确率
NEUTRAL_ACCURACY = 0.5  # 无做题记录时的默认正确率（中性偏低，鼓励覆盖该模块）


def module_weakness(db: Session) -> List[Dict[str, Any]]:
    """返回各模块薄弱信息，按薄弱指数降序。"""
    # 各模块题量与未固化数
    rows = db.query(
        Question.module,
        func.count(Question.id),
        func.count(Mastery.id).filter(Mastery.is_consolidated == False),
    ).outerjoin(Mastery, Mastery.question_id == Question.id) \
     .filter(Question.module.isnot(None)) \
     .group_by(Question.module).all()

    # 各模块最近 N 条记录的正确率
    acc_by_module: Dict[str, List[int, int]] = {}
    for m, _, _ in rows:
        recs = db.query(PracticeRecord).join(Question, Question.id == PracticeRecord.question_id) \
            .filter(Question.module == m, PracticeRecord.is_correct.isnot(None)) \
            .order_by(desc(PracticeRecord.practiced_at)).limit(RECENT_WINDOW).all()
        total = len(recs)
        corr = sum(1 for r in recs if r.is_correct)
        acc_by_module[m] = (corr, total)

    result = []
    for m, total, not_consol in rows:
        ratio = (not_consol / total) if total else 0
        corr, rtot = acc_by_module.get(m, (0, 0))
        acc = (corr / rtot) if rtot else NEUTRAL_ACCURACY
        score = 0.4 * ratio + 0.6 * (1 - acc)
        result.append({
            'module': m,
            'total': total,
            'not_consolidated': not_consol,
            'stock_ratio': round(ratio, 3),
            'recent_correct': corr,
            'recent_total': rtot,
            'recent_accuracy': round(acc, 3),
            'weakness_score': round(score, 3),
        })
    result.sort(key=lambda x: x['weakness_score'], reverse=True)
    return result


if __name__ == '__main__':
    from database import SessionLocal
    db = SessionLocal()
    out = ['%-12s %5s %5s %6s %8s %6s %6s' % ('模块', '总量', '未固化', '存量比', '近期对/总', '正确率', '薄弱指数')]
    for r in module_weakness(db):
        out.append('%-12s %5s %5s %6s %8s %6s %6s' % (
            r['module'], r['total'], r['not_consolidated'], r['stock_ratio'],
            '%s/%s' % (r['recent_correct'], r['recent_total']),
            r['recent_accuracy'], r['weakness_score']))
    db.close()
    with open(r'E:\study\backend\tmp\weakness_test.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('done')