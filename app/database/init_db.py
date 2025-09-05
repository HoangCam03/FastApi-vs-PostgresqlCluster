from app.database.connection import engine, Base
from app.middleware.models.user_model import UserModel
from app.middleware.models.post_model import PostModel
from app.middleware.models.kol_model import KOLModel
from app.middleware.models.category_model import CategoryModel

def init_database():
    """Khởi tạo database và tạo tất cả bảng"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")
    print("✅ Tables created: users, posts, kols, categories")

if __name__ == "__main__":
    init_database()
