from __future__ import annotations

from .app_error import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)


class UserNotFoundError(NotFoundError):
    code = "user_not_found"
    default_message = "Unknown user"


class ApiKeyNotFoundError(NotFoundError):
    code = "api_key_not_found"
    default_message = "Unknown API key"


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"
    default_message = "Invalid credentials"


class MissingSessionTokenError(AuthenticationError):
    code = "missing_session_token"
    default_message = "Missing session token"


class InvalidSessionTokenError(AuthenticationError):
    code = "invalid_session_token"
    default_message = "Invalid session token"


class ExpiredSessionTokenError(AuthenticationError):
    code = "expired_session_token"
    default_message = "Session token expired"


class InactiveUserError(AuthorizationError):
    code = "inactive_user"
    default_message = "User account is inactive"


class ApiAccessDisabledError(AuthorizationError):
    code = "api_access_disabled"
    default_message = "API key access is disabled for this account"


class AdminAccessRequiredError(AuthorizationError):
    code = "admin_access_required"
    default_message = "Admin access required"


class CsrfOriginDeniedError(AuthorizationError):
    code = "csrf_origin_denied"
    default_message = "CSRF origin check failed"


class InternalServiceAuthError(AuthorizationError):
    code = "internal_service_auth_failed"
    default_message = "Internal service authentication failed"


class DuplicateUserRegistrationError(ConflictError):
    code = "duplicate_user_registration"
    default_message = "Email or pseudo already registered"


class ApiKeyAllocationError(ConflictError):
    code = "api_key_allocation_failed"
    default_message = "Unable to allocate a stable worker number for this API key"


class InvalidPseudoError(UnprocessableEntityError):
    code = "invalid_pseudo"
    default_message = "Invalid pseudo"


class WeakPasswordError(UnprocessableEntityError):
    code = "weak_password"
    default_message = "Password does not match the security policy"


class RateLimitExceededError(AppError):
    status_code = 429
    code = "rate_limit_exceeded"
    default_message = "Too many requests"
