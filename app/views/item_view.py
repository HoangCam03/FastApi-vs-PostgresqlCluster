from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# Request schemas (Input validation)
class UserLoginView(BaseModel):
    username: str
    password: str 

class UserRegisterView(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str 

class UserResponseView(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TokenResponseView(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponseView

class LoginResponseView(BaseModel):
    message: str
    user: UserResponseView
    token: TokenResponseView

# Xóa tất cả Post-related schemas khỏi đây vì đã có trong posts_view.py