from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from app.database.connection import get_db  # Thay đổi import
from app.middleware.models.user_model import UserModel
from app.utils.password_utils import get_password_hash, verify_password
from app.utils.jwt_utils import create_access_token
from app.utils.logger import log_debug
from datetime import timedelta
from dotenv import load_dotenv
import os
from app.views.item_view import UserLoginView, UserRegisterView, UserResponseView, TokenResponseView, LoginResponseView
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Load environment variables
load_dotenv()

router = APIRouter()

# JWT Settings từ .env
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "2"))

@router.post("/login", response_model=LoginResponseView, name="api_login")
async def api_login(
    request: UserLoginView,
    response: Response,
    db: Session = Depends(get_db)
):
    """API đăng nhập trả về JSON response và set cookie"""
    log_debug(f"=== API LOGIN ATTEMPT ===", "INFO")
    log_debug(f"Username: {request.username}", "INFO")
    
    # Tìm user trong database
    user = db.query(UserModel).filter(UserModel.username == request.username).first()
    
    if not user:
        log_debug(f"❌ User not found: {request.username}", "WARNING")
        raise HTTPException(
            status_code=401, 
            detail="Invalid username or password"
        )
    
    # Kiểm tra password
    if not verify_password(request.password, user.hashed_password):
        log_debug(f"❌ Invalid password for user: {request.username}", "WARNING")
        raise HTTPException(
            status_code=401, 
            detail="Invalid username or password"
        )
    
    # Kiểm tra user có active không
    if not user.is_active:
        log_debug(f"❌ Inactive user: {request.username}", "WARNING")
        raise HTTPException(
            status_code=403, 
            detail="Account is disabled"
        )
    
    log_debug(f"✅ User verified: {request.username}", "INFO")
    
    # Tạo access token với hiệu lực 2 tiếng
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    log_debug(f"✅ Access token created for user: {request.username}", "INFO")
    
    # Set cookie cho web interface
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600
    )
    
    # Set cookie cho username
    response.set_cookie(
        key="username", 
        value=user.username, 
        httponly=False, 
        max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600,
        secure=False,  # Cho localhost
        samesite="lax",
        path="/"  # Thêm path="/"
    )
    
    log_debug(f"✅ Cookie 'username' set to: {user.username}", "DEBUG")
    
    # Tạo response
    user_response = UserResponseView(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=getattr(user, 'is_admin', False),
        created_at=getattr(user, 'created_at', None)
    )
    
    token_response = TokenResponseView(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user=user_response
    )
    
    return LoginResponseView(
        message="Login successful",
        user=user_response,
        token=token_response
    )

@router.post("/register", response_model=UserResponseView, name="api_register")
async def api_register(
    request: UserRegisterView,
    response: Response,
    db: Session = Depends(get_db)
):
    """API đăng ký trả về JSON response và set cookie"""
    log_debug("=== API REGISTER ATTEMPT ===", "INFO")
    log_debug(f"Username: {request.username}, Email: {request.email}", "INFO")
    
    # Kiểm tra password match
    if request.password != request.confirm_password:
        log_debug("❌ Password mismatch during registration", "WARNING")
        raise HTTPException(
            status_code=400, 
            detail="Passwords do not match"
        )
    
    # Kiểm tra user đã tồn tại
    existing_user = db.query(UserModel).filter(
        (UserModel.username == request.username) | (UserModel.email == request.email)
    ).first()
    
    if existing_user:
        log_debug(f"❌ User already exists: {request.username}", "WARNING")
        raise HTTPException(
            status_code=409, 
            detail="Username or email already exists"
        )
    
    # Tạo user mới
    hashed_password = get_password_hash(request.password)
    new_user = UserModel(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_debug(f"✅ User created successfully: {request.username}", "INFO")
    
    # Tạo access token
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": new_user.username}, 
        expires_delta=access_token_expires
    )
    
    # Set cookie cho web interface
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600
    )
    
    # Set cookie cho username
    response.set_cookie(
        key="username", 
        value=new_user.username, 
        httponly=False, 
        max_age=ACCESS_TOKEN_EXPIRE_HOURS*3600
    )
    
    log_debug(f"✅ Cookies set for new user: {request.username}", "INFO")
    
    return UserResponseView(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        is_active=new_user.is_active,
        is_admin=getattr(new_user, 'is_admin', False),
        created_at=getattr(new_user, 'created_at', None)
    )

@router.post("/logout", name="api_logout")
async def api_logout(response: Response):
    """API đăng xuất và xóa cookie"""
    log_debug("=== API LOGOUT ===", "INFO")
    
    # Xóa cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="username")
    
    return {"message": "Logout successful"} 