from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db, get_primary_db, get_replica_db
from app.middleware.models.post_model import PostModel
from app.middleware.models.kol_model import KOLModel
from app.middleware.models.category_model import CategoryModel
from app.middleware.models.user_model import UserModel
from app.utils.logger import log_debug
from app.views.posts_view import (
    PostResponseView, PostsResponseView, PostDetailResponseView, 
    CreatePostView, UpdatePostView, KOLResponseView, CategoryResponseView
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.jwt_utils import verify_token
from typing import List, Optional

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Dependency cho authentication
async def get_current_user_api(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Lấy user hiện tại - hỗ trợ cả cookie và bearer token"""
    if credentials:
        try:
            token = credentials.credentials
            username = verify_token(token)
            if username:
                user = db.query(UserModel).filter(UserModel.username == username).first()
                if user and user.is_active:
                    return user
        except Exception as e:
            log_debug(f"❌ Error verifying Bearer token: {str(e)}", "ERROR")
    
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            username = verify_token(access_token)
            if username:
                user = db.query(UserModel).filter(UserModel.username == username).first()
                if user and user.is_active:
                    return user
        except Exception as e:
            log_debug(f"❌ Error verifying cookie token: {str(e)}", "ERROR")
    
    raise HTTPException(status_code=401, detail="Authentication required")

# ==================== POST ENDPOINTS ====================

@router.get("/", response_model=PostsResponseView, name="api_get_all_posts")
async def api_get_all_posts(
    skip: int = Query(0, ge=0, description="Skip posts"),
    limit: int = Query(10, ge=1, le=100, description="Limit posts"),
    db: Session = Depends(get_replica_db),  # Use replica for reads
    current_user: UserModel = Depends(get_current_user_api)
):
    """API lấy tất cả bài viết với phân trang"""
    try:
        posts = db.query(PostModel).offset(skip).limit(limit).all()
        total = db.query(PostModel).count()
        
        post_responses = []
        for post in posts:
            post_responses.append(PostResponseView(
                id=post.id,
                title=post.title,
                excerpt=post.excerpt,
                content=post.content,
                author_id=post.author_id,
                kol_id=post.kol_id,
                category_id=post.category_id,
                images=post.images,
                created_at=post.created_at,
                updated_at=post.updated_at,
                kol_name=post.kol.name if post.kol else None,
                category_name=post.category.name if post.category else None,
                author_username=post.author.username if post.author else None
            ))
        
        return PostsResponseView(
            message=f"Posts retrieved successfully by {current_user.username}",
            total_posts=total,
            posts=post_responses
        )
    except Exception as e:
        log_debug(f"❌ Error getting posts: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{post_id}", response_model=PostDetailResponseView, name="api_get_post_by_id")
async def api_get_post_by_id(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_api)
):
    """API lấy chi tiết bài viết theo ID"""
    try:
        post = db.query(PostModel).filter(PostModel.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post_response = PostResponseView(
            id=post.id,
            title=post.title,
            excerpt=post.excerpt,
            content=post.content,
            author_id=post.author_id,
            kol_id=post.kol_id,
            category_id=post.category_id,
            images=post.images,
            created_at=post.created_at,
            updated_at=post.updated_at,
            kol_name=post.kol.name if post.kol else None,
            category_name=post.category.name if post.category else None,
            author_username=post.author.username if post.author else None
        )
        
        return PostDetailResponseView(
            message=f"Post retrieved successfully by {current_user.username}",
            post=post_response
        )
    except HTTPException:
        raise
    except Exception as e:
        log_debug(f"❌ Error getting post {post_id}: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/", response_model=PostDetailResponseView, name="api_create_post")
async def api_create_post(
    post_data: CreatePostView,
    db: Session = Depends(get_primary_db),  # Use primary for writes
    current_user: UserModel = Depends(get_current_user_api)
):
    """API tạo bài viết mới"""
    try:
        # Validate KOL exists
        kol = db.query(KOLModel).filter(KOLModel.id == post_data.kol_id).first()
        if not kol:
            raise HTTPException(status_code=400, detail="KOL not found")
        
        # Validate Category exists
        category = db.query(CategoryModel).filter(CategoryModel.id == post_data.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")
        
        new_post = PostModel(
            title=post_data.title,
            excerpt=post_data.excerpt,
            content=post_data.content,
            author_id=current_user.id,
            kol_id=post_data.kol_id,
            category_id=post_data.category_id,
            images=post_data.images
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        post_response = PostResponseView(
            id=new_post.id,
            title=new_post.title,
            excerpt=new_post.excerpt,
            content=new_post.content,
            author_id=new_post.author_id,
            kol_id=new_post.kol_id,
            category_id=new_post.category_id,
            images=new_post.images,
            created_at=new_post.created_at,
            updated_at=new_post.updated_at,
            kol_name=new_post.kol.name if new_post.kol else None,
            category_name=new_post.category.name if new_post.category else None,
            author_username=new_post.author.username if new_post.author else None
        )
        
        return PostDetailResponseView(
            message=f"Post created successfully by {current_user.username}",
            post=post_response
        )
    except HTTPException:
        raise
    except Exception as e:
        log_debug(f"❌ Error creating post: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{post_id}", response_model=PostDetailResponseView, name="api_update_post")
async def api_update_post(
    post_id: int,
    post_data: UpdatePostView,
    db: Session = Depends(get_primary_db),  # Use primary for writes
    current_user: UserModel = Depends(get_current_user_api)
):
    """API cập nhật bài viết"""
    try:
        post = db.query(PostModel).filter(PostModel.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Validate KOL if provided
        if post_data.kol_id is not None:
            kol = db.query(KOLModel).filter(KOLModel.id == post_data.kol_id).first()
            if not kol:
                raise HTTPException(status_code=400, detail="KOL not found")
            post.kol_id = post_data.kol_id
        
        # Validate Category if provided
        if post_data.category_id is not None:
            category = db.query(CategoryModel).filter(CategoryModel.id == post_data.category_id).first()
            if not category:
                raise HTTPException(status_code=400, detail="Category not found")
            post.category_id = post_data.category_id
        
        # Update other fields
        if post_data.title is not None:
            post.title = post_data.title
        if post_data.excerpt is not None:
            post.excerpt = post_data.excerpt
        if post_data.content is not None:
            post.content = post_data.content
        if post_data.images is not None:
            post.images = post_data.images
        
        db.commit()
        db.refresh(post)
        
        post_response = PostResponseView(
            id=post.id,
            title=post.title,
            excerpt=post.excerpt,
            content=post.content,
            author_id=post.author_id,
            kol_id=post.kol_id,
            category_id=post.category_id,
            images=post.images,
            created_at=post.created_at,
            updated_at=post.updated_at,
            kol_name=post.kol.name if post.kol else None,
            category_name=post.category.name if post.category else None,
            author_username=post.author.username if post.author else None
        )
        
        return PostDetailResponseView(
            message=f"Post updated successfully by {current_user.username}",
            post=post_response
        )
    except HTTPException:
        raise
    except Exception as e:
        log_debug(f"❌ Error updating post {post_id}: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{post_id}", name="api_delete_post")
async def api_delete_post(
    post_id: int,
    db: Session = Depends(get_primary_db),  # Use primary for writes
    current_user: UserModel = Depends(get_current_user_api)
):
    """API xóa bài viết"""
    try:
        post = db.query(PostModel).filter(PostModel.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post_title = post.title
        db.delete(post)
        db.commit()
        
        return {
            "message": f"Post deleted successfully by {current_user.username}",
            "deleted_post_id": post_id,
            "deleted_post_title": post_title
        }
    except HTTPException:
        raise
    except Exception as e:
        log_debug(f"❌ Error deleting post {post_id}: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ==================== KOL ENDPOINTS ====================

@router.get("/kols/", response_model=List[KOLResponseView], name="api_get_all_kols")
async def api_get_all_kols(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_api)
):
    """API lấy tất cả KOLs"""
    try:
        kols = db.query(KOLModel).filter(KOLModel.is_active == True).all()
        return [KOLResponseView.from_orm(kol) for kol in kols]
    except Exception as e:
        log_debug(f"❌ Error getting KOLs: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ==================== CATEGORY ENDPOINTS ====================

@router.get("/categories/", response_model=List[CategoryResponseView], name="api_get_all_categories")
async def api_get_all_categories(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_api)
):
    """API lấy tất cả Categories"""
    try:
        categories = db.query(CategoryModel).filter(CategoryModel.is_active == True).all()
        return [CategoryResponseView.from_orm(category) for category in categories]
    except Exception as e:
        log_debug(f"❌ Error getting categories: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 