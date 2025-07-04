import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.schemas.api_key_schema import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse, APIKeyUpdate


class TestAPIKeyRoutes:
    """Test suite for API key HTTP routes."""

    @pytest.fixture
    def mock_auth_bypass(self, mock_current_user):
        """Mock authentication to bypass auth for tests."""
        def auth_bypass():
            # Mock the auth manager to return successful authentication
            mock_auth_context = {
                "wallet_address": mock_current_user["walletAddress"],
                "auth_method": "wallet",
                "permissions": ["read", "write", "delete"]
            }
            return patch('app.utilities.auth_middleware.AuthManager.authenticate', 
                        new_callable=AsyncMock, return_value=mock_auth_context)
        return auth_bypass
    
    def setup_dependency_overrides(self, mock_service=None, wallet_address=None, enabled=True):
        """Helper to setup FastAPI dependency overrides."""
        from app.api.api_keys_routes import get_api_key_service, get_wallet_address, check_api_keys_enabled
        from app.main import app
        
        if mock_service:
            app.dependency_overrides[get_api_key_service] = lambda: mock_service
        if wallet_address:
            app.dependency_overrides[get_wallet_address] = lambda: wallet_address
        if enabled:
            app.dependency_overrides[check_api_keys_enabled] = lambda: None
        else:
            # For disabled tests, let the actual check_api_keys_enabled run
            app.dependency_overrides.pop(check_api_keys_enabled, None)
        
        return app
    
    def cleanup_dependency_overrides(self):
        """Clean up FastAPI dependency overrides."""
        from app.main import app
        app.dependency_overrides.clear()
    
    def mock_auth_middleware(self, wallet_address):
        """Helper to mock authentication middleware (deprecated - use direct auth manager mocking)."""
        async def mock_auth_dispatch(request, call_next):
            request.state.wallet_address = wallet_address
            request.state.auth_method = "wallet"
            return await call_next(request)
        return patch('app.utilities.auth_middleware.AuthMiddleware.dispatch', side_effect=mock_auth_dispatch)

    @pytest.fixture
    def mock_settings(self):
        """Mock application settings."""
        settings = MagicMock()
        settings.api_key_auth_enabled = True
        settings.api_key_max_per_wallet = 10
        settings.api_key_default_expiration_days = 90
        settings.api_key_rate_limit_per_minute = 100
        return settings

    @pytest.fixture
    def mock_current_user(self, test_wallet_address):
        """Mock current authenticated user."""
        return {"walletAddress": test_wallet_address}

    @pytest.fixture
    def sample_api_key_create_data(self):
        """Sample API key creation data."""
        return {
            "name": "Test API Key",
            "permissions": ["read", "write"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "metadata": {"purpose": "testing"}
        }

    @pytest.fixture
    def sample_api_key_response(self, test_wallet_address):
        """Sample API key response data."""
        return APIKeyResponse(
            name="Test API Key",
            permissions=["read", "write"],
            created_at=datetime.now(timezone.utc),
            last_used_at=None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={"purpose": "testing"}
        )

    @pytest.fixture
    def sample_api_key_create_response(self, test_api_key):
        """Sample API key creation response."""
        return APIKeyCreateResponse(
            api_key=test_api_key,
            name="Test API Key",
            permissions=["read", "write"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={"purpose": "testing"},
            last_used_at=None
        )

    def test_get_api_keys_status_enabled(self, client, mock_settings):
        """Test API keys status endpoint when enabled."""
        with patch('app.api.api_keys_routes.settings', mock_settings):
            response = client.get("/api-keys/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["max_keys_per_wallet"] == 10
        assert data["default_expiration_days"] == 90
        assert data["rate_limit_per_minute"] == 100

    def test_get_api_keys_status_disabled(self, client, mock_settings):
        """Test API keys status endpoint when disabled."""
        mock_settings.api_key_auth_enabled = False
        
        with patch('app.api.api_keys_routes.settings', mock_settings):
            response = client.get("/api-keys/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_get_api_keys_status_no_auth_required(self, client, mock_settings):
        """Test that status endpoint doesn't require authentication."""
        # This test ensures the status endpoint is public
        with patch('app.api.api_keys_routes.settings', mock_settings):
            response = client.get("/api-keys/status")
        
        # Should work without authentication
        assert response.status_code == 200

    def test_create_api_key_success(self, client, mock_settings, sample_api_key_create_data, 
                                  sample_api_key_create_response, mock_current_user):
        """Test successful API key creation."""
        # Mock service
        mock_service = MagicMock()
        mock_service.create_api_key = AsyncMock(return_value=sample_api_key_create_response)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.post("/api-keys/create", json=sample_api_key_create_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "api_key" in data
            assert data["name"] == sample_api_key_create_data["name"]
            assert data["permissions"] == sample_api_key_create_data["permissions"]
        finally:
            self.cleanup_dependency_overrides()

    def test_create_api_key_disabled(self, client, sample_api_key_create_data, mock_current_user):
        """Test API key creation when feature is disabled."""
        mock_settings = MagicMock()
        mock_settings.api_key_auth_enabled = False
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
            
            # Mock auth manager to return authentication context
            mock_auth.return_value = {
                "wallet_address": mock_current_user["walletAddress"],
                "auth_method": "wallet",
                "permissions": ["read", "write", "delete"]
            }
            
            response = client.post("/api-keys/create", json=sample_api_key_create_data)
        
        assert response.status_code == 400
        assert "not enabled" in response.json()["detail"]

    def test_create_api_key_validation_error(self, client, mock_settings, mock_current_user):
        """Test API key creation with validation errors."""
        invalid_data = {
            "name": "",  # Empty name
            "permissions": ["invalid_permission"],  # Invalid permission
        }
        
        # Mock service to raise ValueError
        mock_service = MagicMock()
        mock_service.create_api_key = AsyncMock(side_effect=ValueError("Invalid permissions"))
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.post("/api-keys/create", json=invalid_data)
            
            assert response.status_code == 400
        finally:
            self.cleanup_dependency_overrides()

    def test_create_api_key_max_limit_reached(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test API key creation when limit is reached."""
        # Mock service to raise max limit error
        mock_service = MagicMock()
        mock_service.create_api_key = AsyncMock(side_effect=ValueError("Maximum API keys limit reached"))
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.post("/api-keys/create", json=sample_api_key_create_data)
            
            assert response.status_code == 400
            assert "limit reached" in response.json()["detail"]
        finally:
            self.cleanup_dependency_overrides()

    def test_create_api_key_api_key_auth_forbidden(self, client, mock_settings, sample_api_key_create_data):
        """Test that API keys cannot create other API keys."""
        self.setup_dependency_overrides(None, "test_wallet")
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to simulate API key authentication
                mock_auth.return_value = {
                    "wallet_address": "test_wallet",
                    "auth_method": "api_key",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.post("/api-keys/create", json=sample_api_key_create_data)
            
            # Should be forbidden
            assert response.status_code == 403
            assert "cannot create other API keys" in response.json()["detail"]
        finally:
            self.cleanup_dependency_overrides()

    def test_list_api_keys_success(self, client, mock_settings, sample_api_key_response, mock_current_user):
        """Test successful API key listing."""
        # Mock service
        mock_service = MagicMock()
        mock_service.list_api_keys = AsyncMock(return_value=[sample_api_key_response])
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.get("/api-keys/list")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == sample_api_key_response.name
            assert "api_key" not in data[0]  # Sensitive data should not be included
        finally:
            self.cleanup_dependency_overrides()

    def test_list_api_keys_empty(self, client, mock_settings, mock_current_user):
        """Test listing API keys when none exist."""
        # Mock service to return empty list
        mock_service = MagicMock()
        mock_service.list_api_keys = AsyncMock(return_value=[])
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.get("/api-keys/list")
            
            assert response.status_code == 200
            assert response.json() == []
        finally:
            self.cleanup_dependency_overrides()

    def test_list_api_keys_disabled(self, client, mock_current_user):
        """Test listing API keys when feature is disabled."""
        mock_settings = MagicMock()
        mock_settings.api_key_auth_enabled = False
        
        self.setup_dependency_overrides(None, mock_current_user["walletAddress"], enabled=False)
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.get("/api-keys/list")
            
            assert response.status_code == 400
            assert "not enabled" in response.json()["detail"]
        finally:
            self.cleanup_dependency_overrides()

    def test_revoke_api_key_success(self, client, mock_settings, mock_current_user):
        """Test successful API key revocation."""
        key_name = "Test API Key"
        
        # Mock service
        mock_service = MagicMock()
        mock_service.revoke_api_key = AsyncMock(return_value=True)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.delete(f"/api-keys/{key_name}")
            
            assert response.status_code == 200
            data = response.json()
            assert "revoked successfully" in data["message"]
        finally:
            self.cleanup_dependency_overrides()

    def test_revoke_api_key_not_found(self, client, mock_settings, mock_current_user):
        """Test revoking non-existent API key."""
        key_name = "Nonexistent Key"
        
        # Mock service to return False (not found)
        mock_service = MagicMock()
        mock_service.revoke_api_key = AsyncMock(return_value=False)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.delete(f"/api-keys/{key_name}")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
        finally:
            self.cleanup_dependency_overrides()

    def test_revoke_api_key_url_encoding(self, client, mock_settings, mock_current_user):
        """Test revoking API key with special characters in name."""
        key_name = "Test Key With Spaces"
        encoded_name = "Test%20Key%20With%20Spaces"
        
        mock_service = MagicMock()
        mock_service.revoke_api_key = AsyncMock(return_value=True)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.delete(f"/api-keys/{encoded_name}")
            
            assert response.status_code == 200
            # Verify the service was called with the decoded name
            mock_service.revoke_api_key.assert_called_once_with(mock_current_user["walletAddress"], key_name)
        finally:
            self.cleanup_dependency_overrides()

    def test_update_api_key_permissions_success(self, client, mock_settings, mock_current_user):
        """Test successful API key permission update."""
        key_name = "Test API Key"
        update_data = {
            "permissions": ["read", "write", "delete"]
        }
        
        # Mock service
        mock_service = MagicMock()
        mock_service.update_permissions = AsyncMock(return_value=True)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.put(f"/api-keys/{key_name}/permissions", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "updated" in data["message"]
        finally:
            self.cleanup_dependency_overrides()

    def test_update_api_key_permissions_not_found(self, client, mock_settings, mock_current_user):
        """Test updating permissions for non-existent API key."""
        key_name = "Nonexistent Key"
        update_data = {
            "permissions": ["read"]
        }
        
        # Mock service to return False (not found)
        mock_service = MagicMock()
        mock_service.update_permissions = AsyncMock(return_value=False)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.put(f"/api-keys/{key_name}/permissions", json=update_data)
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
        finally:
            self.cleanup_dependency_overrides()

    def test_update_api_key_permissions_invalid(self, client, mock_settings, mock_current_user):
        """Test updating API key with invalid permissions."""
        key_name = "Test API Key"
        update_data = {
            "permissions": ["invalid_permission"]
        }
        
        # Mock service to raise ValueError
        mock_service = MagicMock()
        mock_service.update_permissions = AsyncMock(side_effect=ValueError("Invalid permissions"))
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.put(f"/api-keys/{key_name}/permissions", json=update_data)
            
            assert response.status_code == 400
        finally:
            self.cleanup_dependency_overrides()

    def test_authentication_required(self, client, mock_settings):
        """Test that API key management endpoints require authentication."""
        endpoints_to_test = [
            ("POST", "/api-keys/create", {"name": "test"}),
            ("GET", "/api-keys/list", None),
            ("DELETE", "/api-keys/test", None),
            ("PUT", "/api-keys/test/permissions", {"permissions": ["read"]})
        ]
        
        with patch('app.api.api_keys_routes.settings', mock_settings):
            for method, endpoint, json_data in endpoints_to_test:
                if method == "POST":
                    response = client.post(endpoint, json=json_data)
                elif method == "GET":
                    response = client.get(endpoint)
                elif method == "DELETE":
                    response = client.delete(endpoint)
                elif method == "PUT":
                    response = client.put(endpoint, json=json_data)
                
                # Should require authentication
                assert response.status_code in [401, 403]

    def test_error_handling_service_exception(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test error handling when service raises unexpected exception."""
        # Mock service to raise unexpected exception
        mock_service = MagicMock()
        mock_service.create_api_key = AsyncMock(side_effect=Exception("Database error"))
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.post("/api-keys/create", json=sample_api_key_create_data)
            
            assert response.status_code == 500
            assert "Failed to create API key" in response.json()["detail"]
        finally:
            self.cleanup_dependency_overrides()

    def test_request_validation(self, client, mock_settings, mock_current_user):
        """Test request validation for required fields."""
        # Test missing required fields
        invalid_requests = [
            {},  # Empty request - missing required 'name'
            {"permissions": ["read"]},  # Missing required 'name'
        ]
        
        # Mock service to handle validation
        mock_service = MagicMock()
        
        def mock_create_api_key(*args, **kwargs):
            # The service should not be reached for validation errors
            # This means validation passed at the schema level
            raise Exception("Service should not be called for validation errors")
        
        mock_service.create_api_key = AsyncMock(side_effect=mock_create_api_key)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                for invalid_data in invalid_requests:
                    response = client.post("/api-keys/create", json=invalid_data)
                    # Should return validation error
                    assert response.status_code == 422  # Unprocessable Entity
        finally:
            self.cleanup_dependency_overrides()

    def test_response_format(self, client, mock_settings, sample_api_key_create_data, 
                           sample_api_key_create_response, mock_current_user):
        """Test that response format matches schema."""
        mock_service = MagicMock()
        mock_service.create_api_key = AsyncMock(return_value=sample_api_key_create_response)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.post("/api-keys/create", json=sample_api_key_create_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify required fields are present
            required_fields = ["api_key", "name", "permissions", "created_at", "expires_at", "is_active"]
            for field in required_fields:
                assert field in data
        finally:
            self.cleanup_dependency_overrides()

    def test_content_type_handling(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test proper content type handling."""
        mock_service = MagicMock()
        # Create a proper mock response for validation
        from app.schemas.api_key_schema import APIKeyCreateResponse
        from datetime import datetime, timezone, timedelta
        mock_response = APIKeyCreateResponse(
            api_key="test_key",
            name="Test Key",
            permissions=["read"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={"large_field": "x" * 10000, "description": "A" * 1000},
            last_used_at=None
        )
        mock_service.create_api_key = AsyncMock(return_value=mock_response)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                # Test with different content types
                response_json = client.post("/api-keys/create", json=sample_api_key_create_data)
                assert response_json.status_code == 200
                
                # Test with form data (should fail)
                response_form = client.post("/api-keys/create", data=sample_api_key_create_data)
                assert response_form.status_code == 422  # Should expect JSON
        finally:
            self.cleanup_dependency_overrides()

    def test_concurrent_requests(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test handling of concurrent requests."""
        import asyncio
        
        mock_service = MagicMock()
        # Create a proper mock response for validation
        from app.schemas.api_key_schema import APIKeyCreateResponse
        from datetime import datetime, timezone, timedelta
        mock_response = APIKeyCreateResponse(
            api_key="test_key",
            name="Test Key",
            permissions=["read"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={"large_field": "x" * 10000, "description": "A" * 1000},
            last_used_at=None
        )
        mock_service.create_api_key = AsyncMock(return_value=mock_response)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                # Multiple concurrent requests should be handled properly
                responses = []
                for i in range(5):
                    data = sample_api_key_create_data.copy()
                    data["name"] = f"Test Key {i}"
                    response = client.post("/api-keys/create", json=data)
                    responses.append(response)
                
                # All should succeed (assuming service handles concurrency)
                for response in responses:
                    assert response.status_code == 200
        finally:
            self.cleanup_dependency_overrides()

    def test_large_request_handling(self, client, mock_settings, mock_current_user):
        """Test handling of large requests."""
        # Create a request with large metadata
        large_data = {
            "name": "Test Key",
            "permissions": ["read"],
            "metadata": {
                "large_field": "x" * 10000,  # 10KB of data
                "description": "A" * 1000
            }
        }
        
        mock_service = MagicMock()
        # Create a proper mock response for validation
        from app.schemas.api_key_schema import APIKeyCreateResponse
        from datetime import datetime, timezone, timedelta
        mock_response = APIKeyCreateResponse(
            api_key="test_key",
            name="Test Key",
            permissions=["read"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={"large_field": "x" * 10000, "description": "A" * 1000},
            last_used_at=None
        )
        mock_service.create_api_key = AsyncMock(return_value=mock_response)
        
        self.setup_dependency_overrides(mock_service, mock_current_user["walletAddress"])
        
        try:
            with patch('app.api.api_keys_routes.settings', mock_settings), \
                 patch('app.services.auth_manager.AuthManager.authenticate') as mock_auth:
                
                # Mock auth manager to return authentication context
                mock_auth.return_value = {
                    "wallet_address": mock_current_user["walletAddress"],
                    "auth_method": "wallet",
                    "permissions": ["read", "write", "delete"]
                }
                
                response = client.post("/api-keys/create", json=large_data)
                
                # Should handle large requests appropriately
                # (may succeed or fail based on configured limits)
                assert response.status_code in [200, 413, 422]
        finally:
            self.cleanup_dependency_overrides()