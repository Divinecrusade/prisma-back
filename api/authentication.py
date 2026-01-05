"""
Authentication module with token-based authentication.
Uses hardcoded admin credentials for now.
"""
import secrets
import time
from functools import wraps
from rest_framework import status
from rest_framework.response import Response

# Hardcoded admin credentials (replace with proper user system in production)
ADMIN_CREDENTIALS = {
    'email': 'admin@example.com',
    'password': 'admin123',
}

# Simple in-memory token store (use Redis/DB in production)
# Format: {token: {'user': {...}, 'expires': timestamp}}
_tokens = {}

# Token expiry time (24 hours)
TOKEN_EXPIRY = 60 * 60 * 24


def _cleanup_expired_tokens():
    """Remove expired tokens."""
    now = time.time()
    expired = [token for token, data in _tokens.items() if data['expires'] < now]
    for token in expired:
        del _tokens[token]


def authenticate_admin(email: str, password: str) -> dict | None:
    """
    Authenticate admin with hardcoded credentials.
    Returns user dict if valid, None otherwise.
    """
    if email == ADMIN_CREDENTIALS['email'] and password == ADMIN_CREDENTIALS['password']:
        return {
            'email': email,
            'is_admin': True,
        }
    return None


def create_token(user: dict) -> str:
    """Create a new auth token for user."""
    _cleanup_expired_tokens()
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        'user': user,
        'expires': time.time() + TOKEN_EXPIRY,
    }
    return token


def login_admin(email: str, password: str) -> tuple[dict, str] | tuple[None, None]:
    """
    Authenticate and create token for admin user.
    Returns (user, token) if successful, (None, None) otherwise.
    """
    user = authenticate_admin(email, password)
    if user:
        token = create_token(user)
        return user, token
    return None, None


def logout_admin(token: str) -> None:
    """Invalidate token."""
    _tokens.pop(token, None)


def get_token_from_request(request) -> str | None:
    """Extract token from Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def get_current_user(request) -> dict | None:
    """Get current authenticated user from token."""
    token = get_token_from_request(request)
    if not token:
        return None
    
    _cleanup_expired_tokens()
    token_data = _tokens.get(token)
    if token_data:
        return token_data['user']
    return None


def is_authenticated(request) -> bool:
    """Check if request has valid auth token."""
    return get_current_user(request) is not None


def admin_required(view_func):
    """
    Decorator for views that require admin authentication.
    Returns 401 if not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_authenticated(request):
            return Response(
                {'error': 'Authentication required', 'authenticated': False},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return view_func(request, *args, **kwargs)
    return wrapper
