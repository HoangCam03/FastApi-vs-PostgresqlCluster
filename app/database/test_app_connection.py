from app.database.connection import get_primary_db, get_db
from app.middleware.models.post_model import PostModel
from app.middleware.models.user_model import UserModel
from app.middleware.models.kol_model import KOLModel        # thêm
from app.middleware.models.category_model import CategoryModel  # thêm
from sqlalchemy.orm import Session
def test_app_connection():
	print("🔍 Testing app database connections...")
	
	# Test post_db (primary)
	try:
		db = next(get_primary_db())
		posts = db.query(PostModel).all()
		print(f"✅ Post DB (primary): Found {len(posts)} posts")
		db.close()
	except Exception as e:
		print(f"❌ Post DB error: {e}")
	
	# Test user_db (pgbouncer/general)
	try:
		db = next(get_db())
		users = db.query(UserModel).all()
		print(f"✅ User DB (pgbouncer): Found {len(users)} users")
		db.close()
	except Exception as e:
		print(f"❌ User DB error: {e}")

if __name__ == "__main__":
	test_app_connection()