# app/middleware/models/user_model.py - ĐÚNG NỘI DUNG
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database.connection import Base
from datetime import datetime



# IMPORT Base TỪ connection.py
# from app.database.connection import UserBase # Xóa dòng này

class UserModel(Base):  # Sửa từ UserBase thành Base
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)  # Thêm length
    email = Column(String(100), unique=True, index=True, nullable=False)  # Thêm length
    hashed_password = Column(String(255), nullable=False)  # Thêm length
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Xóa dòng updated_at để khớp với database hiện tại
    
    def __repr__(self):
        return f"<UserModel(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def role(self):
        """Trả về vai trò của user"""
        return "Administrator" if self.is_admin else "User"
    
    @property
    def status(self):
        """Trả về trạng thái của user"""
        return "Active" if self.is_active else "Inactive"
    
    @property
    def created_date(self):
        """Trả về ngày tạo dạng string"""
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
    
    def to_dict(self):
        """Chuyển đổi user thành dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_date
        }
