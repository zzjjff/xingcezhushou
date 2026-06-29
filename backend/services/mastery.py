"""掌握度引擎 - 加分/扣分、记忆固化、惰性衰减。

设计：
- update_mastery 写 score / consolidation_count / is_consolidated / last_practice_at
- effective_score 惰性计算"有效分" = score - 距上次练习天数 × 日衰减率
- 衰减不靠定时任务，读取时现算，重启/多 worker 都不会丢
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from models import Mastery


# ============ 参数（与确认方案一致）============
INITIAL_SCORE = 50.0
GAIN_ON_CORRECT = 15.0      # 答对加分
LOSE_ON_WRONG = 20.0        # 答错扣分
MAX_SCORE = 100.0
MIN_SCORE = 0.0
CONSOLIDATE_THRESHOLD = 3   # 连续答对次数阈值
DECAY_PER_DAY = 3.0         # 未固化日衰减
DECAY_PER_DAY_CONSOL = 1.0  # 固化后日衰减
SUPPLEMENT_THRESHOLD = 70.0  # 有效分低于此值进入补弱池


def _now() -> datetime:
    return datetime.now()


def _clamp(v: float) -> float:
    return max(MIN_SCORE, min(MAX_SCORE, v))


def get_or_create(db: Session, question_id: int) -> Mastery:
    """获取掌握度记录，不存在则创建（初始分 50）。"""
    m = db.query(Mastery).filter(Mastery.question_id == question_id).first()
    if not m:
        m = Mastery(question_id=question_id, score=INITIAL_SCORE,
                    consolidation_count=0, is_consolidated=False)
        db.add(m)
        db.flush()
    return m


def update_mastery(db: Session, question_id: int, is_correct: Optional[bool]) -> Mastery:
    """交卷后更新单题掌握度。

    is_correct=None（无标准答案）时只更新 last_practice_at，不改分、不固化。
    """
    m = get_or_create(db, question_id)
    now = _now()

    if is_correct is True:
        m.score = _clamp(m.score + GAIN_ON_CORRECT)
        m.consolidation_count = (m.consolidation_count or 0) + 1
        if m.consolidation_count >= CONSOLIDATE_THRESHOLD:
            m.is_consolidated = True
    elif is_correct is False:
        m.score = _clamp(m.score - LOSE_ON_WRONG)
        m.consolidation_count = 0
        # 答错打破固化，需要重新连续答对才能再固化
        m.is_consolidated = False
    # is_correct is None：仅刷新练习时间

    m.last_practice_at = now
    # 下次复习时间：未固化按衰减到补弱线估算；固化后给更宽裕周期
    daily = DECAY_PER_DAY_CONSOL if m.is_consolidated else DECAY_PER_DAY
    days_to_review = max(1, int((m.score - SUPPLEMENT_THRESHOLD) / daily)) if daily > 0 and m.score > SUPPLEMENT_THRESHOLD else 1
    m.next_review_at = now + timedelta(days=days_to_review)
    return m


def effective_score(m: Mastery, now: Optional[datetime] = None) -> float:
    """惰性计算有效分 = score - 天数 × 日衰减率。

    从未练过（last_practice_at 为空）不衰减，返回 score。
    结果下限 0。
    """
    if m is None:
        return INITIAL_SCORE
    if not m.last_practice_at:
        return float(m.score if m.score is not None else INITIAL_SCORE)
    now = now or _now()
    days = (now - m.last_practice_at).total_seconds() / 86400.0
    if days < 0:
        days = 0
    daily = DECAY_PER_DAY_CONSOL if m.is_consolidated else DECAY_PER_DAY
    eff = (m.score if m.score is not None else INITIAL_SCORE) - days * daily
    return max(MIN_SCORE, eff)


def needs_supplement(m: Mastery, now: Optional[datetime] = None) -> bool:
    """是否进入补弱池：未固化 且 有效分 < 70。"""
    if m is None:
        return True  # 没掌握度记录视为需要补
    if m.is_consolidated:
        return False
    return effective_score(m, now) < SUPPLEMENT_THRESHOLD


# ============ 自测（纯逻辑，不依赖 DB）============
if __name__ == '__main__':
    # 用一个轻量假对象验证 effective_score / 衰减逻辑
    class FakeM:
        def __init__(self, score, last, consol):
            self.score = score
            self.last_practice_at = last
            self.is_consolidated = consol

    now = datetime(2026, 6, 29, 12, 0, 0)
    out = []

    # 1. 从未练过：不衰减
    m = FakeM(50.0, None, False)
    out.append('从未练过 eff=%.1f (期望50)' % effective_score(m, now))

    # 2. 昨天90分未固化：90 - 1*3 = 87
    m = FakeM(90.0, now - timedelta(days=1), False)
    out.append('90/昨天/未固化 eff=%.1f (期望87)' % effective_score(m, now))

    # 3. 10天前80分未固化：80 - 10*3 = 50
    m = FakeM(80.0, now - timedelta(days=10), False)
    out.append('80/10天前/未固化 eff=%.1f (期望50)' % effective_score(m, now))

    # 4. 10天前80分已固化：80 - 10*1 = 70
    m = FakeM(80.0, now - timedelta(days=10), True)
    out.append('80/10天前/固化 eff=%.1f (期望70)' % effective_score(m, now))

    # 5. 衰减到底不超下限：20分30天前未固化 -> 20-90=-70 -> 0
    m = FakeM(20.0, now - timedelta(days=30), False)
    out.append('20/30天前/未固化 eff=%.1f (期望0)' % effective_score(m, now))

    # 6. 补弱判定
    out.append('90/昨天/未固化 needs_supplement=%s (期望False)' % needs_supplement(FakeM(90.0, now - timedelta(days=1), False), now))
    out.append('50/从未练 needs_supplement=%s (期望True)' % needs_supplement(FakeM(50.0, None, False), now))
    out.append('80/10天前/固化 needs_supplement=%s (期望False,固化不补)' % needs_supplement(FakeM(80.0, now - timedelta(days=10), True), now))

    with open(r'E:\study\backend\tmp\mastery_test.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('done')