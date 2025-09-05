import time
from fastapi import Request
from app.utils.logger import log_request

async def logging_middleware(request: Request, call_next):
    """Middleware để log tất cả requests"""
    start_time = time.time()
    
    # Log request bắt đầu
    log_request(request.method, request.url.path, 0)
    
    # Xử lý request
    response = await call_next(request)
    
    # Tính thời gian xử lý
    duration = time.time() - start_time
    
    # Log response
    log_request(request.method, request.url.path, response.status_code, duration)
    
    return response
