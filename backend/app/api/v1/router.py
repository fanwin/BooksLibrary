"""
API路由注册
"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.books import router as books_router
from app.api.v1.borrows import router as borrows_router
from app.api.v1.reservations_fines import router as reservations_fines_router
from app.api.v1.statistics import router as statistics_router
from app.api.v1.system import router as system_router
from app.api.v1.roles import router as roles_router
from app.api.v1.ratings import router as ratings_router

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth_router)
api_router.include_router(books_router)
api_router.include_router(borrows_router)
api_router.include_router(reservations_fines_router)
api_router.include_router(statistics_router)
api_router.include_router(system_router)
api_router.include_router(roles_router)
api_router.include_router(ratings_router)
