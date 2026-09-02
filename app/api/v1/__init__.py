# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1.endpoints import scanner

api_router = APIRouter()
api_router.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
