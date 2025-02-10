import logging
from fastapi import APIRouter, HTTPException
from app.mongodb_client import MongoDBClient

router = APIRouter(prefix="/transactions", tags=["transactions"])
db_client = MongoDBClient()

@router.get("/document/{document_id}")
async def get_document_history(document_id: str):
    """Get transaction history for a specific document"""
    try:
        transactions = db_client.transaction_collection.find(
            {"documentId": document_id}
        ).sort("timestamp", -1)
        
        # Convert ObjectId to string and format the response
        transaction_list = []
        for tx in transactions:
            tx['_id'] = str(tx['_id'])
            tx['timestamp'] = tx['timestamp'].isoformat()
            transaction_list.append(tx)
            
        return {"transactions": transaction_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallet/{wallet_address}")
async def get_wallet_history(wallet_address: str):
    """Get transaction history for a specific wallet"""
    try:
        transactions = db_client.transaction_collection.find(
            {"walletAddress": wallet_address}
        ).sort("timestamp", -1)
        
        transaction_list = []
        for tx in transactions:
            tx['_id'] = str(tx['_id'])
            tx['timestamp'] = tx['timestamp'].isoformat()
            transaction_list.append(tx)
            
        return {"transactions": transaction_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))