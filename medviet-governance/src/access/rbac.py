# src/access/rbac.py
import casbin
import inspect
from functools import wraps
from fastapi import HTTPException, Header
from typing import Optional

# Danh sách user giả lập (production dùng JWT + DB)
MOCK_USERS = {
    "token-alice": {"username": "alice", "role": "admin"},
    "token-bob":   {"username": "bob",   "role": "ml_engineer"},
    "token-carol": {"username": "carol", "role": "data_analyst"},
    "token-dave":  {"username": "dave",  "role": "intern"},
}

enforcer = casbin.Enforcer("src/access/model.conf", "src/access/policy.csv")

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    TODO: Parse Bearer token và trả về user info.
    Raise HTTPException 401 nếu token không hợp lệ.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.removeprefix("Bearer ").strip()
    user = MOCK_USERS.get(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user

def require_permission(resource: str, action: str):
    """
    TODO: Decorator kiểm tra RBAC permission.
    Dùng casbin enforcer để check (role, resource, action).
    Raise HTTPException 403 nếu không có quyền.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Lấy current_user từ kwargs (FastAPI inject qua Depends)
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="Missing user")

            username = current_user["username"]
            role = current_user["role"]

            allowed = enforcer.enforce(username, resource, action)

            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{role}' cannot '{action}' on '{resource}'"
                )
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        return wrapper
    return decorator
