from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils.logger import log_debug
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Định nghĩa tất cả các API endpoints
API_ENDPOINTS = {
    "authentication": {
        "login_page": {
            "method": "GET",
            "path": "/user/login-page",
            "description": "Trang đăng nhập",
            "response": "HTML"
        },
        "login_submit": {
            "method": "POST", 
            "path": "/user/login-submit",
            "description": "Xử lý đăng nhập",
            "response": "HTML/Redirect"
        },
        "register_page": {
            "method": "GET",
            "path": "/user/register-page", 
            "description": "Trang đăng ký",
            "response": "HTML"
        },
        "register_submit": {
            "method": "POST",
            "path": "/user/register-submit",
            "description": "Xử lý đăng ký",
            "response": "HTML/Redirect"
        },
        "logout": {
            "method": "GET",
            "path": "/user/logout",
            "description": "Đăng xuất",
            "response": "Redirect"
        }
    },
    "user_management": {
        "admin_users_page": {
            "method": "GET",
            "path": "/user/admin-users",
            "description": "Trang quản lý người dùng (Admin)",
            "response": "HTML"
        },
        "get_all_users": {
            "method": "GET",
            "path": "/api/users/all",
            "description": "Lấy danh sách tất cả người dùng (API)",
            "response": "JSON"
        },
        "get_user_by_id": {
            "method": "GET",
            "path": "/api/users/{user_id}",
            "description": "Lấy thông tin người dùng theo ID",
            "response": "JSON"
        },
        "create_user": {
            "method": "POST",
            "path": "/api/users/create",
            "description": "Tạo người dùng mới",
            "response": "JSON"
        },
        "update_user": {
            "method": "PUT",
            "path": "/api/users/{user_id}",
            "description": "Cập nhật thông tin người dùng",
            "response": "JSON"
        },
        "delete_user": {
            "method": "DELETE",
            "path": "/api/users/{user_id}",
            "description": "Xóa người dùng",
            "response": "JSON"
        },
        "toggle_user_status": {
            "method": "PATCH",
            "path": "/api/users/{user_id}/toggle-status",
            "description": "Bật/tắt trạng thái người dùng",
            "response": "JSON"
        },
        "change_user_role": {
            "method": "PATCH",
            "path": "/api/users/{user_id}/change-role",
            "description": "Thay đổi vai trò người dùng",
            "response": "JSON"
        }
    },
    "posts": {
        "jisoo_posts": {
            "method": "GET",
            "path": "/post/jisoo",
            "description": "Lấy bài viết của Jisoo",
            "response": "HTML/Redirect"
        },
        "rose_posts": {
            "method": "GET", 
            "path": "/post/rose",
            "description": "Lấy bài viết của Rosé",
            "response": "HTML/Redirect"
        },
        "lisa_posts": {
            "method": "GET",
            "path": "/post/lisa", 
            "description": "Lấy bài viết của Lisa",
            "response": "HTML/Redirect"
        },
        "jennie_posts": {
            "method": "GET",
            "path": "/post/jennie",
            "description": "Lấy bài viết của Jennie", 
            "response": "HTML/Redirect"
        },
        "admin_management": {
            "method": "GET",
            "path": "/post/admin-management",
            "description": "Quản lý bài viết (Admin)",
            "response": "HTML/Redirect"
        },
        "add_post": {
            "method": "POST",
            "path": "/post/add-post",
            "description": "Thêm bài viết mới",
            "response": "HTML/Redirect"
        },
        "edit_post": {
            "method": "POST", 
            "path": "/post/edit-post/{post_id}",
            "description": "Sửa bài viết",
            "response": "HTML/Redirect"
        },
        "delete_post": {
            "method": "POST",
            "path": "/post/delete-post/{post_id}", 
            "description": "Xóa bài viết",
            "response": "HTML/Redirect"
        },
        "post_detail": {
            "method": "GET",
            "path": "/post/post-detail/{post_id}",
            "description": "Xem chi tiết bài viết",
            "response": "HTML/Redirect"
        },
        "jisoo_post_detail": {
            "method": "GET",
            "path": "/post/jisoo-post-detail/{post_id}",
            "description": "Xem chi tiết bài viết Jisoo",
            "response": "HTML/Redirect"
        },
        "rose_post_detail": {
            "method": "GET",
            "path": "/post/rose-post-detail/{post_id}",
            "description": "Xem chi tiết bài viết Rosé",
            "response": "HTML/Redirect"
        },
        "lisa_post_detail": {
            "method": "GET",
            "path": "/post/lisa-post-detail/{post_id}",
            "description": "Xem chi tiết bài viết Lisa",
            "response": "HTML/Redirect"
        },
        "jennie_post_detail": {
            "method": "GET",
            "path": "/post/jennie-post-detail/{post_id}",
            "description": "Xem chi tiết bài viết Jennie",
            "response": "HTML/Redirect"
        }
    },
    "system": {
        "root": {
            "method": "GET",
            "path": "/",
            "description": "Trang chủ",
            "response": "HTML/Redirect"
        },
        "home": {
            "method": "GET", 
            "path": "/home",
            "description": "Trang chủ",
            "response": "HTML/Redirect"
        },
        "health": {
            "method": "GET",
            "path": "/health",
            "description": "Kiểm tra trạng thái hệ thống",
            "response": "JSON"
        },
        "api_discovery": {
            "method": "GET",
            "path": "/api/discovery",
            "description": "Danh sách tất cả API endpoints",
            "response": "JSON"
        },
        "api_docs": {
            "method": "GET",
            "path": "/api-docs",
            "description": "Trang documentation API",
            "response": "HTML/Redirect"
        }
    }
}

@router.get("/discovery")
async def api_discovery():
    """Trả về danh sách tất cả các API endpoints"""
    log_debug("API discovery endpoint called", "INFO")
    
    return {
        "message": "API Discovery",
        "version": "1.0.0",
        "total_endpoints": sum(len(category) for category in API_ENDPOINTS.values()),
        "categories": API_ENDPOINTS,
        "base_url": "https://localhost:8443"  # Chỉ sử dụng HTTPS
    }

@router.get("/docs", response_class=HTMLResponse)
async def api_docs_page(request: Request):
    """Trang hiển thị API documentation"""
    log_debug("API docs page accessed", "INFO")
    return templates.TemplateResponse("api-docs.html", {
        "request": request
    })
