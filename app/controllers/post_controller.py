from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.models.post_model import PostModel
from app.middleware.models.kol_model import KOLModel
from app.utils.logger import log_debug
from app.middleware.auth_middleware import get_current_user  # Thêm import
from app.middleware.models.user_model import UserModel
import os
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Tạo thư mục uploads nếu chưa có
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Thêm function kiểm tra file ảnh
def is_valid_image_file(filename):
    """Kiểm tra file có phải là ảnh không"""
    if not filename:
        return False
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    file_extension = os.path.splitext(filename.lower())[1]
    return file_extension in allowed_extensions

@router.get("/jisoo", response_class=HTMLResponse, name="jisoo")
async def jisoo(request: Request, db: Session = Depends(get_db)):
    """Hiển thị tất cả bài viết của Jisoo"""
    log_debug(f"🔍 Truy cập trang Jisoo - IP: {request.client.host}", "DEBUG")
    # Lấy bài viết của Jisoo thông qua KOL
    posts = db.query(PostModel).join(KOLModel).filter(KOLModel.name == "jisoo").all()
    log_debug(f"📝 Tìm thấy {len(posts)} bài viết của Jisoo", "DEBUG")
    return templates.TemplateResponse("members/jisoo.html", {
        "request": request,
        "posts": posts
    })

@router.get("/rose", response_class=HTMLResponse, name="rose")
async def rose(request: Request, db: Session = Depends(get_db)):
    """Hiển thị tất cả bài viết của Rosé"""
    log_debug(f"🔍 Truy cập trang Rosé - IP: {request.client.host}", "DEBUG")
    # Lấy bài viết của Rosé thông qua KOL
    posts = db.query(PostModel).join(KOLModel).filter(KOLModel.name == "rose").all()
    log_debug(f"📝 Tìm thấy {len(posts)} bài viết của Rosé", "DEBUG")
    return templates.TemplateResponse("members/rose.html", {
        "request": request,
        "posts": posts
    })

@router.get("/lisa", response_class=HTMLResponse, name="lisa")
async def lisa(request: Request, db: Session = Depends(get_db)):
    """Hiển thị tất cả bài viết của Lisa"""
    log_debug(f"🔍 Truy cập trang Lisa - IP: {request.client.host}", "DEBUG")
    # Lấy bài viết của Lisa thông qua KOL
    posts = db.query(PostModel).join(KOLModel).filter(KOLModel.name == "lisa").all()
    log_debug(f"📝 Tìm thấy {len(posts)} bài viết của Lisa", "DEBUG")
    return templates.TemplateResponse("members/lisa.html", {
        "request": request,
        "posts": posts
    })

@router.get("/jennie", response_class=HTMLResponse, name="jennie")
async def jennie(request: Request, db: Session = Depends(get_db)):
    """Hiển thị tất cả bài viết của Jennie"""
    log_debug(f"🔍 Truy cập trang Jennie - IP: {request.client.host}", "DEBUG")
    # Lấy bài viết của Jennie thông qua KOL
    posts = db.query(PostModel).join(KOLModel).filter(KOLModel.name == "jennie").all()
    log_debug(f"📝 Tìm thấy {len(posts)} bài viết của Jennie", "DEBUG")
    return templates.TemplateResponse("members/jennie.html", {
        "request": request,
        "posts": posts
    })

@router.get("/admin-management", response_class=HTMLResponse, name="admin_management")
async def admin_management(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)  
):
    """Trang quản lý bài viết - Yêu cầu đăng nhập"""
    log_debug(f"🔐 Admin Management accessed by: {current_user.username}", "INFO")
    # Lấy tất cả bài viết
    posts = db.query(PostModel).all()
    log_debug(f"📊 Tổng số bài viết trong hệ thống: {len(posts)}", "DEBUG")
    return templates.TemplateResponse("admin/admin-management.html", {
        "request": request,
        "posts": posts,
        "username": current_user.username  # Hiển thị username thực
    })

