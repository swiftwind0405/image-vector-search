from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


def create_auth_router(*, admin_username: str, admin_password: str) -> APIRouter:
    router = APIRouter()
    normalized_username = admin_username.strip()
    normalized_password = admin_password.strip()
    auth_enabled = bool(normalized_username and normalized_password)

    @router.get("/api/auth/me")
    async def auth_me(request: Request):
        if not auth_enabled:
            return JSONResponse({"authenticated": True})
        authenticated = request.session.get("authenticated", False)
        return JSONResponse({"authenticated": authenticated})

    @router.post("/api/auth/login")
    async def auth_login(payload: LoginRequest, request: Request):
        if not auth_enabled:
            return JSONResponse({"ok": True})
        if payload.username == normalized_username and payload.password == normalized_password:
            request.session["authenticated"] = True
            return JSONResponse({"ok": True})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    @router.post("/api/auth/logout")
    async def auth_logout(request: Request):
        request.session.clear()
        return JSONResponse({"ok": True})

    return router
