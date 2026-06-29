"""做题相关路由"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Question, PracticeRecord
from services.mastery import update_mastery, effective_score, needs_supplement, SUPPLEMENT_THRESHOLD
from services.weakness import module_weakness
from services.review import build_review, wrong_book
import random
from schemas import (
    ExamStartRequest, ExamStartResponse, ExamSubmit, ExamResult, ExamDetail, ExamGenerateRequest, ReviewResponse, WrongBookItem,
    QuestionResponse,
)

router = APIRouter(prefix="/api/exam", tags=["做题"])


@router.post("/start", response_model=ExamStartResponse)
def start_exam(req: ExamStartRequest, db: Session = Depends(get_db)):
    """随机抽题组卷。可选模块；不查掌握度（培优补弱留 Phase 3）。"""
    query = db.query(Question)
    if req.module:
        query = query.filter(Question.module == req.module)

    total_available = query.count()
    if total_available == 0:
        raise HTTPException(status_code=400, detail="该模块下无题目")

    # 抽题数不超过可用数
    count = min(req.count, total_available)
    questions = query.order_by(Question.id).all()

    # 随机抽样（题库小，用 random.sample 即可）
    import random
    picked = random.sample(questions, count)

    items = [QuestionResponse(
        id=q.id,
        content=q.content,
        option_a=q.option_a,
        option_b=q.option_b,
        option_c=q.option_c,
        option_d=q.option_d,
        option_e=q.option_e,
        answer=q.answer,
        explanation=q.explanation,
        module=q.module,
        sub_type=q.sub_type,
        difficulty=q.difficulty,
        source_file=q.source_file,
        created_at=q.created_at,
        mastery_score=q.mastery.score if q.mastery else None,
    ) for q in picked]

    return ExamStartResponse(exam_id=str(uuid.uuid4()), questions=items)


@router.post("/submit", response_model=ExamResult)
def submit_exam(req: ExamSubmit, db: Session = Depends(get_db)):
    """交卷：记录每题作答。

    有标准答案时触发掌握度更新（答对加分/答错扣分/固化）。
    无标准答案时 is_correct 为 None，仅刷新练习时间不改分。
    """
    details: List[ExamDetail] = []
    for ans in req.answers:
        q = db.query(Question).filter(Question.id == ans.question_id).first()
        if not q:
            continue

        has_answer = bool(q.answer)
        is_correct = None
        if has_answer:
            is_correct = (ans.user_answer == q.answer)

        # 写做题记录
        # 触发掌握度更新（Phase 3）
        update_mastery(db, ans.question_id, is_correct)

        db.add(PracticeRecord(
            question_id=ans.question_id,
            user_answer=ans.user_answer,
            correct_answer_at_time=q.answer,
            is_correct=is_correct,
            time_spent_seconds=ans.time_spent,
        ))

        details.append(ExamDetail(
            question_id=ans.question_id,
            user_answer=ans.user_answer,
            correct_answer=q.answer if has_answer else None,
            is_correct=is_correct,
            time_spent=ans.time_spent,
        ))

    db.commit()

    # 有标准答案的题才计入正确率
    judged = [d for d in details if d.is_correct is not None]
    if judged:
        correct = sum(1 for d in judged if d.is_correct)
        accuracy = round(correct / len(judged), 4)
    else:
        correct = None
        accuracy = None

    return ExamResult(
        total=len(details),
        correct=correct,
        accuracy=accuracy,
        details=details,
    )
# 行测通用模块比例（共130题，国/省/市有差异，先做通用版，后续按具体考试个性化调整）
MOCK_RATIO = {
    "政治理论": 20, "常识判断": 15, "言语理解与表达": 30,
    "判断推理": 35, "数量关系": 10, "资料分析": 20,
}

# 全真模拟题量档位（后续可细化难度调整）
LEVEL_QUESTIONS = {"easy": 120, "easier": 125, "normal": 130, "hard": 135, "hell": 140}

def _to_response(q):
    return QuestionResponse(
        id=q.id, content=q.content, option_a=q.option_a, option_b=q.option_b,
        option_c=q.option_c, option_d=q.option_d, option_e=q.option_e,
        answer=q.answer, explanation=q.explanation, module=q.module,
        sub_type=q.sub_type, difficulty=q.difficulty, source_file=q.source_file,
        created_at=q.created_at,
        mastery_score=q.mastery.score if q.mastery else None,
    )


def _pick_random(db, module, n):
    """从指定模块随机抽 n 题（不查掌握度）。"""
    qs = db.query(Question).filter(Question.module == module).all()
    return random.sample(qs, min(n, len(qs))) if qs else []


@router.post("/generate", response_model=ExamStartResponse)
def generate_paper(req: ExamGenerateRequest, db: Session = Depends(get_db)):
    """双模式组卷。

    模式A(mock)：按行测真实比例分配题量，纯随机抽题，不查掌握度。
    模式B(supplement)：按薄弱指数分配模块题量，从有效分<70且未固化的补弱池抽；
                       不足则从该模块未固化全量补、再不足从全量随机补，标注来源。
    """
    if req.mode == "mock":
        # 全真模拟：按档位题量 + 通用比例抽题，不跨模块补足（各模块 min(目标,库有)，多少就是多少）
        count = LEVEL_QUESTIONS.get(req.level, 130)
        total_ratio = sum(MOCK_RATIO.values())
        picked = []
        for m, r in MOCK_RATIO.items():
            n = round(count * r / total_ratio)
            picked.extend(_pick_random(db, m, n))  # _pick_random 内部已 min(n, 库有)
        # 限时按题量等比折算（130 题=7200 秒）
        total_time = round(count / 130 * 7200)
        return ExamStartResponse(exam_id=str(uuid.uuid4()), questions=[_to_response(q) for q in picked], total_time_seconds=total_time)

    # 模式B：培优补弱
    weakness = module_weakness(db)
    if not weakness:
        raise HTTPException(status_code=400, detail="题库无题目，无法组卷")

    # 按薄弱指数分配题量（薄弱指数加权）
    wsum = sum(w["weakness_score"] for w in weakness) or 1.0
    picked = []
    now = datetime.now()
    for w in weakness:
        n = max(1, round(req.count * w["weakness_score"] / wsum))
        # 补弱池：有效分<70 且未固化
        pool = [q for q in db.query(Question).filter(Question.module == w["module"]).all()
                if q.mastery and needs_supplement(q.mastery, now)]
        # 降级1：补弱池不足 → 该模块未固化全量
        if len(pool) < n:
            extra = [q for q in db.query(Question).filter(Question.module == w["module"]).all()
                     if q.mastery and not q.mastery.is_consolidated and q not in pool]
            pool.extend(extra)
        # 降级2：仍不足 → 该模块全量随机
        if len(pool) < n:
            pool = db.query(Question).filter(Question.module == w["module"]).all()
        picked.extend(random.sample(pool, min(n, len(pool))) if pool else [])

    # 总量不足 req.count 时从全库随机补
    if len(picked) < req.count:
        all_q = db.query(Question).all()
        candidates = [q for q in all_q if q not in picked]
        picked.extend(random.sample(candidates, min(req.count - len(picked), len(candidates))) if candidates else [])
    picked = picked[:req.count]

    return ExamStartResponse(exam_id=str(uuid.uuid4()), questions=[_to_response(q) for q in picked])

@router.get("/review", response_model=ReviewResponse)
def get_review(db: Session = Depends(get_db)):
    """复盘统计：各模块正确率/平均耗时、近期趋势、错题列表。"""
    return build_review(db)

@router.get("/wrong_book", response_model=List[WrongBookItem])
def get_wrong_book(module: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """动态错题本：做错过的题，按有效分(含衰减)升序。"""
    return wrong_book(db, module)

@router.post("/practice_one", response_model=ExamStartResponse)
def practice_one(question_id: int = Query(...), db: Session = Depends(get_db)):
    """定向复习：按指定题 id 组单题试卷。"""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    return ExamStartResponse(exam_id=str(uuid.uuid4()), questions=[_to_response(q)])

