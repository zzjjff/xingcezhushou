"""题库管理路由"""
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from models import Question, Mastery
from schemas import (
    QuestionCreate, QuestionResponse, QuestionList, UploadResponse,
    ParseRequest, ParseResult, BatchImportResult, QuestionUpdate, AICompleteRequest, AICompleteResult,
)
from services.parser import parse_file
from services.question_parser import parse_text_to_questions
from routers.auth import require_admin
from config import has_ai_key
from services.ai_client import call_llm, AIConfigError
from services.prompts import build_complete_prompt, BATCH_SIZE

router = APIRouter(prefix="/api/questions", tags=["题库管理"])

# 无答案时占位，保证交卷判分闭环不中断；找到真答案后用 PATCH 覆盖
_PLACEHOLDER_ANSWER = "A"


def _fill_placeholder(q: QuestionCreate) -> QuestionCreate:
    if not q.answer:
        return q.model_copy(update={"answer": _PLACEHOLDER_ANSWER})
    return q


def _create_one(db: Session, question: QuestionCreate) -> bool:
    """插入单道题并联动创建掌握度。按 content 去重，已存在返回 False。"""
    exists = db.query(Question.id).filter(Question.content == question.content).first()
    if exists:
        return False
    question = _fill_placeholder(question)
    db_question = Question(**question.model_dump())
    db.add(db_question)
    db.flush()
    db.add(Mastery(question_id=db_question.id, score=50.0))
    return True


@router.post("", response_model=QuestionResponse)
def create_question(question: QuestionCreate, db: Session = Depends(get_db), admin: bool = Depends(require_admin)):
    """创建单道题目"""
    question = _fill_placeholder(question)
    db_question = Question(**question.model_dump())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    mastery = Mastery(question_id=db_question.id, score=50.0)
    db.add(mastery)
    db.commit()

    return db_question


@router.get("", response_model=QuestionList)
def list_questions(
    module: Optional[str] = Query(None, description="按模块筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db), admin: bool = Depends(require_admin)
):
    """题目列表查询"""
    query = db.query(Question)

    if module:
        query = query.filter(Question.module == module)

    total = query.count()
    items = query.order_by(Question.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    result = []
    for q in items:
        q_dict = {
            "id": q.id,
            "content": q.content,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "option_e": q.option_e,
            "answer": q.answer,
            "explanation": q.explanation,
            "module": q.module,
            "sub_type": q.sub_type,
            "difficulty": q.difficulty,
            "source_file": q.source_file,
            "created_at": q.created_at,
            "mastery_score": q.mastery.score if q.mastery else None
        }
        result.append(QuestionResponse(**q_dict))

    return QuestionList(total=total, items=result)


@router.post("/parse", response_model=ParseResult)
def parse_questions(req: ParseRequest, db: Session = Depends(get_db)):
    """把纯文本切成结构化题目列表（不入库）。"""
    items = parse_text_to_questions(req.raw_text)
    return ParseResult(mode="regex", count=len(items), items=items)


@router.post("/batch", response_model=BatchImportResult)
def batch_import(questions: List[QuestionCreate], db: Session = Depends(get_db)):
    """批量入库，按 content 去重，无答案占位 A。"""
    inserted = 0
    skipped = 0
    for q in questions:
        if _create_one(db, q):
            inserted += 1
        else:
            skipped += 1
    db.commit()
    return BatchImportResult(inserted=inserted, skipped=skipped, total=len(questions))


@router.post("/ai_complete", response_model=AICompleteResult)
def ai_complete(req: AICompleteRequest, db: Session = Depends(get_db)):
    """AI 补全答案与解析。

    无 AI_API_KEY 时降级返回原题（mode=skipped）；有 key 时按批调用大模型补全。
    """
    if not has_ai_key():
        return AICompleteResult(
            mode="skipped",
            count=len(req.questions),
            items=req.questions,
            message="未配置 AI_API_KEY，已跳过补全。可在 backend/.env 填入后启用。",
        )

    items = [q.model_dump() for q in req.questions]
    fields = ("content", "option_a", "option_b", "option_c", "option_d", "option_e", "module")
    try:
        for start in range(0, len(items), BATCH_SIZE):
            chunk = items[start:start + BATCH_SIZE]
            numbered = [{"index": i, **{k: c.get(k) for k in fields}} for i, c in enumerate(chunk)]
            raw = call_llm(build_complete_prompt(numbered))
            import json
            data = json.loads(raw)
            ans_map = {r.get("index"): r for r in data.get("results", [])}
            for i, c in enumerate(chunk):
                r = ans_map.get(i)
                if not r:
                    continue
                if r.get("answer"):
                    c["answer"] = r["answer"]
                if r.get("explanation"):
                    c["explanation"] = r["explanation"]
        return AICompleteResult(
            mode="ai",
            count=len(items),
            items=[QuestionCreate(**c) for c in items],
            message="AI 补全完成",
        )
    except AIConfigError as e:
        return AICompleteResult(mode="skipped", count=len(items), items=[QuestionCreate(**c) for c in items], message=str(e))
    except Exception as e:
        return AICompleteResult(mode="skipped", count=len(items), items=[QuestionCreate(**c) for c in items], message=f"AI 调用异常，已降级：{e}")

@router.post("/{question_id}/ai_explain", response_model=AICompleteResult)
def ai_explain_one(question_id: int, db: Session = Depends(get_db)):
    """单题 AI 补全答案/解析（无 key 降级返回原题+提示）。"""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    qc = QuestionCreate(content=q.content, option_a=q.option_a, option_b=q.option_b,
                       option_c=q.option_c, option_d=q.option_d, option_e=q.option_e,
                       answer=q.answer, explanation=q.explanation, module=q.module,
                       sub_type=q.sub_type, difficulty=q.difficulty, source_file=q.source_file)
    # 复用 ai_complete 逻辑：构造单题请求
    req = AICompleteRequest(questions=[qc])
    return ai_complete(req, db)


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: int, db: Session = Depends(get_db), admin: bool = Depends(require_admin)):
    """获取单道题目详情"""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")

    return QuestionResponse(
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
        mastery_score=q.mastery.score if q.mastery else None
    )


@router.patch("/{question_id}", response_model=QuestionResponse)
def update_question(question_id: int, req: QuestionUpdate, db: Session = Depends(get_db), admin: bool = Depends(require_admin)):
    """更新题目（答案录入/解析补充）。仅更新非 None 字段。"""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")

    if req.answer is not None:
        q.answer = req.answer
    if req.explanation is not None:
        q.explanation = req.explanation

    db.commit()
    db.refresh(q)

    return QuestionResponse(
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
        mastery_score=q.mastery.score if q.mastery else None
    )


@router.delete("/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db), admin: bool = Depends(require_admin)):
    """删除题目"""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")

    if q.mastery:
        db.delete(q.mastery)
    for record in q.practice_records:
        db.delete(record)
    db.delete(q)
    db.commit()

    return {"message": "删除成功"}


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传 Word/PDF 文件，提取原文"""
    if not file.filename.lower().endswith((".docx", ".pdf")):
        raise HTTPException(status_code=400, detail="仅支持 .docx 和 .pdf 文件")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        raw_text = parse_file(tmp_path)
        return UploadResponse(
            filename=file.filename,
            raw_text=raw_text,
            text_length=len(raw_text)
        )
    finally:
        os.unlink(tmp_path)


@router.get("/modules/list")
def list_modules(db: Session = Depends(get_db)):
    """获取所有模块列表"""
    modules = db.query(Question.module).distinct().all()
    return [m[0] for m in modules if m[0]]