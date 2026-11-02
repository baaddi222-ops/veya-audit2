"""
Central error mapping — the Django/DRF equivalent of
lib/core/error/failure.dart from the Flutter phase.

Every exception DRF would otherwise turn into a raw traceback or a bare
`{"detail": "..."}` is mapped here into one consistent, non-leaking shape:

    {"error": {"code": "validation_error", "message": "human-safe text"}}

No SQLSTATE, no Python traceback, no internal exception class name ever
reaches the client — the same "map at the boundary" discipline the
repository layer enforced in the Flutter/Supabase phase (0.1-E §17).
"""
import logging

from django.db import IntegrityError
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('veya')


def veya_exception_handler(exc, context):
    # Let DRF handle what it already handles well (validation, auth,
    # throttling, 404/403 conversion) — just reshape the response.
    response = exception_handler(exc, context)

    if response is not None:
        code = None
        if isinstance(response.data, dict):
            code = getattr(response.data.get('detail'), 'code', None)
        code = code or getattr(exc, 'default_code', None) or 'error'
        error = {'code': code, 'message': _flatten_detail(response.data)}
        if isinstance(exc, drf_exceptions.ValidationError) and isinstance(response.data, dict):
            # Per-field messages so the client can show them next to inputs.
            error['fields'] = {k: _flatten_detail(v) for k, v in response.data.items()}
        response.data = {'error': error}
        return response

    # Anything DRF didn't handle: log full detail server-side only and
    # return a generic, safe message — never the raw exception text.
    if isinstance(exc, IntegrityError):
        logger.error('Unhandled IntegrityError', exc_info=exc)
        return Response(
            {'error': {'code': 'conflict', 'message': 'That value is already in use.'}},
            status=409,
        )

    logger.error('Unmapped exception', exc_info=exc)
    return Response(
        {'error': {'code': 'unknown', 'message': 'Something went wrong. Please try again.'}},
        status=500,
    )


def _flatten_detail(data):
    if isinstance(data, dict):
        for value in data.values():
            flattened = _flatten_detail(value)
            if flattened:
                return flattened
        return 'Invalid request.'
    if isinstance(data, list):
        return _flatten_detail(data[0]) if data else 'Invalid request.'
    return str(data)
