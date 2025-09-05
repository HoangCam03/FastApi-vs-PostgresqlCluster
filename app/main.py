from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.controllers.user_controller import router as user_router
from app.controllers.post_controller import router as post_router
from app.controllers.api_controller import router as api_router
from app.api.auth import router as auth_api_router
from app.api.posts import router as posts_api_router
from app.api.users import router as users_api_router
from app.api.kols import router as kols_api_router
from app.api.categories import router as categories_api_router
from app.utils.jwt_utils import verify_token
from app.database.connection import get_db, engine, Base
from app.middleware.models.user_model import UserModel
from app.middleware.models.post_model import PostModel
from app.middleware.logging_middleware import logging_middleware
from app.middleware.auth_middleware import auth_middleware
from app.utils.logger import log_debug
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Security scheme cho Swagger UI
security = HTTPBearer()

app = FastAPI(
    title="BLACKPINK Fan Site API",
    description="""
    ## BLACKPINK Fan Site API
    
    ### 🔐 Authentication (HTML)
    - **Login Page**: GET /user/login-page
    - **Login Submit**: POST /user/login-submit  
    - **Register Page**: GET /user/register-page
    - **Register Submit**: POST /user/register-submit
    - **Logout**: GET /user/logout
    
    ### 👥 User Management (HTML)
    - **Admin Users Page**: GET /user/admin-users
    
    ### 👤 User Management API (JSON) - Requires Admin Authentication
    - **Get All Users**: GET /api/users/all
    - **Get User by ID**: GET /api/users/{user_id}
    - **Create User**: POST /api/users/create
    - **Update User**: PUT /api/users/{user_id}
    - **Delete User**: DELETE /api/users/{user_id}
    - **Toggle User Status**: PATCH /api/users/{user_id}/toggle-status
    - **Change User Role**: PATCH /api/users/{user_id}/change-role
    
    ###  API Authentication (JSON)
    - **Login API**: POST /api/auth/login
    - **Register API**: POST /api/auth/register
    - **Logout API**: POST /api/auth/logout
    
    ###  Posts Management (HTML)
    - **View Posts**: GET /post/{member} (jisoo, rose, lisa, jennie)
    - **Admin Management**: GET /post/admin-management
    - **Add Post**: POST /post/add-post
    - **Edit Post**: POST /post/edit-post/{post_id}
    - **Delete Post**: POST /post/delete-post/{post_id}
    - **Post Detail**: GET /post/{member}-post-detail/{post_id}
    
    ###  Posts API (JSON) - Requires Authentication
    - **Get All Posts**: GET /api/posts/
    - **Get Post by ID**: GET /api/posts/{post_id}
    - **Create Post**: POST /api/posts/
    - **Update Post**: PUT /api/posts/{post_id}
    - **Delete Post**: DELETE /api/posts/{post_id}
    
    ### 👥 KOLs API (JSON) - Requires Authentication
    - **Get All KOLs**: GET /api/kols/
    - **Create KOL**: POST /api/kols/ (Admin only)
    - **Update KOL**: PUT /api/kols/{kol_id} (Admin only)
    - **Delete KOL**: DELETE /api/kols/{kol_id} (Admin only)
    
    ### 🏷️ Categories API (JSON) - Requires Authentication
    - **Get All Categories**: GET /api/categories/
    - **Create Category**: POST /api/categories/ (Admin only)
    - **Update Category**: PUT /api/categories/{category_id} (Admin only)
    - **Delete Category**: DELETE /api/categories/{category_id} (Admin only)
    
    ### 🔧 System
    - **Health Check**: GET /health
    - **API Discovery**: GET /api/discovery
    - **Current User**: GET /me
    - **API Docs**: GET /docs
    
    ### 📚 Documentation
    - **Swagger UI**: GET /docs
    - **ReDoc**: GET /redoc
    
    ###  Authentication for Swagger UI
    - **Step 1**: Login via POST /api/auth/login to get access_token
    - **Step 2**: Click "Authorize" button in Swagger UI
    - **Step 3**: Enter: Bearer {your_access_token}
    - **Step 4**: Test API endpoints
    """,
    version="2.0.0",
    contact={
        "name": "BLACKPINK Fan Site",
        "email": "admin@blackpinkfansite.com",
        "url": "https://blackpinkfansite.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "HTTP server (Development)"
        },
        {
            "url": "https://localhost:8443",
            "description": "HTTPS server (Production)"
        }
    ],
    tags=[
        {
            "name": "authentication",
            "description": "Authentication operations (HTML)"
        },
        {
            "name": "user-management",
            "description": "User management operations (HTML & API)"
        },
        {
            "name": "api-auth",
            "description": "Authentication API (JSON)"
        },
        {
            "name": "posts", 
            "description": "Posts management operations (HTML)"
        },
        {
            "name": "api-posts",
            "description": "Posts API (JSON) - Requires Authentication"
        },
        {
            "name": "api-kols",
            "description": "KOLs API (JSON) - Requires Authentication"
        },
        {
            "name": "api-categories",
            "description": "Categories API (JSON) - Requires Authentication"
        },
        {
            "name": "system",
            "description": "System operations"
        }
    ]
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="app/templates")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*", "Authorization", "Content-Type"],
)

