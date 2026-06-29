from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Question(Base):
    """题目表"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False, comment="题干内容")
    option_a = Column(String(500), comment="选项A")
    option_b = Column(String(500), comment="选项B")
    option_c = Column(String(500), comment="选项C")
    option_d = Column(String(500), comment="选项D")
    option_e = Column(String(500), comment="选项E")
    answer = Column(String(10), comment="正确答案")
    explanation = Column(Text, comment="解析")
    module = Column(String(50), comment="模块：言语理解/数量关系/判断推理/资料分析/常识判断")
    sub_type = Column(String(50), comment="子类型")
    difficulty = Column(Integer, default=3, comment="难度1-5")
    source_file = Column(String(200), comment="来源文件名")
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联
    mastery = relationship("Mastery", back_populates="question", uselist=False)
    practice_records = relationship("PracticeRecord", back_populates="question")


class Mastery(Base):
    """掌握度表"""
    __tablename__ = "masteries"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), unique=True)
    score = Column(Float, default=50.0, comment="掌握度分数0-100")
    last_practice_at = Column(DateTime, comment="最近练习时间")
    next_review_at = Column(DateTime, comment="下次复习时间")
    consolidation_count = Column(Integer, default=0, comment="连续答对次数（用于固化判断）")
    is_consolidated = Column(Boolean, default=False, comment="是否已固化")
    
    # 关联
    question = relationship("Question", back_populates="mastery")


class PracticeRecord(Base):
    """做题记录表"""
    __tablename__ = "practice_records"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    user_answer = Column(String(10), comment="用户答案")
    correct_answer_at_time = Column(String(10), comment="当时的正确答案")
    is_correct = Column(Boolean, comment="是否正确")
    time_spent_seconds = Column(Integer, comment="耗时秒数")
    practiced_at = Column(DateTime, default=datetime.now, comment="练习时间")
    
    # 关联
    question = relationship("Question", back_populates="practice_records")
