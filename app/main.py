from fastapi import FastAPI
from app.core.route_sc import router as sc_router
from app.core.route_db import router as db_router
from app.core.route_ipfs import router as ipfs_router
from app.utilities.route_verify import router as verify_router
from app.connectors.route_storage import router as storage_router
from app.external.route_auth import router as auth_router
from app.external.route_transactions import router as transactions_router
from app.external.route_sessions import router as session_router

app = FastAPI(title="FuseVault API")

routers = [
    sc_router,
    db_router,
    ipfs_router,
    verify_router,
    storage_router,
    auth_router,
    transactions_router,
    session_router
]

for router in routers:
    app.include_router(router)