# Add logging middleware
app.middleware("http")(logging_middleware)

# Add authentication middleware
app.middleware("http")(auth_middleware)

# Create tables in database
Base.metadata.create_all(bind=engine)

# ==================== INCLUDE ROUTERS ====================

# HTML Routes (Web Interface)
app.include_router(user_router, prefix="/user", tags=["authentication", "user-management"])
app.include_router(post_router, prefix="/post", tags=["posts"])

# API Routes (JSON)
app.include_router(api_router, prefix="/api", tags=["system"])
app.include_router(auth_api_router, prefix="/api/auth", tags=["api-auth"])
app.include_router(posts_api_router, prefix="/api/posts", tags=["api-posts"])
app.include_router(users_api_router, prefix="/api", tags=["user-management"])
app.include_router(kols_api_router, prefix="/api/kols", tags=["api-kols"])
app.include_router(categories_api_router, prefix="/api/categories", tags=["api-categories"])

# ==================== ROOT ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse, name="root")
async def root(request: Request, db: Session = Depends(get_db)):
    """Trang chủ của ứng dụng"""
    log_debug("=== ACCESSING ROOT PAGE ===", "INFO")
    
    # Lấy username từ cookie
    username = request.cookies.get("username")
    log_debug(f"🔍 Username from cookie: {username}", "DEBUG")
    
    is_admin = False
    if username:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if user:
            is_admin = bool(user.is_admin)

    return templates.TemplateResponse("homepage.html", {
        "request": request,
        "username": username,
        "is_admin": is_admin
    })

# ==================== AUTHENTICATION ENDPOINTS ====================

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Lấy user từ Bearer token cho Swagger UI"""
    try:
        token = credentials.credentials
        username = verify_token(token)
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/me", name="get_current_user")
async def get_current_user_info(user: UserModel = Depends(get_current_user_from_token)):
    """Lấy thông tin user hiện tại"""
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
        }
    }

# ==================== SYSTEM ENDPOINTS ====================

@app.get("/health", name="health_check")
async def health_check():
    """Kiểm tra trạng thái hệ thống"""
    log_debug("Health check endpoint called", "INFO")
    return {
        "status": "healthy",
        "message": "BLACKPINK Fan Site API is running",
        "version": "2.0.0",
        "database": "connected",
        "endpoints": {
            "html_routes": ["/user/*", "/post/*"],
            "api_routes": ["/api/*"],
            "docs": ["/docs", "/redoc"]
        }
    }

# ==================== ERROR HANDLERS ====================

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """Handle 401 Unauthorized errors"""
    log_debug(f"🔒 Unauthorized access attempt to: {request.url}", "WARNING")
    
    # Nếu là API request, trả về JSON
    if request.url.path.startswith("/api/"):
        return {"error": "Authentication required", "detail": exc.detail}
    
    # Nếu là HTML request, redirect về login page
    return RedirectResponse(url="/user/login-page", status_code=302)

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    """Handle 403 Forbidden errors"""
    log_debug(f"🚫 Forbidden access attempt to: {request.url}", "WARNING")
    
    # Nếu là API request, trả về JSON
    if request.url.path.startswith("/api/"):
        return {"error": "Access denied", "detail": exc.detail}
    
    # Nếu là HTML request, redirect về homepage với error message
    return templates.TemplateResponse("homepage.html", {
        "request": request,
        "error": "Access denied. Please login first."
    })

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 Not Found errors"""
    log_debug(f"🔍 Not found: {request.url}", "WARNING")
    
    # Nếu là API request, trả về JSON
    if request.url.path.startswith("/api/"):
        return {"error": "Endpoint not found", "detail": exc.detail}
    
    # Nếu là HTML request, redirect về homepage
    return RedirectResponse(url="/", status_code=302)

# ==================== STARTUP EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Chạy khi ứng dụng khởi động"""
    log_debug("🚀 Application starting up...", "INFO")
    log_debug("📊 Database tables created", "INFO")
    log_debug("🔧 Middleware configured", "INFO")
    log_debug("📚 API documentation available at /docs", "INFO")

@app.on_event("shutdown")
async def shutdown_event():
    """Chạy khi ứng dụng tắt"""
    log_debug("🛑 Application shutting down...", "INFO")

# ==================== DEBUG INFO ====================

# Log tất cả routes khi khởi động
log_debug(f"🔍 Total routes registered: {len(app.routes)}", "INFO")
log_debug(f"🔍 Available routes: {[route.name for route in app.routes if hasattr(route, 'name')]}", "DEBUG")

