from typing import Optional, Dict, Any
import logging
from fastapi import HTTPException

from app.services.asset_service import AssetService
from app.services.blockchain_service import BlockchainService
from app.services.ipfs_service import IPFSService
from app.services.transaction_service import TransactionService
from app.schemas.retrieve_schema import MetadataRetrieveResponse, MetadataVerificationResult
from app.utilities.format import get_ipfs_metadata

logger = logging.getLogger(__name__)

class RetrieveHandler:
    """
    Handler for metadata retrieval operations.
    Verifies metadata integrity by comparing blockchain CID with computed CID.
    Retrieves authentic metadata from IPFS if tampering is detected.
    """
    
    def __init__(
        self,
        asset_service: AssetService,
        blockchain_service: BlockchainService,
        ipfs_service: IPFSService,
        transaction_service: TransactionService = None,
        auth_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize with required services.
        
        Args:
            asset_service: Service for asset operations
            blockchain_service: Service for blockchain operations
            ipfs_service: Service for IPFS operations
            transaction_service: Optional service for recording transactions
            auth_context: Authentication context for the current request
        """
        self.asset_service = asset_service
        self.blockchain_service = blockchain_service
        self.ipfs_service = ipfs_service
        self.transaction_service = transaction_service
        self.auth_context = auth_context
        
    async def retrieve_metadata(
        self,
        asset_id: str,
        version: Optional[int] = None,
        auto_recover: bool = True,
        initiator_address: Optional[str] = None
    ) -> MetadataRetrieveResponse:
        """
        Retrieve and verify metadata for an asset.
        
        Args:
            asset_id: The asset's unique identifier
            version: Optional specific version to retrieve
            auto_recover: Whether to automatically recover from tampering (only applies to latest version)
            initiator_address: Address of the user performing the operation (for delegation context)
            
        Returns:
            MetadataRetrieveResponse containing metadata and verification results
            
        Raises:
            HTTPException: If asset not found or retrieval fails
        """
        try:
            # 1. First check if the asset exists at all (with any version)
            any_version = await self.asset_service.get_asset_with_deleted(asset_id)
            
            if not any_version:
                raise HTTPException(status_code=404, detail=f"Asset with ID {asset_id} not found")
                
            # 2. Now fetch the specific version requested
            document = await self.asset_service.get_asset(asset_id, version)
            
            if not document:
                if version:
                    raise HTTPException(status_code=404, detail=f"Version {version} of asset {asset_id} not found or is deleted")
                else:
                    # This should not normally happen if any_version exists, unless the asset is deleted
                    raise HTTPException(status_code=404, detail=f"Current version of asset {asset_id} not found or is deleted")
                
            # Extract required fields
            doc_id = document["_id"]
            doc_version = document.get("versionNumber", 1)
            # Use ipfsVersion if available, otherwise fall back to versionNumber
            ipfs_version = document.get("ipfsVersion", doc_version)
            is_latest_version = document.get("isCurrent", False)
            wallet_address = document.get("walletAddress")
            blockchain_tx_id = document.get("smartContractTxId")
            ipfs_hash = document.get("ipfsHash")
            critical_metadata = document.get("criticalMetadata", {})
            non_critical_metadata = document.get("nonCriticalMetadata", {})
            
            # Initialize verification result
            verification_result = MetadataVerificationResult(
                verified=False,
                cid_match=False,
                blockchain_cid="unknown",
                computed_cid="unknown",
                recovery_needed=False,
                deletion_status_tampered=False
            )
            
            # 3. Use the contract's verification methods to verify the CID
            blockchain_cid = "unknown"
            ipfs_hash_verified = False
            try:
                # First get IPFS info from the blockchain
                blockchain_data = await self.blockchain_service.get_ipfs_info(
                    asset_id=asset_id,
                    owner_address=wallet_address
                )
                logger.info(f"Initial Blockchain Data: asset_id={asset_id}, version={blockchain_data.get('ipfs_version')}, deleted={blockchain_data.get('is_deleted')}")

                # Now verify the CID using the verifyCID function
                # Important: Use ipfs_version instead of doc_version for blockchain verification
                verify_result = await self.blockchain_service.verify_cid_on_chain(
                    asset_id=asset_id,
                    owner_address=wallet_address,
                    cid=ipfs_hash,
                    claimed_version=ipfs_version
                )
                
                # Set verification results from blockchain response
                verification_result.ipfs_version = verify_result["actual_version"]
                verification_result.is_deleted = verify_result["is_deleted"]
                verification_result.message = verify_result["message"]
                
                # Store result of IPFS hash verification (if stored ipfs_hash matches blockchain)
                ipfs_hash_verified = verify_result["is_valid"]
                
                # Get transaction details for additional verification
                tx_data = await self.blockchain_service.get_transaction_details(blockchain_tx_id, asset_id)
                blockchain_cid = tx_data.get("cid", "unknown")
                tx_sender = tx_data.get("tx_sender", None)

                # Set blockchain CID
                verification_result.blockchain_cid = blockchain_cid
                
                # Verify transaction sender if possible
                server_wallet = self.blockchain_service.get_server_wallet_address()
                
                if tx_sender and server_wallet:
                    # Convert both addresses to lowercase for case-insensitive comparison
                    tx_sender_lower = tx_sender.lower() if isinstance(tx_sender, str) else None
                    server_wallet_lower = server_wallet.lower() if isinstance(server_wallet, str) else None
                    
                    # Check if transaction sender matches server wallet address
                    tx_sender_verified = (tx_sender_lower and server_wallet_lower and 
                                        tx_sender_lower == server_wallet_lower)
                    
                    if not tx_sender_verified:
                        logger.warning(f"Transaction sender verification failed for {asset_id}. "
                                      f"Expected: {server_wallet_lower}, Found: {tx_sender_lower}")
                else:
                    tx_sender_verified = False
                    logger.warning(f"Transaction sender verification failed - missing data. " 
                                  f"tx_sender: {tx_sender}, server_wallet: {server_wallet}")
                
                verification_result.tx_sender_verified = tx_sender_verified
                
            except Exception as e:
                logger.error(f"Error verifying asset on blockchain: {str(e)}")
                verification_result.message = f"Blockchain verification failed: {str(e)}"
            
            # 4. Compute CID from MongoDB critical metadata
            metadata_for_ipfs = {
                "asset_id": asset_id,
                "wallet_address": wallet_address,
                "critical_metadata": critical_metadata
            }
            computed_cid = await self.ipfs_service.compute_cid(get_ipfs_metadata(metadata_for_ipfs))

            # 5. Set computed CID and compare with blockchain CID
            verification_result.computed_cid = computed_cid
            verification_result.cid_match = computed_cid == verification_result.blockchain_cid

            # Check specifically for deletion status tampering
            deletion_status_tampered = verification_result.is_deleted and not document.get("isDeleted", False)
            verification_result.deletion_status_tampered = deletion_status_tampered

            # Different verification logic for current vs. historical versions
            if is_latest_version:
                # For latest version, verify both the IPFS hash AND that the computed CID matches
                verification_result.verified = ipfs_hash_verified and verification_result.cid_match and not deletion_status_tampered
                verification_result.recovery_needed = not verification_result.verified
                
                if verification_result.verified:
                    logger.info(f"Verification Success: Current version of asset {asset_id}, version={doc_version}, ipfs_version={ipfs_version}")
                else:
                    logger.warning(f"Current version verification failed for asset {asset_id}, version {doc_version}, ipfs_version {ipfs_version}")
                    if deletion_status_tampered:
                        verification_result.message = "Tampering detected: Asset is marked as deleted on blockchain but not in MongoDB"
                    elif not ipfs_hash_verified:
                        if verification_result.is_deleted:
                            verification_result.message = "Asset is marked as deleted on blockchain"
                        else:
                            verification_result.message = "IPFS hash verification failed - stored hash doesn't match blockchain"
                    elif not verification_result.cid_match:
                        verification_result.message = "CID mismatch - computed CID from current data doesn't match blockchain CID"
            else:
                # For historical versions, use transaction history verification instead
                # Consider it verified if the transaction data matches the computed data
                verification_result.verified = verification_result.cid_match and verification_result.tx_sender_verified and not deletion_status_tampered
                verification_result.recovery_needed = not verification_result.verified
                
                if verification_result.verified:
                    logger.info(f"Verification Success: Historical version of asset {asset_id}, version={doc_version}, ipfs_version={ipfs_version}")
                    verification_result.message = "Historical version verified via transaction data"
                else:
                    logger.warning(f"Historical version verification failed for asset {asset_id}, version {doc_version}, ipfs_version {ipfs_version}")
                    if deletion_status_tampered:
                        verification_result.message = "Tampering detected: Asset is marked as deleted on blockchain but not in MongoDB"
                    elif verification_result.cid_match:
                        verification_result.message = "Historical transaction sender verification failed"
                    else:
                        verification_result.message = "Historical CID verification failed"
            
            # Additional logging if recovery needed
            if verification_result.recovery_needed:
                logger.warning(f"Verification failed for asset {asset_id}. "
                             f"CID match: {verification_result.cid_match}, IPFS hash verified: {ipfs_hash_verified}, "
                             f"needs recovery: {verification_result.recovery_needed}, deletion status tampered: {deletion_status_tampered}")
            
            # 6. If verification failed and auto-recover is enabled, try to recover
            new_version_created = False
            
            # Special handling for deletion status tampering
            if verification_result.deletion_status_tampered and auto_recover:
                try:
                    # Mark all versions of this asset as deleted in MongoDB
                    restored = await self.asset_service.soft_delete(asset_id, wallet_address)
                    
                    if restored:
                        # Record transaction if transaction service is available
                        if self.transaction_service:
                            performed_by = initiator_address if initiator_address and initiator_address.lower() != wallet_address.lower() else wallet_address
                            
                            await self.transaction_service.record_transaction(
                                asset_id=asset_id,
                                action="DELETION_STATUS_RESTORED",
                                wallet_address=wallet_address,
                                performed_by=performed_by,
                                metadata={
                                    "previous_doc_id": doc_id,
                                    "previous_version": doc_version,
                                    "recovery_source": "blockchain_verification",
                                    "auto_recover": auto_recover
                                }
                            )
                        
                        verification_result.recovery_successful = True
                        verification_result.message = "Asset deletion status restored from blockchain"
                        logger.info(f"Restored deletion status for asset {asset_id} based on blockchain verification")
                        
                        # No new version created, just status restored
                        verification_result.new_version_created = False
                        
                        # Refresh document to get updated deletion status
                        document = await self.asset_service.get_asset_with_deleted(asset_id, version)
                        if document:
                            # Update the response to reflect the corrected deletion status
                            critical_metadata = document.get("criticalMetadata", {})
                            non_critical_metadata = document.get("nonCriticalMetadata", {})
                    else:
                        verification_result.recovery_successful = False
                        verification_result.message = "Failed to restore deletion status"
                        logger.error(f"Failed to restore deletion status for asset {asset_id}")
                except Exception as e:
                    logger.error(f"Error restoring deletion status: {str(e)}")
                    verification_result.recovery_successful = False
                    verification_result.message = f"Error restoring deletion status: {str(e)}"
            
            # Regular recovery for other types of tampering
            elif verification_result.recovery_needed and auto_recover and is_latest_version and not verification_result.deletion_status_tampered:
                try:
                    # Retrieve authentic metadata from IPFS using blockchain CID
                    try:
                        authentic_metadata = await self.ipfs_service.retrieve_metadata(verification_result.blockchain_cid)
                    except Exception as ipfs_error:
                        logger.error(f"Failed to retrieve metadata from IPFS: {str(ipfs_error)}")
                        verification_result.recovery_successful = False
                        raise ipfs_error
                    
                    # Ensure we have the required fields
                    if not authentic_metadata or "critical_metadata" not in authentic_metadata:
                        logger.error(f"Failed to retrieve valid metadata from IPFS for CID {verification_result.blockchain_cid}")
                        verification_result.recovery_successful = False
                    else:
                        # Extract authentic critical metadata
                        authentic_critical_metadata = authentic_metadata.get("critical_metadata", {})
                        
                        # 7. Create new version with authentic data
                        new_doc_id = await self.asset_service.create_new_version(
                            asset_id=asset_id,
                            wallet_address=wallet_address,
                            smart_contract_tx_id=blockchain_tx_id,
                            ipfs_hash=verification_result.blockchain_cid,
                            critical_metadata=authentic_critical_metadata,
                            non_critical_metadata=non_critical_metadata,
                            ipfs_version=verification_result.ipfs_version
                        )
                        
                        # Get the new document to get its version number
                        new_doc = await self.asset_service.get_asset(asset_id)
                        new_version = new_doc.get("versionNumber", doc_version + 1)
                        
                        # Record transaction if transaction service is available
                        if self.transaction_service:
                            performed_by = initiator_address if initiator_address and initiator_address.lower() != wallet_address.lower() else wallet_address
                            
                            await self.transaction_service.record_transaction(
                                asset_id=asset_id,
                                action="INTEGRITY_RECOVERY",
                                wallet_address=wallet_address,
                                performed_by=performed_by,
                                metadata={
                                    "previous_doc_id": doc_id,
                                    "new_doc_id": new_doc_id,
                                    "previous_version": doc_version,
                                    "new_version": new_version,
                                    "previous_ipfs_version": ipfs_version,
                                    "new_ipfs_version": verification_result.ipfs_version,
                                    "blockchain_cid": verification_result.blockchain_cid,
                                    "computed_cid": computed_cid,
                                    "recovery_source": "ipfs",
                                    "tx_sender_verified": verification_result.tx_sender_verified,
                                    "auto_recover": auto_recover
                                }
                            )
                        
                        # Update response data
                        doc_id = new_doc_id["document_id"]
                        doc_version = new_version
                        critical_metadata = authentic_critical_metadata
                        new_version_created = True
                        verification_result.recovery_successful = True
                        
                except Exception as e:
                    logger.error(f"Error recovering metadata from IPFS: {str(e)}")
                    verification_result.recovery_successful = False
            
            # Set new version created flag in verification result
            verification_result.new_version_created = new_version_created
            
            # 8. Prepare response
            return MetadataRetrieveResponse(
                asset_id=asset_id,
                version=doc_version,
                critical_metadata=critical_metadata,
                non_critical_metadata=non_critical_metadata,
                verification=verification_result,
                document_id=doc_id,
                ipfs_hash=verification_result.blockchain_cid,
                blockchain_tx_id=blockchain_tx_id
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving metadata: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving metadata: {str(e)}")
