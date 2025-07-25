from typing import Callable, Optional, Dict, Any
import logging
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.wallet_auth_provider import WalletAuthProvider
from app.services.auth_manager import AuthManager
from app.repositories.auth_repo import AuthRepository
from app.repositories.user_repo import UserRepository
from app.database import get_db_client

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate authentication for all protected routes.
    Public routes are excluded from authentication checks.
    """

    def __init__(self, app):
        """
        Initialize the middleware.

        Args:
            app: The FastAPI app
        """
        super().__init__(app)
        self.auth_manager = AuthManager()

        # Public routes that don't require authentication
        self.public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/validate",
            "/auth/logout",
            "/users/register",
            "/api-keys/status",  # API keys status endpoint is public
            "/delegation/server-info",  # Delegation server info is public
        ]
        
        # Routes that start with these prefixes are public
        self.public_prefixes = [
            "/docs/",
            "/redoc/",
            "/openapi/",
            "/auth/nonce/",  # Nonce endpoints for any wallet address
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch the request and check authentication for protected routes.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response from the next middleware or route handler
        """
        path = request.url.path
        method = request.method
        logger.debug(f"Received {method} request for path: {path}")
        
        # Special logging for batch upload completion calls
        if path == "/upload/batch/complete":
            logger.warning(f"🔥 BATCH COMPLETION CALL DETECTED - Method: {method}")
        if "/upload/" in path and method == "POST":
            logger.warning(f"🔥 UPLOAD POST CALL - Path: {path}, Method: {method}")

        # Skip authentication for OPTIONS requests (CORS preflight)
        if method == "OPTIONS":
            logger.debug(f"Skipping authentication for OPTIONS request to {path}")
            return await call_next(request)

        # Get session ID from cookies
        session_id = request.cookies.get("session_id")
        logger.debug(f"Session ID: {session_id}")

        # Skip authentication for public paths
        if self._is_public_path(path):
            logger.debug(f"Path {path} is public, skipping authentication")
            return await call_next(request)

        # Try to authenticate using the AuthManager
        try:
            auth_context = await self.auth_manager.authenticate(request)
        except HTTPException as http_exc:
            # Handle authentication errors (e.g., invalid API key format/signature)
            logger.warning(f"Authentication failed for {path}: {http_exc.detail}")
            return JSONResponse(
                status_code=http_exc.status_code,
                content={"detail": http_exc.detail}
            )
        except Exception as e:
            # Handle unexpected errors during authentication
            logger.error(f"Unexpected authentication error for {path}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal authentication error"}
            )

        if not auth_context:
            logger.warning(
                f"Authentication required for {path} but no valid credentials found"
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )

        # Add auth context to request state
        self._set_auth_state(request, auth_context)

        logger.debug(
            f"User {auth_context.get('wallet_address')} authenticated for {path} "
            f"via {auth_context.get('auth_method')}"
        )

        return await call_next(request)


    def _set_auth_state(self, request: Request, auth_context: Dict[str, Any]) -> None:
        """
        Set authentication state on the request.

        Args:
            request: The request object
            auth_context: Authentication context
        """
        request.state.auth_context = auth_context
        request.state.wallet_address = auth_context.get("wallet_address")
        request.state.auth_method = auth_context.get("auth_method")
        request.state.permissions = auth_context.get("permissions", [])

        # For backward compatibility
        if auth_context.get("session_data"):
            request.state.user = auth_context.get("session_data")

    def _is_public_path(self, path: str) -> bool:
        """
        Check if a path is public (doesn't require authentication).

        Args:
            path: The request path

        Returns:
            True if public, False if protected
        """
        logger.debug(f"Checking if path is public: {path}")

        # Check exact matches
        if path in self.public_paths:
            logger.debug(f"Path {path} matched exact public path")
            return True

        # Check prefix matches
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                logger.debug(f"Path {path} matched public prefix: {prefix}")
                return True

        logger.debug(f"Path {path} is NOT public")
        return False

    async def _validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session ID.

        Args:
            session_id: The session ID to validate

        Returns:
            Session data if valid, None otherwise
        """
        try:
            # Get database client
            db_client = get_db_client()

            # Initialize repositories and wallet auth provider
            auth_repo = AuthRepository(db_client)
            user_repo = UserRepository(db_client)
            wallet_auth_provider = WalletAuthProvider(auth_repo, user_repo)

            # Validate session
            session_data = await wallet_auth_provider.validate_session(session_id)
            if session_data:
                logger.debug(f"Session validated successfully: {session_id}")
                return session_data
            else:
                logger.debug(f"Invalid session ID: {session_id}")
                return None

        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return None


# Dependency functions for FastAPI routes

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get the current authenticated user from request state.
    Use this as a dependency in route handlers that need the current user.

    Args:
        request: The request object

    Returns:
        User data from session

    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "user") or not request.state.user:
        # For API key auth, we might not have full user data
        if hasattr(request.state, "auth_context") and request.state.auth_context:
            # Return a minimal user object for API key auth
            return {
                "walletAddress": request.state.auth_context.get("wallet_address"),
                "auth_method": request.state.auth_context.get("auth_method")
            }
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return request.state.user


async def get_wallet_address(request: Request) -> str:
    """
    Get the wallet address of the current authenticated user.
    Use this as a dependency in route handlers that only need the wallet address.

    Args:
        request: The request object

    Returns:
        Wallet address

    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "wallet_address") or not request.state.wallet_address:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return request.state.wallet_address


def check_permission(permission: str):
    """
    Create a dependency that checks for a specific permission.

    Args:
        permission: The required permission (read, write, delete)

    Returns:
        A dependency function that validates the permission
    """
    async def permission_checker(request: Request) -> Dict[str, Any]:
        if not hasattr(request.state, "auth_context") or not request.state.auth_context:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )

        permissions = request.state.auth_context.get("permissions", [])

        # Check specific permission
        if permission in permissions:
            return request.state.auth_context

        raise HTTPException(
            status_code=403,
            detail=f"Permission denied. Required permission: {permission}"
        )

    return permission_checker


async def get_wallet_only_user(request: Request) -> Dict[str, Any]:
    """
    Get the current authenticated user, but only allow wallet authentication.
    Use this as a dependency in route handlers that require wallet authentication
    and should not be accessible via API keys.

    Args:
        request: The request object

    Returns:
        User data from session

    Raises:
        HTTPException: If user is not authenticated or using API key authentication
    """
    if not hasattr(request.state, "auth_context") or not request.state.auth_context:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    auth_method = request.state.auth_context.get("auth_method")
    
    # Reject API key authentication
    if auth_method == "api_key":
        raise HTTPException(
            status_code=403,
            detail="Wallet authentication required. This endpoint is not accessible via API keys."
        )

    # For wallet authentication, return user data
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user
    
    # If no full user data but wallet authenticated, return minimal user object
    return {
        "walletAddress": request.state.auth_context.get("wallet_address"),
        "auth_method": auth_method
    }
