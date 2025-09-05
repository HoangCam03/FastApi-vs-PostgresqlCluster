from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.models.user_model import UserModel
from app.utils.password_utils import get_password_hash
from app.utils.jwt_utils import verify_token
from app.utils.logger import log_debug
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Helper function để lấy current user từ token
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
    created_at: datetime | None = None  # Sửa thành datetime

    class Config:
        from_attributes = True
        
    # Xóa computed_field property vì không cần thiết nữa

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

# API ENDPOINTS FOR USER MANAGEMENT
@router.get("/users/all", response_model=List[UserResponse], name="get_all_users")
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_from_token)
):
    """Lấy danh sách tất cả người dùng (chỉ admin)"""
    log_debug(f"=== GET ALL USERS API CALLED BY {current_user.username} ===", "INFO")
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        log_debug(f"❌ User {current_user.username} is not admin", "WARNING")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        users = db.query(UserModel).all()
        log_debug(f"✅ Returning {len(users)} users", "INFO")
        return users
    except Exception as e:
        log_debug(f"❌ Error getting users: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/users/{user_id}", response_model=UserResponse, name="get_user_by_id")
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_from_token)
):
    """Lấy thông tin người dùng theo ID (chỉ admin)"""
    log_debug(f"=== GET USER BY ID API CALLED BY {current_user.username} ===", "INFO")
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        log_debug(f"❌ User {current_user.username} is not admin", "WARNING")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        log_debug(f"❌ User with ID {user_id} not found", "WARNING")
        raise HTTPException(status_code=404, detail="User not found")
    
    log_debug(f"✅ Returning user {user.username}", "INFO")
    return user

@router.post("/users/create", response_model=UserResponse, name="create_user")
async def create_user(
    user_data: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_from_token)
):
    """Tạo người dùng mới (chỉ admin)"""
    log_debug(f"=== CREATE USER API CALLED BY {current_user.username} ===", "INFO")
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        log_debug(f"❌ User {current_user.username} is not admin", "WARNING")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Kiểm tra user đã tồn tại
    existing_user = db.query(UserModel).filter(
        (UserModel.username == user_data.username) | (UserModel.email == user_data.email)
    ).first()
    
    if existing_user:
        log_debug(f"❌ User already exists: {user_data.username}", "WARNING")
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Tạo user mới
    hashed_password = get_password_hash(user_data.password)
    new_user = UserModel(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=user_data.is_active,
        is_admin=user_data.is_admin
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_debug(f"✅ User created successfully: {new_user.username}", "INFO")
    return new_user

@router.put("/users/{user_id}", response_model=UserResponse, name="update_user")
async def update_user(
    user_id: int,
    user_data: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_from_token)
):
    """Cập nhật thông tin người dùng (chỉ admin)"""
    log_debug(f"=== UPDATE USER API CALLED BY {current_user.username} ===", "INFO")
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        log_debug(f"❌ User {current_user.username} is not admin", "WARNING")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        log_debug(f"❌ User with ID {user_id} not found", "WARNING")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cập nhật thông tin
    if user_data.username is not None:
        user.username = user_data.username
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    
    db.commit()
    db.refresh(user)
    
    log_debug(f"✅ User updated successfully: {user.username}", "INFO")
    return user

@router.delete("/users/{user_id}", name="delete_user")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_from_token)
):
    """Xóa người dùng (chỉ admin)"""
    log_debug(f"=== DELETE USER API CALLED BY {current_user.username} ===", "INFO")
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        log_debug(f"❌ User {current_user.username} is not admin", "WARNING")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Không cho phép xóa chính mình
    if user_id == current_user.id:
        log_debug(f"❌ User {current_user.username} trying to delete themselves", "WARNING")
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        log_debug(f"❌ User with ID {user_id} not found", "WARNING")
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    log_debug(f"✅ User deleted successfully: {user.username}", "INFO")
    return {"message": f"User {user.username} deleted successfully"}

@router.patch("/users/{user_id}/toggle-status", response_model=UserResponse, name="toggle_user_status")
async def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_from_token)
):
    """Bật/tắt trạng thái người dùng (chỉ admin)"""
    log_debug(f"=== TOGGLE USER STATUS API CALLED BY {current_user.username} ===", "INFO")
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        log_debug(f"❌ User {current_user.username} is not admin", "WARNING")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Không cho phép tắt chính mình
    if user_id == current_user.id:
        log_debug(f"❌ User {current_user.username} trying to disable themselves", "WARNING")
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        log_debug(f"❌ User with ID {user_id} not found", "WARNING")
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    status = "enabled" if user.is_active else "disabled"
    log_debug(f"✅ User {user.username} {status}", "INFO")
    return user

@router.patch("/users/{user_id}/change-role", response_model=UserResponse, name="change_user_role")
async def change_user_role(
    user_id: int,
    is_admin: bool,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_from_token)
):
    """Thay đổi vai trò người dùng (chỉ admin)"""
    log_debug(f"=== CHANGE USER ROLE API CALLED BY {current_user.username} ===", "INFO")
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        log_debug(f"❌ User {current_user.username} is not admin", "WARNING")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Không cho phép thay đổi vai trò chính mình
    if user_id == current_user.id:
        log_debug(f"❌ User {current_user.username} trying to change their own role", "WARNING")
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        log_debug(f"❌ User with ID {user_id} not found", "WARNING")
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_admin = is_admin
    db.commit()
    db.refresh(user)
    
    role = "admin" if user.is_admin else "user"
    log_debug(f"✅ User {user.username} role changed to {role}", "INFO")
    return user
