from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import v1_router
from app.database import Base, engine
from app.logging_config import configure_logging
from app.middleware import WideEventMiddleware

configure_logging(log_level="INFO")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Endeavor PokéTracker", version="0.0.1")

app.add_middleware(WideEventMiddleware)  # ty: ignore[invalid-argument-type]

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)  # ty: ignore[invalid-argument-type]


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["error"] = {
            "type": "RateLimitExceeded",
            "message": "Rate limit exceeded",
        }
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["error"] = {
            "type": "ValueError",
            "message": str(exc),
        }
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    return {"message": "Welcome to PokéTracker API"}


app.include_router(v1_router, prefix="/v1")
