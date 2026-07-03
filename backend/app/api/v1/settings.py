"""Settings & workspace configuration API router.

Provides endpoints for user settings, API provider configs, session
management, password change, and settings import/export.  All endpoints
are ownership-gated via the ``get_current_active_user`` dependency.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from jose import JWTError

from app.api.deps import DbSession, get_current_active_user
from app.core.config import settings as app_settings
from app.core.security import decode_token
from app.models.user import User
from app.schemas.settings import (
    ACCENT_COLORS,
    AI_PROVIDERS,
    DENSITY_OPTIONS,
    THEME_OPTIONS,
    ApiProviderCreate,
    ApiProviderListResponse,
    ApiProviderResponse,
    ApiProviderUpdate,
    PasswordChangeRequest,
    SettingsExportResponse,
    SettingsImport,
    UserSessionListResponse,
    UserSessionResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services.settings import (
    CannotRevokeCurrentSession,
    PasswordIncorrect,
    ProviderAlreadyExists,
    ProviderNotFound,
    SessionNotFound,
    SettingsNotFound,
    SettingsService,
)

router = APIRouter()


# ── Helper ─────────────────────────────────────────────────────────────────────


def _extract_jti_from_cookie(request: Request) -> str | None:
    """Extract the JWT ID from the refresh-token cookie, if present."""
    cookie_name = app_settings.REFRESH_TOKEN_COOKIE_NAME
    token = request.cookies.get(cookie_name)
    if not token:
        return None
    try:
        payload = decode_token(token)
        jti: str | None = payload.get("jti")
        return jti
    except JWTError:
        return None


# ── User Settings ─────────────────────────────────────────────────────────────


@router.get(
    "/settings",
    response_model=UserSettingsResponse,
    summary="Get user settings",
    description=(
        "Return the current user's settings, auto-creating a default "
        "settings row if one does not yet exist."
    ),
)
async def get_settings(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> UserSettingsResponse:
    svc = SettingsService(db)
    return await svc.get_settings(current_user.id)


@router.patch(
    "/settings",
    response_model=UserSettingsResponse,
    summary="Update user settings",
    description=(
        "Partial update of user settings.  Only the fields provided in "
        "the request body are changed; omitted fields keep their current "
        "values.  Auto-creates default settings if they don't exist yet."
    ),
)
async def update_settings(
    data: UserSettingsUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> UserSettingsResponse:
    svc = SettingsService(db)
    return await svc.update_settings(current_user.id, data)


@router.post(
    "/settings/reset",
    response_model=UserSettingsResponse,
    summary="Reset settings to defaults",
    description=(
        "Reset settings to factory defaults.  Optionally pass a "
        "``category`` query parameter to reset only ``general``, "
        "``notifications``, or ``appearance`` fields."
    ),
)
async def reset_settings(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    category: str | None = Query(
        None,
        description="Optional category to reset: 'general', 'notifications', 'appearance'",
    ),
) -> UserSettingsResponse:
    svc = SettingsService(db)
    try:
        return await svc.reset_settings(current_user.id, category=category)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/settings/export",
    response_model=SettingsExportResponse,
    summary="Export settings",
    description=(
        "Export all user settings, API provider configs (keys masked), "
        "and active session count.  Compatible with the import endpoint."
    ),
)
async def export_settings(
    request: Request,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> SettingsExportResponse:
    jti = _extract_jti_from_cookie(request)
    svc = SettingsService(db)
    return await svc.export_settings(current_user.id, current_jti=jti)


@router.post(
    "/settings/import",
    response_model=UserSettingsResponse,
    summary="Import settings",
    description=(
        "Import settings and/or API provider configs from a JSON payload "
        "matching the export shape.  Existing settings are merged; "
        "duplicate providers are silently skipped."
    ),
)
async def import_settings(
    data: SettingsImport,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> UserSettingsResponse:
    svc = SettingsService(db)
    return await svc.import_settings(current_user.id, data)


# ── API Provider Config ───────────────────────────────────────────────────────


@router.get(
    "/settings/providers",
    response_model=ApiProviderListResponse,
    summary="List API providers",
    description="Return all configured API providers with masked keys.",
)
async def list_providers(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> ApiProviderListResponse:
    svc = SettingsService(db)
    items = await svc.list_providers(current_user.id)
    return ApiProviderListResponse(items=items)


@router.post(
    "/settings/providers",
    response_model=ApiProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add API provider",
    description=(
        "Add a new API provider configuration.  The API key is encrypted "
        "at rest and never exposed in API responses.  Raises 409 if a "
        "config for this provider already exists."
    ),
)
async def add_provider(
    data: ApiProviderCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> ApiProviderResponse:
    svc = SettingsService(db)
    try:
        return await svc.add_provider(current_user.id, data)
    except ProviderAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=exc.detail
        )


@router.patch(
    "/settings/providers/{provider_id}",
    response_model=ApiProviderResponse,
    summary="Update API provider",
    description=(
        "Partial update of an API provider config.  If a new ``api_key`` "
        "is provided, it is re-encrypted before storage."
    ),
)
async def update_provider(
    provider_id: uuid.UUID,
    data: ApiProviderUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> ApiProviderResponse:
    svc = SettingsService(db)
    try:
        return await svc.update_provider(provider_id, current_user.id, data)
    except ProviderNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail
        )


@router.delete(
    "/settings/providers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove API provider",
    description="Delete an API provider configuration.",
)
async def remove_provider(
    provider_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    svc = SettingsService(db)
    try:
        await svc.remove_provider(provider_id, current_user.id)
    except ProviderNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail
        )


@router.post(
    "/settings/providers/{provider_id}/validate",
    summary="Validate API provider key",
    description=(
        "Decrypt the stored API key and run a basic connectivity check "
        "against the provider's API.  Only validates key format and "
        "decryption — full provider-specific validation is a future enhancement."
    ),
)
async def validate_provider(
    provider_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    svc = SettingsService(db)
    try:
        return await svc.validate_provider_key(provider_id, current_user.id)
    except ProviderNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail
        )


# ── User Sessions ─────────────────────────────────────────────────────────────


@router.get(
    "/settings/sessions",
    response_model=UserSessionListResponse,
    summary="List active sessions",
    description=(
        "Return all active (non-revoked) sessions for the current user. "
        "The session matching the current refresh token is marked "
        "``is_current = true``."
    ),
)
async def list_sessions(
    request: Request,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> UserSessionListResponse:
    jti = _extract_jti_from_cookie(request)
    svc = SettingsService(db)
    items = await svc.list_sessions(current_user.id, current_jti=jti)
    return UserSessionListResponse(items=items)


@router.delete(
    "/settings/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a session",
    description="Revoke a specific user session by ID.",
)
async def revoke_session(
    session_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    svc = SettingsService(db)
    try:
        await svc.revoke_session(session_id, current_user.id)
    except SessionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail
        )


@router.delete(
    "/settings/sessions",
    status_code=status.HTTP_200_OK,
    summary="Revoke all other sessions",
    description=(
        "Revoke all sessions except the one associated with the current "
        "refresh token.  Returns the number of sessions revoked."
    ),
)
async def revoke_all_other_sessions(
    request: Request,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    jti = _extract_jti_from_cookie(request)
    if jti is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token found — cannot determine current session",
        )
    svc = SettingsService(db)
    count = await svc.revoke_all_other_sessions(current_user.id, jti)
    return {"revoked": count}


# ── Password Change ───────────────────────────────────────────────────────────


@router.post(
    "/settings/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description=(
        "Change the current user's password.  Requires the current "
        "password for verification.  The new password must be at least "
        "8 characters long."
    ),
)
async def change_password(
    data: PasswordChangeRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    svc = SettingsService(db)
    try:
        await svc.change_password(
            current_user.id, data.current_password, data.new_password
        )
    except PasswordIncorrect as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail
        )
    return {"message": "Password changed successfully"}
