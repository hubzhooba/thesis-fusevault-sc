import hashlib
import os
import logging
from web3 import Web3
from dotenv import load_dotenv
from typing import Any, Dict
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class BlockchainService:
    def __init__(self):
        load_dotenv()
        self.infura_url = os.getenv("INFURA_URL")
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        self.private_key = os.getenv("PRIVATE_KEY")
        self.contract_address = os.getenv("CONTRACT_ADDRESS")
        self.contract_abi = [
            {
                "inputs": [{"internalType": "string", "name": "cid", "type": "string"}],
                "name": "storeCIDDigest",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

        self.web3 = Web3(Web3.HTTPProvider(self.infura_url))

        if not self.web3.is_connected():
            logger.error("Unable to connect to Infura.")
            raise HTTPException(status_code=500, detail="Blockchain connection error")

        try:
            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=self.contract_abi
            )
        except Exception as e:
            logger.error(f"Error setting up contract: {str(e)}")
            raise

    async def store_hash(self, cid: str) -> Dict[str, Any]:
        try:
            # Compute SHA-256 digest
            digest = hashlib.sha256(cid.encode()).hexdigest()

            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.storeCIDDigest(digest).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)

            # Debug the signed_tx object to see what attributes are available
            logger.debug(f"Signed transaction attributes: {dir(signed_tx)}")

            # Different versions of Web3.py use different attribute names
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                try:
                    # Try to extract the raw transaction data in other ways
                    if hasattr(signed_tx, '__dict__'):
                        for key, value in signed_tx.__dict__.items():
                            if isinstance(value, (bytes, bytearray)):
                                raw_tx = value
                                break
                    # If we can't find any bytes attribute, convert the entire object to bytes
                    raw_tx = bytes(signed_tx)
                except:
                    raise ValueError("Could not extract raw transaction bytes. "
                                    "Check Web3.py version compatibility.")

            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"CID successfully stored on blockchain. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")
