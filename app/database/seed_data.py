from sqlalchemy.orm import Session
from app.database.connection import engine
from app.middleware.models.kol_model import KOLModel
from app.middleware.models.category_model import CategoryModel

def seed_initial_data():
    """Thêm dữ liệu mẫu cho KOL và Category"""
    with Session(engine) as session:
        # Thêm KOLs mẫu
        kols = [
            KOLModel(name="Jennie", description="BLACKPINK Jennie", avatar="jennie.jpg"),
            KOLModel(name="Jisoo", description="BLACKPINK Jisoo", avatar="jisoo.jpg"),
            KOLModel(name="Lisa", description="BLACKPINK Lisa", avatar="lisa.jpg"),
            KOLModel(name="Rose", description="BLACKPINK Rose", avatar="rose.jpg"),
        ]
        
        # Thêm Categories mẫu
        categories = [
            CategoryModel(name="Music", description="Âm nhạc", color="#FF6B6B"),
            CategoryModel(name="Fashion", description="Thời trang", color="#4ECDC4"),
            CategoryModel(name="Beauty", description="Làm đẹp", color="#45B7D1"),
            CategoryModel(name="Lifestyle", description="Phong cách sống", color="#96CEB4"),
            CategoryModel(name="Travel", description="Du lịch", color="#FFEAA7"),
        ]
        
        # Kiểm tra xem đã có dữ liệu chưa
        existing_kols = session.query(KOLModel).count()
        existing_categories = session.query(CategoryModel).count()
        
        if existing_kols == 0:
            session.add_all(kols)
            print("✅ Added sample KOLs")
        
        if existing_categories == 0:
            session.add_all(categories)
            print("✅ Added sample categories")
        
        session.commit()
        print("✅ Database seeded successfully!")

if __name__ == "__main__":
    seed_initial_data()