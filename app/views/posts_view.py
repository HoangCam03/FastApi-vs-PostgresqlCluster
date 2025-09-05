from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PostResponseView(BaseModel):
    id: int
    title: str
    excerpt: Optional[str] = None
    content: str
    author_id: int
    kol_id: int
    category_id: int
    images: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Related data
    kol_name: Optional[str] = None
    category_name: Optional[str] = None
    author_username: Optional[str] = None
    
    class Config:
        from_attributes = True

class PostsResponseView(BaseModel):
    message: str
    total_posts: int
    posts: List[PostResponseView]

class PostDetailResponseView(BaseModel):
    message: str
    post: PostResponseView

class CreatePostView(BaseModel):
    title: str
    excerpt: Optional[str] = None
    content: str
    kol_id: int
    category_id: int
    images: Optional[str] = None

class UpdatePostView(BaseModel):
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    kol_id: Optional[int] = None
    category_id: Optional[int] = None
    images: Optional[str] = None

# Additional views for KOLs and Categories
class KOLResponseView(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True

class CategoryResponseView(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True 