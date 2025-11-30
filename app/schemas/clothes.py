from pydantic import BaseModel
from typing import List, Optional

class ClothingBase(BaseModel):
    name: str
    price: Optional[float] = None
    color: str
    item_url: Optional[str] = None
    image_url: str

class ClothingCreate(ClothingBase):
    pass

class Clothing(ClothingBase):
    id: int

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    owned_clothes: List[Clothing] = []

    class Config:
        orm_mode = True

class OutfitBase(BaseModel):
    name: Optional[str] = None

class OutfitCreate(OutfitBase):
    clothing_ids: List[int]

class Outfit(OutfitBase):
    id: int
    user_id: int
    clothes: List[Clothing] = []

    class Config:
        orm_mode = True