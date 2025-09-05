from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.models.user_model import UserModel
from app.utils.password_utils import get_password_hash, verify_password
from app.utils.jwt_utils import create_access_token, verify_token
from app.utils.logger import log_debug
from datetime import timedelta
from dotenv import load_dotenv
import os
from typing import List
from pydantic import BaseModel
from app.api.users import router as users_api_router

# Load environment variables
load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# JWT Settings từ .env
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "2"))

# Helper function để lấy current user từ token - DI CHUYỂN LÊN ĐÂY
async def get_current_user_from_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """Lấy user từ token trong header hoặc cookie"""
    # Thử lấy từ Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        username = verify_token(token)
        if username:
            user = db.query(UserModel).filter(UserModel.username == username).first()
            if user and user.is_active:
                return user
    
    # Thử lấy từ cookie
    username = request.cookies.get("username")
    if username:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if user and user.is_active:
            return user
    
    raise HTTPException(status_code=401, detail="Authentication required")

# Pydantic models cho API responses
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: str

    class Config:
        from_attributes = True

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False

class UpdateUserRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None

# ===== EXISTING AUTH ENDPOINTS =====

@router.get("/login-page", response_class=HTMLResponse, name="login_page")
async def login_page(request: Request):
    """Hiển thị trang đăng nhập cho người dùng"""
    log_debug("=== ACCESSING LOGIN PAGE ===", "INFO")
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
    })

@router.post("/login-submit", response_class=HTMLResponse, name="login_submit")
async def login_submit(
    request: Request,
    username: str = Form(..., description="Tên đăng nhập"),
    password: str = Form(..., description="Mật khẩu"),
    db: Session = Depends(get_db)
):
    """Xử lý đăng nhập người dùng và tạo JWT token"""
    log_debug(f"=== LOGIN ATTEMPT ===", "INFO")
    log_debug(f"Username: {username}", "INFO")
    
    # Tìm user trong database
    user = db.query(UserModel).filter(UserModel.username == username).first()
    
    if not user:
        log_debug(f"❌ User not found: {username}", "WARNING")
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid username or password"
        })
    
    # Kiểm tra password
    if not verify_password(password, user.hashed_password):
        log_debug(f"❌ Invalid password for user: {username}", "WARNING")
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid username or password"
        })
    
    # Kiểm tra user có active không
    if not user.is_active:
        log_debug(f"❌ Inactive user: {username}", "WARNING")
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Account is disabled"
        })
    
    log_debug(f"✅ Password verified for user: {username}", "INFO")
    
    # Tạo access token với hiệu lực 2 tiếng
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    log_debug(f"✅ Access token created for user: {username}", "INFO")
    
    # Redirect với token
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600)
    response.set_cookie(key="username", value=user.username, httponly=False, max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600)

    log_debug(f"✅ Login successful, redirecting to homepage", "INFO")
    return response

@router.get("/register", response_class=HTMLResponse, name="register")
async def register(request: Request):
    """Hiển thị trang đăng ký cho người dùng mới"""
    log_debug("=== ACCESSING REGISTER PAGE ===", "INFO")
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
    })

@router.post("/register-submit", response_class=HTMLResponse, name="register_submit")
async def register_submit(
    request: Request,
    username: str = Form(..., description="Tên đăng nhập"),
    email: str = Form(..., description="Email"),
    password1: str = Form(..., description="Mật khẩu"),
    password2: str = Form(..., description="Xác nhận mật khẩu"),
    db: Session = Depends(get_db)
):
    """Xử lý đăng ký người dùng mới và tạo tài khoản"""
    log_debug("=== REGISTER SUBMIT FUNCTION CALLED ===", "INFO")
    log_debug(f"Register attempt for username: {username}, email: {email}", "INFO")
    
    # Kiểm tra password match
    if password1 != password2:
        log_debug("❌ Password mismatch during registration", "WARNING")
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Passwords do not match"
        })
    
    # Kiểm tra user đã tồn tại
    existing_user = db.query(UserModel).filter(
        (UserModel.username == username) | (UserModel.email == email)
    ).first()
    
    if existing_user:
        log_debug(f"❌ User already exists: {username}", "WARNING")
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Username or email already exists"
        })
    
    # Tạo user mới
    hashed_password = get_password_hash(password1)
    new_user = UserModel(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_debug(f"✅ User created successfully: {username}", "INFO")
    
    # Tạo access token với hiệu lực 2 tiếng
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": new_user.username}, 
        expires_delta=access_token_expires
    )
    
    log_debug(f"✅ Access token created for user: {username}", "INFO")
    
    # Redirect với token
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600)
    response.set_cookie(key="username", value=new_user.username, httponly=False, max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600)

    log_debug("✅ Registration successful, redirecting to homepage", "INFO")
    return response

@router.get("/logout", name="logout")
async def logout():
    """Đăng xuất người dùng và xóa JWT token"""
    log_debug("=== USER LOGOUT ===", "INFO")
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="username")
    return response

# ===== NEW USER MANAGEMENT ENDPOINTS =====

@router.get("/admin-users", response_class=HTMLResponse, name="admin_users_page")
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    """Trang quản lý người dùng cho admin"""
    log_debug("=== ACCESSING ADMIN USERS PAGE ===", "INFO")
    
    # Lấy username từ cookie
    username = request.cookies.get("username")
    if not username:
        log_debug("❌ No username in cookies, redirecting to login", "WARNING")
        return RedirectResponse(url="/user/login-page", status_code=302)
    
    # Kiểm tra user có phải admin không
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user or not user.is_admin:
        log_debug(f"❌ User {username} is not admin", "WARNING")
        return RedirectResponse(url="/", status_code=302)
    
    # Lấy tất cả users
    users = db.query(UserModel).all()
    log_debug(f"✅ Found {len(users)} users", "INFO")
    
    return templates.TemplateResponse("admin/user-management.html", {
        "request": request,
        "username": username,
        "users": users,
        "is_admin": True
    })

# XÓA TẤT CẢ CÁC API ENDPOINTS (từ dòng 254 trở đi)
# Chỉ giữ lại các HTML endpoints và auth endpoints