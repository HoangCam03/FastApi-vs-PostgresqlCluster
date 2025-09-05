from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class PostModel(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(String(500), nullable=True)
    images = Column(String(255), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Khóa ngoại đến KOL và Category
    kol_id = Column(Integer, ForeignKey("kols.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - chỉ dùng string để tránh circular import
    kol = relationship("KOLModel", back_populates="posts")
    category = relationship("CategoryModel", back_populates="posts")
    author = relationship("UserModel")
    
    def __repr__(self):
        return f"<PostModel(id={self.id}, title='{self.title}', kol_id={self.kol_id}, category_id={self.category_id})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "excerpt": self.excerpt,
            "images": self.images,
            "author_id": self.author_id,
            "kol_id": self.kol_id,
            "category_id": self.category_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Include related data
            "kol_name": self.kol.name if self.kol else None,
            "category_name": self.category.name if self.category else None,
            "author_username": self.author.username if self.author else None
        }
