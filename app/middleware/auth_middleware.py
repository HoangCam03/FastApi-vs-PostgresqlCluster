from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.utils.jwt_utils import verify_token
from app.utils.logger import log_debug
from app.database.connection import get_db
from app.middleware.models.user_model import UserModel
from sqlalchemy.orm import Session
from typing import Callable
import time

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Lấy user hiện tại từ JWT token - kiểm tra cả header và cookie"""
    log_debug("=== AUTHENTICATION CHECK ===", "DEBUG")

    # Ưu tiên lấy từ header Authorization
    access_token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        access_token = auth_header.split(" ")[1]
        log_debug(f"🔍 Access token from header: {access_token[:20]}...", "DEBUG")
    else:
        access_token = request.cookies.get("access_token")
        log_debug(f"🔍 Access token from cookie: {access_token[:20] if access_token else None}...", "DEBUG")

    if not access_token:
        log_debug("❌ No access token found", "WARNING")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    try:
        # Verify token - trả về username (string)
        username = verify_token(access_token)
        if not username:
            log_debug("❌ Token verification failed", "WARNING")
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        
        log_debug(f"✅ Token verified for user: {username}", "DEBUG")
        
        # Lấy user từ database
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            log_debug(f"❌ User not found in database: {username}", "WARNING")
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        if not user.is_active:
            log_debug(f"❌ Inactive user: {username}", "WARNING")
            raise HTTPException(
                status_code=403,
                detail="Account is disabled"
            )
        
        log_debug(f"✅ Authentication successful for user: {username}", "INFO")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        log_debug(f"❌ Token verification failed: {str(e)}", "WARNING")
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

async def auth_middleware(request: Request, call_next: Callable):
    """Middleware để kiểm tra authentication cho các route cần thiết"""
    start_time = time.time()

    # Danh sách các path cần authentication (chỉ admin và API)
    protected_paths = [
        "/post/admin-management",
        "/post/add-post", 
        "/post/edit-post",
        "/post/delete-post",
        "/api/posts"  # API posts cần authentication
    ]

    # Kiểm tra xem path hiện tại có cần authentication không
    path = request.url.path
    needs_auth = any(path.startswith(protected_path) for protected_path in protected_paths)

    if needs_auth:
        log_debug(f"🔐 Protected path accessed: {path}", "DEBUG")

        # Lấy token từ header hoặc cookie
        access_token = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            log_debug(f"🔍 Access token from header: {access_token[:20]}...", "DEBUG")
        else:
            access_token = request.cookies.get("access_token")
            log_debug(f"🔍 Access token from cookie: {access_token[:20] if access_token else None}...", "DEBUG")

        if not access_token:
            log_debug(f"❌ No access token for protected path: {path}", "WARNING")
            # Redirect về login page cho HTML requests
            if not path.startswith("/api/"):
                return RedirectResponse(url="/user/login-page", status_code=302)
            else:
                # Trả về JSON error cho API requests
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"error": "Authentication required"}
                )

        try:
            # Verify token
            username = verify_token(access_token)
            if not username:
                log_debug(f"❌ Invalid token for path: {path}", "WARNING")
                if not path.startswith("/api/"):
                    return RedirectResponse(url="/user/login-page", status_code=302)
                else:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid token"}
                    )

            log_debug(f"✅ Authentication successful for {path} - User: {username}", "DEBUG")

        except Exception as e:
            log_debug(f"❌ Authentication failed for {path}: {str(e)}", "WARNING")
            if not path.startswith("/api/"):
                return RedirectResponse(url="/user/login-page", status_code=302)
            else:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"error": "Authentication failed"}
                )

    # Tiếp tục xử lý request
    response = await call_next(request)

    # Log thời gian xử lý
    process_time = time.time() - start_time
    log_debug(f"⏱️ Request processed in {process_time:.4f}s: {path}", "DEBUG")

    return response