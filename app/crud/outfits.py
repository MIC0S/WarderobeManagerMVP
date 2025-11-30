from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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

    # Reload the outfit with clothes relationship
    stmt = select(Outfit).where(Outfit.id == outfit.id).options(
        selectinload(Outfit.clothes)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_user_outfits(db: AsyncSession, user_id: int) -> List[Outfit]:
    """Get all outfits for a user with their clothing items"""
    stmt = select(Outfit).where(Outfit.user_id == user_id).options(
        selectinload(Outfit.clothes)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_outfit_by_id(db: AsyncSession, outfit_id: int, user_id: int) -> Outfit:
    """Get a specific outfit by ID for a user"""
    stmt = select(Outfit).where(
        (Outfit.id == outfit_id) & (Outfit.user_id == user_id)
    ).options(selectinload(Outfit.clothes))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_outfit(
        db: AsyncSession,
        outfit_id: int,
        user_id: int,
        outfit_data: OutfitCreate
) -> Outfit:
    """Update an existing outfit"""
    outfit = await get_outfit_by_id(db, outfit_id, user_id)
    if not outfit:
        raise ValueError("Outfit not found")

    # Verify new clothing items exist
    stmt = select(Clothing).where(Clothing.id.in_(outfit_data.clothing_ids))
    result = await db.execute(stmt)
    existing_clothes = result.scalars().all()

    found_ids = {clothing.id for clothing in existing_clothes}
    missing_ids = set(outfit_data.clothing_ids) - found_ids

    if missing_ids:
        raise ValueError(f"Clothing items not found: {missing_ids}")

    if len(existing_clothes) < 1 or len(existing_clothes) > 15:
        raise ValueError("Outfit must contain between 1 and 15 clothing items")

    # Update outfit
    outfit.name = outfit_data.name
    outfit.clothes = existing_clothes  # Replace all clothing items

    await db.commit()
    await db.refresh(outfit)

    # Reload with clothes
    stmt = select(Outfit).where(Outfit.id == outfit.id).options(
        selectinload(Outfit.clothes)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def delete_outfit(db: AsyncSession, outfit_id: int, user_id: int) -> bool:
    """Delete an outfit"""
    outfit = await get_outfit_by_id(db, outfit_id, user_id)
    if not outfit:
        return False

    await db.delete(outfit)
    await db.commit()
    return True