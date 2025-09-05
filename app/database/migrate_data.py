from sqlalchemy.orm import Session
from app.database.connection import engine
# Import tất cả models để đảm bảo chúng được đăng ký
from app.middleware.models.user_model import UserModel
from app.middleware.models.kol_model import KOLModel
from app.middleware.models.category_model import CategoryModel
from app.middleware.models.post_model import PostModel

def migrate_existing_data():
    """Chuyển đổi dữ liệu từ cột member và category cũ sang khóa ngoại mới"""
    with Session(engine) as session:
        # Lấy tất cả posts hiện tại
        posts = session.query(PostModel).all()
        
        # Tạo mapping cho KOLs
        kol_mapping = {}
        for post in posts:
            if hasattr(post, 'member') and post.member and post.member not in kol_mapping:
                kol = session.query(KOLModel).filter(KOLModel.name == post.member).first()
                if not kol:
                    kol = KOLModel(name=post.member, description=f"KOL {post.member}")
                    session.add(kol)
                    session.flush()  # Để lấy ID
                kol_mapping[post.member] = kol.id
        
        # Tạo mapping cho Categories
        category_mapping = {}
        for post in posts:
            if hasattr(post, 'category') and post.category and post.category not in category_mapping:
                category = session.query(CategoryModel).filter(CategoryModel.name == post.category).first()
                if not category:
                    category = CategoryModel(name=post.category, description=f"Category {post.category}")
                    session.add(category)
                    session.flush()  # Để lấy ID
                category_mapping[post.category] = category.id
        
        # Cập nhật posts với khóa ngoại
        for post in posts:
            if hasattr(post, 'member') and post.member and post.member in kol_mapping:
                post.kol_id = kol_mapping[post.member]
            if hasattr(post, 'category') and post.category and post.category in category_mapping:
                post.category_id = category_mapping[post.category]
        
        session.commit()
        print("✅ Data migration completed successfully!")

if __name__ == "__main__":
    migrate_existing_data()
