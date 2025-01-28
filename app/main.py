from fastapi import FastAPI
from app.routes.route_sc import router as sc_router
from app.routes.route_db import router as db_router
from app.routes.route_ipfs import router as ipfs_router


# Initialize FastAPI app
app = FastAPI()

for router in sc_router, db_router, ipfs_router:
    app.include_router(router)