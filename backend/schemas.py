from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============ 题目相关 ============

class QuestionBase(BaseModel):
    content: str = Field(..., description="题干内容")
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    option_e: Optional[str] = None
    answer: Optional[str] = None
    explanation: Optional[str] = None
    module: Optional[str] = None
    sub_type: Optional[str] = None
    difficulty: Optional[int] = 3


class QuestionCreate(QuestionBase):
    source_file: Optional[str] = None


class QuestionResponse(QuestionBase):
    id: int
    source_file: Optional[str] = None
    created_at: datetime
    mastery_score: Optional[float] = None

    class Config:
        from_attributes = True


class QuestionList(BaseModel):
    total: int
    items: List[QuestionResponse]


# ============ 做题相关 ============

class ExamAnswer(BaseModel):
    question_id: int
    user_answer: str
    time_spent: int = Field(..., description="耗时秒数")


class ExamSubmit(BaseModel):
    answers: List[ExamAnswer]


class ExamStartRequest(BaseModel):
    module: Optional[str] = None
    count: int = Field(10, ge=1, le=50, description="抽题数量")


class ExamStartResponse(BaseModel):
    exam_id: str
    questions: List[QuestionResponse]
    total_time_seconds: Optional[int] = None  # 全真模拟限时(7200)，None 表示不限时


# 单题判分明细：无标准答案时 is_correct/correct_answer 为 None（待 AI 补全后回溯）
class ExamDetail(BaseModel):
    question_id: int
    user_answer: str
    correct_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    time_spent: int


class ExamResult(BaseModel):
    total: int
    correct: Optional[int] = None  # 无标准答案时为 None
    accuracy: Optional[float] = None
    details: List[ExamDetail]


# ============ 上传与解析相关 ============

class UploadResponse(BaseModel):
    filename: str
    raw_text: str
    text_length: int


class ParseRequest(BaseModel):
    raw_text: str = Field(..., description="待解析的题目纯文本")


class ParseResult(BaseModel):
    mode: str = Field(..., description="解析方式：regex / ai")
    count: int
    items: List[QuestionCreate]


class BatchImportResult(BaseModel):
    inserted: int
    skipped: int
    total: int


# 单题更新（答案录入用，可扩展）
class QuestionUpdate(BaseModel):
    answer: Optional[str] = None
    explanation: Optional[str] = None



# ============ AI 补全相关 ============

class AICompleteRequest(BaseModel):
    questions: List[QuestionCreate]


class AICompleteResult(BaseModel):
    mode: str = Field(..., description="ai / skipped")
    count: int
    items: List[QuestionCreate]
    message: Optional[str] = None



# ============ 组卷相关 ============

class ExamGenerateRequest(BaseModel):
    mode: str = Field("supplement", description="mock 按行测比例模拟 / supplement 培优补弱")
    count: int = Field(10, ge=1, le=50, description="组卷题量(补弱/按模块用)")
    level: Optional[str] = Field("normal", description="全真模拟档位: easy120/easier125/normal130/hard135/hell140")

# ============ 复盘相关 ============

class ReviewSummary(BaseModel):
    total: int
    correct: int
    accuracy: float

class ReviewModule(BaseModel):
    module: str
    total: int
    correct: int
    accuracy: float
    avg_time: float

class ReviewTrendItem(BaseModel):
    date: str
    correct: int
    total: int
    accuracy: float

class ReviewWrong(BaseModel):
    question_id: int
    content: str
    module: Optional[str] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    practiced_at: Optional[str] = None

class ReviewResponse(BaseModel):
    summary: ReviewSummary
    modules: List[ReviewModule]
    trend: List[ReviewTrendItem]
    wrong_questions: List[ReviewWrong]

class WrongBookItem(BaseModel):
    question_id: int
    content: str
    module: Optional[str] = None
    score: float
    effective_score: float
    is_consolidated: bool
    last_practice_at: Optional[str] = None
    wrong_count: int

