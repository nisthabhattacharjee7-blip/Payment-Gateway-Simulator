from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config.settings import settings
from app.middlewares.idempotency_middleware import IdempotentReplayResponse
from app.middlewares.rate_limiter import limiter
from app.routers import merchant_router
from app.routers import payment_router
from app.routers import refund_router
from app.routers import webhook_router
from app.routers import settlement_router

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(IdempotentReplayResponse)
async def handle_idempotent_replay(request: Request, exc: IdempotentReplayResponse):
    """
    Catches IdempotentReplayResponse raised by check_idempotency and
    converts it into the actual cached HTTP response, short-circuiting
    whatever route would have otherwise run.
    """
    return JSONResponse(status_code=exc.status_code, content=exc.body)


app.include_router(merchant_router.router)
app.include_router(payment_router.router)
app.include_router(refund_router.router)
app.include_router(webhook_router.router)
app.include_router(settlement_router.router)


@app.get("/health")
def health_check():
    """
    Basic liveness check — confirms the API is running.
    """
    return {"status": "ok"}

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config.settings import settings
from app.middlewares.idempotency_middleware import IdempotentReplayResponse
from app.middlewares.rate_limiter import limiter
from app.routers import merchant_router
from app.routers import payment_router
from app.routers import refund_router
from app.routers import webhook_router
from app.routers import settlement_router

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(IdempotentReplayResponse)
async def handle_idempotent_replay(request: Request, exc: IdempotentReplayResponse):
    """
    Catches IdempotentReplayResponse raised by check_idempotency and
    converts it into the actual cached HTTP response, short-circuiting
    whatever route would have otherwise run.
    """
    return JSONResponse(status_code=exc.status_code, content=exc.body)


app.include_router(merchant_router.router)
app.include_router(payment_router.router)
app.include_router(refund_router.router)
app.include_router(webhook_router.router)
app.include_router(settlement_router.router)


@app.get("/health")
def health_check():
    """
    Basic liveness check — confirms the API is running.
    """
    return {"status": "ok"}

from contextlib import asynccontextmanager
from app.services.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