# Thêm bài viết mới - Yêu cầu authentication
@router.post("/add-post", response_class=HTMLResponse, name="add_post")
async def add_post(
    request: Request,
    title: str = Form(..., description="Tiêu đề bài viết"),
    member: str = Form(..., description="Thành viên (jisoo, rose, lisa, jennie)"),
    category: str = Form(..., description="Danh mục bài viết"),
    excerpt: str = Form(..., description="Tóm tắt bài viết"),
    content: str = Form(..., description="Nội dung bài viết"),
    author: str = Form(..., description="Tác giả"),
    images: UploadFile = File(..., description="Ảnh bài viết"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)  # Thêm authentication
):
    """Thêm bài viết mới - Yêu cầu đăng nhập"""
    log_debug(f"📝 Add post attempt by user: {current_user.username}", "INFO")
    log_debug(f" Bắt đầu tạo bài viết mới - Title: {title}, Member: {member}", "DEBUG")
    log_debug(f"📁 File ảnh: {images.filename if images else 'Không có'}", "DEBUG")
    
    try:
        # Lưu file ảnh
        if images and images.filename:
            if not is_valid_image_file(images.filename):
                log_debug(f"❌ File không hợp lệ: {images.filename}", "DEBUG")
                raise HTTPException(status_code=400, detail="File không phải là ảnh hợp lệ")
            
            file_extension = os.path.splitext(images.filename)[1]
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            log_debug(f"💾 Lưu file ảnh: {filename}", "DEBUG")
            with open(file_path, "wb") as buffer:
                content_file = images.file.read()
                buffer.write(content_file)
        
        # Tạo bài viết mới
        new_post = PostModel(
            title=title,
            member=member,
            category=category,
            excerpt=excerpt,
            content=content,
            author_id=1,  # Tạm thời hardcode
            images=filename if images and images.filename else None # Lưu tên file nếu có ảnh
        )
        
        log_debug(f"💾 Lưu bài viết vào database", "DEBUG")
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        log_debug(f"✅ Bài viết mới được tạo: {title}", "INFO")
        log_debug(f" ID bài viết mới: {new_post.id}", "DEBUG")
        
        # Redirect về trang admin
        return RedirectResponse(url="/post/admin-management", status_code=302)
        
    except Exception as e:
        log_debug(f"❌ Lỗi khi tạo bài viết: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Lỗi khi tạo bài viết")

# Sửa bài viết - Yêu cầu authentication
@router.post("/edit-post/{post_id}", response_class=HTMLResponse, name="edit_post")
async def edit_post(
    request: Request,
    post_id: int,
    title: str = Form(..., description="Tiêu đề bài viết"),
    member: str = Form(..., description="Thành viên"),
    category: str = Form(..., description="Danh mục bài viết"),
    excerpt: str = Form(..., description="Tóm tắt bài viết"),
    content: str = Form(..., description="Nội dung bài viết"),
    author: str = Form(..., description="Tác giả"),
    images: UploadFile = File(None, description="Ảnh bài viết (tùy chọn)"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)  # Thêm authentication
):
    """Sửa bài viết - Yêu cầu đăng nhập"""
    log_debug(f"✏️ Edit post {post_id} attempt by user: {current_user.username}", "INFO")
    log_debug(f"✏️ Bắt đầu cập nhật bài viết ID: {post_id}", "DEBUG")
    log_debug(f" Thông tin cập nhật - Title: {title}, Member: {member}", "DEBUG")
    log_debug(f"📁 File ảnh mới: {images.filename if images else 'Không có'}", "DEBUG")
    
    try:
        # Tìm bài viết
        post = db.query(PostModel).filter(PostModel.id == post_id).first()
        if not post:
            log_debug(f"❌ Không tìm thấy bài viết ID: {post_id}", "DEBUG")
            raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
        
        log_debug(f" Tìm thấy bài viết: {post.title}", "DEBUG")
        
        # Cập nhật thông tin
        post.title = title
        post.member = member
        post.category = category
        post.excerpt = excerpt
        post.content = content
        
        # Chỉ cập nhật ảnh nếu có upload ảnh mới
        if images and images.filename:
            log_debug(f"️ Cập nhật ảnh mới: {images.filename}", "DEBUG")
            # Xóa ảnh cũ nếu có
            if post.images:
                old_image_path = os.path.join(UPLOAD_DIR, post.images)
                if os.path.exists(old_image_path):
                    log_debug(f"️ Xóa ảnh cũ: {post.images}", "DEBUG")
                    os.remove(old_image_path)
            
            # Lưu ảnh mới
            file_extension = os.path.splitext(images.filename)[1]
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            log_debug(f"💾 Lưu ảnh mới: {filename}", "DEBUG")
            with open(file_path, "wb") as buffer:
                content_file = images.file.read()
                buffer.write(content_file)
            
            post.images = filename
        else:
            log_debug("📷 Giữ nguyên ảnh cũ", "DEBUG")
        
        db.commit()
        log_debug(f"✅ Bài viết đã được cập nhật: {title}", "INFO")
        
        # Redirect về trang admin
        return RedirectResponse(url="/post/admin-management", status_code=302)
        
    except Exception as e:
        log_debug(f"❌ Lỗi khi cập nhật bài viết: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Lỗi khi cập nhật bài viết")

