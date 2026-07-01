"""Pydantic schemas — re-exports for convenient imports."""

from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse as AuthMessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    VerifyEmailRequest,
)
from app.schemas.chat import (
    ConversationCreate,
    ConversationList,
    ConversationResponse,
    ConversationUpdate,
    MessageList,
    MessageResponse as ChatMessageResponse,
    MessageSend,
    StreamChunk,
)

__all__ = [
    "AuthMessageResponse",
    "AuthResponse",
    "ChangePasswordRequest",
    "ChatMessageResponse",
    "ConversationCreate",
    "ConversationList",
    "ConversationResponse",
    "ConversationUpdate",
    "ForgotPasswordRequest",
    "MessageList",
    "MessageSend",
    "RefreshRequest",
    "ResetPasswordRequest",
    "StreamChunk",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "VerifyEmailRequest",
]
