from fastapi import APIRouter, Depends, Request
from typing import Dict, Any, List
import logging

from app.schemas.asset_schema import AssetListResponse
from app.services.asset_service import AssetService
from app.repositories.asset_repo import AssetRepository
from app.database import get_db_client
from app.utilities.auth_middleware import get_current_user, get_wallet_address

# Setup router
router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_asset_service(db_client=Depends(get_db_client)) -> AssetService:
    """Dependency to get the asset service with required dependencies."""
    asset_repo = AssetRepository(db_client)
    return AssetService(asset_repo)

@router.get("/user/{wallet_address}", response_model=AssetListResponse)
async def get_user_assets(
    wallet_address: str,
    request: Request,
    asset_service: AssetService = Depends(get_asset_service)
) -> AssetListResponse:
    """
    Get all assets owned by a specific wallet address.
    
    Args:
        wallet_address: The wallet address to get assets for
        request: The request object
        asset_service: The asset service
        
    Returns:
        AssetListResponse containing the list of assets owned by the wallet
    """
    try:
        # Check if request has authenticated user
        is_authenticated = hasattr(request.state, "user") and request.state.user is not None
        
        if is_authenticated:
            # Validate that authenticated user can access these assets
            authenticated_wallet = request.state.user.get("walletAddress")
            is_own_assets = authenticated_wallet.lower() == wallet_address.lower()
            
            # Only allow users to access their own assets
            # Future enhancement: Add role-based access control
            if not is_own_assets:
                logger.warning(f"Unauthorized access attempt: {authenticated_wallet} tried to access assets of {wallet_address}")
                return {"status": "success", "assets": []}
        
        # Get assets (will work in both authenticated and demo modes)
        assets = await asset_service.get_user_assets(wallet_address)
        return {"status": "success", "assets": assets}
    except Exception as e:
        logger.error(f"Error getting user assets: {str(e)}")
        # Return empty list instead of error to match frontend expectations
        return {"status": "success", "assets": []}