# Xóa bài viết - Yêu cầu authentication
@router.post("/delete-post/{post_id}", response_class=HTMLResponse, name="delete_post")
async def delete_post(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)  # Thêm authentication
):
    """Xóa bài viết - Yêu cầu đăng nhập"""
    log_debug(f"🗑️ Delete post {post_id} attempt by user: {current_user.username}", "INFO")
    log_debug(f"🗑️ Bắt đầu xóa bài viết ID: {post_id}", "DEBUG")
    
    try:
        # Tìm bài viết
        post = db.query(PostModel).filter(PostModel.id == post_id).first()
        if not post:
            log_debug(f"❌ Không tìm thấy bài viết ID: {post_id}", "DEBUG")
            raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
        
        log_debug(f"📖 Tìm thấy bài viết để xóa: {post.title}", "DEBUG")
        
        # Xóa file ảnh
        if post.images:
            image_path = os.path.join(UPLOAD_DIR, post.images)
            if os.path.exists(image_path):
                log_debug(f"🗑️ Xóa file ảnh: {post.images}", "DEBUG")
                os.remove(image_path)
            else:
                log_debug(f"⚠️ File ảnh không tồn tại: {post.images}", "DEBUG")
        else:
            log_debug(" Bài viết không có ảnh", "DEBUG")
        
        # Xóa bài viết
        log_debug(f"️ Xóa bài viết khỏi database", "DEBUG")
        db.delete(post)
        db.commit()
        
        log_debug(f"✅ Bài viết đã được xóa: {post.title}", "INFO")
        
        # Redirect về trang admin
        return RedirectResponse(url="/post/admin-management", status_code=302)
        
    except Exception as e:
        log_debug(f"❌ Lỗi khi xóa bài viết: {e}", "ERROR")
        raise HTTPException(status_code=500, detail="Lỗi khi xóa bài viết")

# Xem chi tiết bài viết
@router.get("/post-detail/{post_id}", response_class=HTMLResponse, name="post_detail")
async def post_detail(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    """Xem chi tiết bài viết theo ID"""
    log_debug(f"️ Truy cập chi tiết bài viết ID: {post_id} - IP: {request.client.host}", "DEBUG")
    
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        log_debug(f"❌ Không tìm thấy bài viết ID: {post_id}", "DEBUG")
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    
    log_debug(f"📖 Hiển thị bài viết: {post.title}", "DEBUG")
    
    return templates.TemplateResponse("posts/detail.html", {
        "request": request,
        "post": post
    })

# Xem chi tiết bài viết Jisoo
@router.get("/jisoo-post-detail/{post_id}", response_class=HTMLResponse, name="jisoo_post_detail")
async def jisoo_post_detail(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    """Xem chi tiết bài viết Jisoo theo ID"""
    log_debug(f"👁️ Truy cập chi tiết bài viết Jisoo ID: {post_id} - IP: {request.client.host}", "DEBUG")
    
    post = db.query(PostModel).filter(PostModel.id == post_id, PostModel.member == "jisoo").first()
    if not post:
        log_debug(f"❌ Không tìm thấy bài viết Jisoo ID: {post_id}", "DEBUG")
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    
    log_debug(f"📖 Hiển thị bài viết Jisoo: {post.title}", "DEBUG")
    
    return templates.TemplateResponse("posts/post_detail.html", {
        "request": request,
        "post": post
    })

# Xem chi tiết bài viết Rosé
@router.get("/rose-post-detail/{post_id}", response_class=HTMLResponse, name="rose_post_detail")
async def rose_post_detail(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    """Xem chi tiết bài viết Rosé theo ID"""
    log_debug(f"👁️ Truy cập chi tiết bài viết Rosé ID: {post_id} - IP: {request.client.host}", "DEBUG")
    
    post = db.query(PostModel).filter(PostModel.id == post_id, PostModel.member == "rose").first()
    if not post:
        log_debug(f"❌ Không tìm thấy bài viết Rosé ID: {post_id}", "DEBUG")
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    
    log_debug(f"📖 Hiển thị bài viết Rosé: {post.title}", "DEBUG")
    
    return templates.TemplateResponse("posts/rose_post_detail.html", {
        "request": request,
        "post": post
    })

# Xem chi tiết bài viết Lisa
@router.get("/lisa-post-detail/{post_id}", response_class=HTMLResponse, name="lisa_post_detail")
async def lisa_post_detail(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    """Xem chi tiết bài viết Lisa theo ID"""
    log_debug(f"👁️ Truy cập chi tiết bài viết Lisa ID: {post_id} - IP: {request.client.host}", "DEBUG")
    
    post = db.query(PostModel).filter(PostModel.id == post_id, PostModel.member == "lisa").first()
    if not post:
        log_debug(f"❌ Không tìm thấy bài viết Lisa ID: {post_id}", "DEBUG")
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    
    log_debug(f"📖 Hiển thị bài viết Lisa: {post.title}", "DEBUG")
    
    return templates.TemplateResponse("posts/lisa_post_detail.html", {
        "request": request,
        "post": post
    })

# Xem chi tiết bài viết Jennie
@router.get("/jennie-post-detail/{post_id}", response_class=HTMLResponse, name="jennie_post_detail")
async def jennie_post_detail(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    """Xem chi tiết bài viết Jennie theo ID"""
    log_debug(f"👁️ Truy cập chi tiết bài viết Jennie ID: {post_id} - IP: {request.client.host}", "DEBUG")
    
    post = db.query(PostModel).filter(PostModel.id == post_id, PostModel.member == "jennie").first()
    if not post:
        log_debug(f"❌ Không tìm thấy bài viết Jennie ID: {post_id}", "DEBUG")
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    
    log_debug(f"📖 Hiển thị bài viết Jennie: {post.title}", "DEBUG")
    
    return templates.TemplateResponse("posts/jennie_post_detail.html", {
        "request": request,
        "post": post
    })

