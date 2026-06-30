"""认证与管理员权限"""
from fastapi import APIRouter, HTTPException, Header
from config import ADMIN_PASSWORD
from schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """管理员密码登录，返回 token。"""
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=400, detail="未配置管理员密码(backend/.env ADMIN_PASSWORD)")
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    return TokenResponse(token=ADMIN_PASSWORD, role="admin")


def require_admin(authorization: str = Header(None, alias="Authorization")):
    """依赖：校验管理员 token。普通用户不可访问受保护接口。"""
    token = (authorization or "").replace("Bearer ", "").strip()
    if not ADMIN_PASSWORD or token != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="需要管理员权限")
    return True
