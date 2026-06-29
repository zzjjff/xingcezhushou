"""FastAPI 主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from routers import questions
from routers import exam


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：创建所有表
    Base.metadata.create_all(bind=engine)
    print("数据库表已创建/确认")
    yield
    # 关闭时：清理资源（如有定时任务在此停止）
    print("服务关闭")


app = FastAPI(
    title="行测智能学习系统",
    description="个人行测刷题工具 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(questions.router)
app.include_router(exam.router)


@app.get("/")
def root():
    return {"message": "行测智能学习系统 API 运行中"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
