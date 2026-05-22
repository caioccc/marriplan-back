import logging
from typing import Any

try:
    import sentry_sdk
except ImportError:  # pragma: no cover - sentry is optional in local/dev setups
    sentry_sdk = None


audit_logger = logging.getLogger('app.audit')


def _get_username(user: Any) -> str:
    if not user:
        return 'anonymous'
    username = getattr(user, 'username', None)
    if username:
        return str(username)
    email = getattr(user, 'email', None)
    return str(email) if email else 'anonymous'


def _describe_object(obj: Any) -> str:
    if obj is None:
        return '-'
    for attr in ('pk', 'id'):
        value = getattr(obj, attr, None)
        if value is not None:
            return f'{obj.__class__.__name__}#{value}'
    return obj.__class__.__name__


def audit_log(action: str, *, user=None, obj=None, status: str = 'success', message: str = '', **details: Any) -> None:
    audit_logger.info(
        '%s | status=%s | user=%s | object=%s | %s | data=%s',
        action,
        status,
        _get_username(user),
        _describe_object(obj),
        message,
        details or {},
    )


def audit_exception(action: str, *, user=None, obj=None, message: str = '', exc: Exception | None = None, **details: Any) -> None:
    audit_logger.error(
        '%s | status=error | user=%s | object=%s | %s | data=%s',
        action,
        _get_username(user),
        _describe_object(obj),
        message,
        details or {},
        exc_info=True,
    )
    if sentry_sdk and exc is not None:
        with sentry_sdk.push_scope() as scope:
            if user:
                scope.set_user({
                    'id': getattr(user, 'id', None),
                    'username': getattr(user, 'username', None),
                    'email': getattr(user, 'email', None),
                })
            if obj is not None:
                scope.set_context('object', {'type': obj.__class__.__name__, 'id': getattr(obj, 'pk', None)})
            if details:
                scope.set_context('details', details)
            sentry_sdk.capture_exception(exc)