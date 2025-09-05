from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.middleware.models.category_model import CategoryModel
from app.middleware.models.user_model import UserModel
from app.utils.jwt_utils import verify_token
from app.utils.logger import log_debug
from pydantic import BaseModel

router = APIRouter()

# Pydantic models
class CategoryCreateRequest(BaseModel):
    name: str
    description: str = None
    color: str = None
    is_active: bool = True

class CategoryUpdateRequest(BaseModel):
    name: str = None
    description: str = None
    color: str = None
    is_active: bool = None

# Authentication dependency
async def get_current_user_api(
    request: Request,
    db: Session = Depends(get_db)
):
    """Lấy user hiện tại"""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        username = verify_token(token)
        if username:
            user = db.query(UserModel).filter(UserModel.username == username).first()
            if user and user.is_active:
                return user
    
    raise HTTPException(status_code=401, detail="Authentication required")

@router.get("/", response_model=List[dict])
def get_categories(db: Session = Depends(get_db)):
    """Lấy danh sách tất cả categories"""
    categories = db.query(CategoryModel).filter(CategoryModel.is_active == True).all()
    return [category.to_dict() for category in categories]

@router.post("/", response_model=dict)
def create_category(
    category_data: CategoryCreateRequest, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user_api)
):
    """Tạo category mới (chỉ admin)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create categories")
    
    # Kiểm tra tên category đã tồn tại
    existing_category = db.query(CategoryModel).filter(CategoryModel.name == category_data.name).first()
    if existing_category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name already exists")
    
    category = CategoryModel(**category_data.dict())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category.to_dict()

@router.put("/{category_id}", response_model=dict)
def update_category(
    category_id: int, 
    category_data: CategoryUpdateRequest, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user_api)
):
    """Cập nhật category (chỉ admin)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update categories")
    
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Update only provided fields
    update_data = category_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category.to_dict()

@router.delete("/{category_id}")
def delete_category(
    category_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user_api)
):
    """Xóa category (chỉ admin)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete categories")
    
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Soft delete - chỉ set is_active = False
    category.is_active = False
    db.commit()
    return {"message": "Category deleted successfully"}