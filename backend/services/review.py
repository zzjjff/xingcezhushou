"""复盘统计 - 聚合各模块正确率、平均耗时、近期趋势、错题列表。

数据量小也能跑：无记录的模块返回零值，趋势按做题日期聚合取最近 30 天。
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Question, PracticeRecord, Mastery


def build_review(db: Session, days: int = 30) -> Dict[str, Any]:
    """聚合复盘数据。"""
    since = datetime.now() - timedelta(days=days)

    # 各模块做题情况
    rows = db.query(
        Question.module,
        func.count(PracticeRecord.id),
        func.coalesce(func.sum(PracticeRecord.is_correct), 0),
        func.coalesce(func.avg(PracticeRecord.time_spent_seconds), 0),
    ).join(Question, Question.id == PracticeRecord.question_id) \
     .filter(Question.module.isnot(None)) \
     .group_by(Question.module).all()

    modules = []
    total_all = 0
    correct_all = 0
    for m, tot, corr, avg_t in rows:
        tot = int(tot)
        corr = int(corr)
        total_all += tot
        correct_all += corr
        modules.append({
            'module': m,
            'total': tot,
            'correct': corr,
            'accuracy': round(corr / tot, 4) if tot else 0.0,
            'avg_time': round(float(avg_t), 1) if avg_t else 0.0,
        })
    modules.sort(key=lambda x: x['module'])

    # 近期趋势：按做题日期聚合
    recs = db.query(PracticeRecord).filter(PracticeRecord.practiced_at >= since) \
        .order_by(PracticeRecord.practiced_at).all()
    day_map: Dict[str, List[int, int]] = {}
    for r in recs:
        if r.is_correct is None or not r.practiced_at:
            continue
        key = r.practiced_at.strftime('%Y-%m-%d')
        d = day_map.setdefault(key, [0, 0])
        d[1] += 1
        if r.is_correct:
            d[0] += 1
    trend = [{'date': k, 'correct': v[0], 'total': v[1], 'accuracy': round(v[0]/v[1], 4)}
             for k, v in sorted(day_map.items())]

    # 错题列表（最近）
    wrong = db.query(PracticeRecord, Question).join(Question, Question.id == PracticeRecord.question_id) \
        .filter(PracticeRecord.is_correct == False) \
        .order_by(PracticeRecord.practiced_at.desc()).limit(50).all()
    wrong_questions = [{
        'question_id': q.id,
        'content': q.content[:120],
        'module': q.module,
        'user_answer': p.user_answer,
        'correct_answer': q.answer,
        'practiced_at': p.practiced_at.strftime('%Y-%m-%d %H:%M') if p.practiced_at else None,
    } for p, q in wrong]

    return {
        'summary': {
            'total': total_all,
            'correct': correct_all,
            'accuracy': round(correct_all / total_all, 4) if total_all else 0.0,
        },
        'modules': modules,
        'trend': trend,
        'wrong_questions': wrong_questions,
    }


if __name__ == '__main__':
    from database import SessionLocal
    import json
    db = SessionLocal()
    data = build_review(db)
    db.close()
    with open(r'E:\study\backend\tmp\review_test.txt', 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
    print('done')

def wrong_book(db: Session, module: Optional[str] = None) -> List[Dict[str, Any]]:
    """动态错题本：做错过的题 + 有效分<70 的题，按有效分升序。

    effective_score 为惰性现算（含衰减），是"该不该复习"的核心信号。
    """
    from services.mastery import effective_score, SUPPLEMENT_THRESHOLD
    from sqlalchemy import func

    # 错题本范围：做错过的题（effective_score 仅作为衰减信号展示，不作为入选条件——
    # 否则初始分50的题全<70会把全库塞进来）
    wrong_ids = [r[0] for r in db.query(PracticeRecord.question_id)
                 .filter(PracticeRecord.is_correct == False)
                 .distinct().all()]

    target_ids = set(wrong_ids)
    if module:
        # 按模块过滤
        target_ids = {qid for qid in target_ids
                      if db.query(Question.module).filter(Question.id == qid).scalar() == module}

    result = []
    for qid in target_ids:
        q = db.query(Question).filter(Question.id == qid).first()
        if not q:
            continue
        m = q.mastery
        eff = effective_score(m) if m else 50.0
        wrong_count = db.query(func.count(PracticeRecord.id))             .filter(PracticeRecord.question_id == qid, PracticeRecord.is_correct == False).scalar() or 0
        result.append({
            'question_id': q.id,
            'content': q.content[:120],
            'module': q.module,
            'score': round(float(m.score), 1) if m else 50.0,
            'effective_score': round(eff, 1),
            'is_consolidated': bool(m.is_consolidated) if m else False,
            'last_practice_at': m.last_practice_at.strftime('%Y-%m-%d %H:%M') if m and m.last_practice_at else None,
            'wrong_count': wrong_count,
        })
    result.sort(key=lambda x: x['effective_score'])
    return result

