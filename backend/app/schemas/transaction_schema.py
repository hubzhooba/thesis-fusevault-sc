from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class TransactionBase(BaseModel):
    asset_id: str = Field(..., description="ID of the asset involved in the transaction", alias="assetId")
    action: str = Field(..., description="Type of action (CREATE, UPDATE, VERSION_CREATE, etc.)")
    wallet_address: str = Field(..., description="Wallet address that performed the action", alias="walletAddress")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the transaction")

class TransactionRequest(TransactionBase):
    pass

class TransactionResponse(BaseModel):
    transaction: Dict[str, Any] = Field(..., description="Transaction details")
    asset_info: Optional[Dict[str, Any]] = Field(None, description="Associated asset information", alias="assetInfo")

    class Config:
        populate_by_name = True

class TransactionHistoryResponse(BaseModel):
    asset_id: str = Field(..., description="Asset ID", alias="assetId")
    version: Optional[int] = Field(None, description="Version number if filtered")
    transactions: List[Dict[str, Any]] = Field(..., description="List of transactions for this asset")
    transaction_count: int = Field(..., description="Number of transactions", alias="transactionCount")

    class Config:
        populate_by_name = True

class WalletHistoryResponse(BaseModel):
    wallet_address: str = Field(..., description="Wallet address", alias="walletAddress")
    include_all_versions: bool = Field(..., description="Whether all versions are included", alias="includeAllVersions")
    transactions: List[Dict[str, Any]] = Field(..., description="List of transactions")
    transaction_count: int = Field(..., description="Number of transactions", alias="transactionCount")
    unique_assets: int = Field(..., description="Number of unique assets", alias="uniqueAssets")
    action_summary: Dict[str, int] = Field(..., description="Summary of actions by type", alias="actionSummary")

    class Config:
        populate_by_name = True

class TransactionRecordResponse(BaseModel):
    status: str = Field(..., description="Status of the record operation")
    message: str = Field(..., description="Message describing the result")
    transaction_id: str = Field(..., description="ID of the recorded transaction", alias="transactionId")
    asset_id: str = Field(..., description="ID of the asset involved", alias="assetId")
    action: str = Field(..., description="Type of action recorded")
    wallet_address: str = Field(..., description="Wallet address that performed the action", alias="walletAddress")

    class Config:
        populate_by_name = True

class TransactionSummaryResponse(BaseModel):
    wallet_address: str = Field(..., description="Wallet address", alias="walletAddress")
    summary: Dict[str, Any] = Field(..., description="Summary information")

    class Config:
        populate_by_name = True
