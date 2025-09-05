from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.middleware.models.kol_model import KOLModel
from app.middleware.models.user_model import UserModel
from app.utils.jwt_utils import verify_token
from app.utils.logger import log_debug
from pydantic import BaseModel

router = APIRouter()

# Pydantic models
class KOLCreateRequest(BaseModel):
    name: str
    description: str = None
    avatar: str = None
    is_active: bool = True

class KOLUpdateRequest(BaseModel):
    name: str = None
    description: str = None
    avatar: str = None
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
def get_kols(db: Session = Depends(get_db)):
    """Lấy danh sách tất cả KOLs"""
    kols = db.query(KOLModel).filter(KOLModel.is_active == True).all()
    return [kol.to_dict() for kol in kols]

@router.post("/", response_model=dict)
def create_kol(
    kol_data: KOLCreateRequest, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user_api)
):
    """Tạo KOL mới (chỉ admin)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create KOLs")
    
    # Kiểm tra tên KOL đã tồn tại
    existing_kol = db.query(KOLModel).filter(KOLModel.name == kol_data.name).first()
    if existing_kol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KOL name already exists")
    
    kol = KOLModel(**kol_data.dict())
    db.add(kol)
    db.commit()
    db.refresh(kol)
    return kol.to_dict()

@router.put("/{kol_id}", response_model=dict)
def update_kol(
    kol_id: int, 
    kol_data: KOLUpdateRequest, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user_api)
):
    """Cập nhật KOL (chỉ admin)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update KOLs")
    
    kol = db.query(KOLModel).filter(KOLModel.id == kol_id).first()
    if not kol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOL not found")
    
    # Update only provided fields
    update_data = kol_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kol, key, value)
    
    db.commit()
    db.refresh(kol)
    return kol.to_dict()

@router.delete("/{kol_id}")
def delete_kol(
    kol_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user_api)
):
    """Xóa KOL (chỉ admin)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete KOLs")
    
    kol = db.query(KOLModel).filter(KOLModel.id == kol_id).first()
    if not kol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOL not found")
    
    # Soft delete - chỉ set is_active = False
    kol.is_active = False
    db.commit()
    return {"message": "KOL deleted successfully"}