"""Authentication endpoints (email + password, JWT session cookie, email codes).

The frontend reaches these through a Next.js rewrite of ``/api/*``, so the
routes carry no ``/api`` prefix.
"""

import asyncio
import logging
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.core.auth import User, get_current_user
from app.core.security import (
    SESSION_COOKIE_NAME,
    create_session_token,
)
from app.services import auth_service
from app.services.auth_service import AuthError, PendingEmail
from app.services.mailer import send_code_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ResendCodeRequest(BaseModel):
    email: EmailStr
    purpose: Literal["verify_email", "reset_password"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    password: str


def _error(status_code: int, code: str, message: str, headers: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "request_id": str(uuid4())}},
        headers=headers,
    )


def _to_http_error(exc: AuthError) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return _error(exc.status_code, exc.code, exc.message, headers)


async def _send(pending: PendingEmail | None) -> None:
    if pending is not None:
        await send_code_email(pending.to, pending.code, pending.purpose)


async def _run(func, *args):
    """Run blocking service code (database, bcrypt) off the event loop."""
    return await asyncio.to_thread(func, *args)


def _set_session_cookie(response: Response, user_id: str, email: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(user_id, email),
        max_age=settings.AUTH_SESSION_TTL_SECONDS,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, response: Response):
    email = auth_service.normalize_email(body.email)

    if not settings.AUTH_REQUIRE_EMAIL_VERIFICATION:
        # Happy path without email: create the account and start a session.
        try:
            user = await _run(
                auth_service.signup_without_verification,
                body.email,
                body.password,
                body.full_name,
            )
        except AuthError as exc:
            raise _to_http_error(exc) from exc
        _set_session_cookie(response, str(user["id"]), user["email"])
        return {
            "email": email,
            "verification_required": False,
            "user": auth_service.public_user(user),
        }

    try:
        pending = await _run(auth_service.signup, body.email, body.password, body.full_name)
    except AuthError as exc:
        raise _to_http_error(exc) from exc
    await _send(pending)
    return {"email": email, "verification_required": True}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, response: Response):
    try:
        user = await _run(auth_service.verify_email, body.email, body.code)
    except AuthError as exc:
        raise _to_http_error(exc) from exc
    _set_session_cookie(response, str(user["id"]), user["email"])
    return {"user": auth_service.public_user(user)}


@router.post("/resend-code")
async def resend_code(body: ResendCodeRequest):
    try:
        pending = await _run(auth_service.resend_code, body.email, body.purpose)
    except Exception:
        # Never reveal whether the account exists, even through a failure.
        logger.exception("resend-code failed")
        return {"sent": True}
    await _send(pending)
    return {"sent": True}


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    try:
        user = await _run(auth_service.login, body.email, body.password)
    except AuthError as exc:
        await _send(exc.pending_email)
        raise _to_http_error(exc) from exc
    _set_session_cookie(response, str(user["id"]), user["email"])
    return {"user": auth_service.public_user(user)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return response


@router.get("/session")
async def session(current_user: User = Depends(get_current_user)):
    user = await _run(auth_service.get_user, current_user.id)
    if user is None:
        raise _error(
            status.HTTP_401_UNAUTHORIZED,
            "INVALID_TOKEN",
            "Invalid authentication token",
            {"WWW-Authenticate": "Bearer"},
        )
    return {"user": auth_service.public_user(user)}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    try:
        pending = await _run(auth_service.forgot_password, body.email)
    except Exception:
        logger.exception("forgot-password failed")
        return {"sent": True}
    await _send(pending)
    return {"sent": True}


@router.post("/verify-reset-code")
async def verify_reset_code(body: VerifyResetCodeRequest):
    try:
        token = await _run(auth_service.verify_reset_code, body.email, body.code)
    except AuthError as exc:
        raise _to_http_error(exc) from exc
    return {"reset_token": token}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    try:
        await _run(auth_service.reset_password, body.reset_token, body.password)
    except AuthError as exc:
        raise _to_http_error(exc) from exc
    return {"ok": True}
