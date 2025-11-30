from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import Outfit, Clothing
from app.schemas.clothes import OutfitCreate
from typing import List


async def create_outfit(
        db: AsyncSession,
        outfit_data: OutfitCreate,
        user_id: int
) -> Outfit:
    # Verify that all clothing items exist
    stmt = select(Clothing).where(Clothing.id.in_(outfit_data.clothing_ids))
    result = await db.execute(stmt)
    existing_clothes = result.scalars().all()

    # Check if we found all requested clothing items
    found_ids = {clothing.id for clothing in existing_clothes}
    missing_ids = set(outfit_data.clothing_ids) - found_ids

    if missing_ids:
        raise ValueError(f"Clothing items not found: {missing_ids}")

    # Check if we have between 1-15 items
    if len(existing_clothes) < 1 or len(existing_clothes) > 15:
        raise ValueError("Outfit must contain between 1 and 15 clothing items")

    # Create the outfit
    outfit = Outfit(
        user_id=user_id,
        name=outfit_data.name
    )

    # Add the clothing items to the outfit
    outfit.clothes.extend(existing_clothes)

    db.add(outfit)
    await db.commit()
    await db.refresh(outfit)

    return outfit


async def get_user_outfits(db: AsyncSession, user_id: int) -> List[Outfit]:
    stmt = select(Outfit).where(Outfit.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_outfit_with_clothes(db: AsyncSession, outfit_id: int) -> Outfit:
    stmt = select(Outfit).where(Outfit.id == outfit_id)
    result = await db.execute(stmt)
    outfit = result.scalar_one_or_none()
    return outfit