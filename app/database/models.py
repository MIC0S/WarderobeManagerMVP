from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from app.database.connection import Base

# Association table for outfit-clothing many-to-many relationship
outfit_clothing = Table(
    'outfit_clothing',
    Base.metadata,
    Column('outfit_id', Integer, ForeignKey('outfits.id'), primary_key=True),
    Column('clothing_id', Integer, ForeignKey('clothing.id'), primary_key=True)
)

# Association table for user-clothing ownership
user_clothing = Table(
    'user_clothing',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('clothing_id', Integer, ForeignKey('clothing.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)  # Store hashed passwords

    # Relationships
    outfits = relationship("Outfit", back_populates="user")
    owned_clothes = relationship("Clothing", secondary=user_clothing, back_populates="owners")


class Clothing(Base):
    __tablename__ = "clothing"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=True)
    color = Column(String(50), nullable=False)
    item_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=False)
    category = Column(String(50), nullable=True)  # NEW: Add category field

    # Relationships remain the same
    outfits = relationship("Outfit", secondary=outfit_clothing, back_populates="clothes")
    owners = relationship("User", secondary=user_clothing, back_populates="owned_clothes")


class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=True)  # Optional outfit name

    # Relationships
    user = relationship("User", back_populates="outfits")
    clothes = relationship("Clothing", secondary=outfit_clothing, back_populates="outfits")