from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.models import User, Clothing
import random


async def get_users_with_stats(db: AsyncSession):
    """Get all users with their relationships eagerly loaded for admin display"""
    stmt = select(User).options(
        selectinload(User.owned_clothes),
        selectinload(User.outfits)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def assign_random_clothes_to_user(db: AsyncSession, user_id: int, item_count: int):
    """Assign random clothes to a specific user"""
    # Get user with relationships
    stmt_user = select(User).where(User.id == user_id).options(
        selectinload(User.owned_clothes)
    )
    result_user = await db.execute(stmt_user)
    user = result_user.scalar_one_or_none()

    if not user:
        return None, "User not found"

    # Get all available clothes
    stmt_clothes = select(Clothing)
    result_clothes = await db.execute(stmt_clothes)
    all_clothes = result_clothes.scalars().all()

    if len(all_clothes) < item_count:
        return None, f"Not enough clothes in master list. Only {len(all_clothes)} available."

    # Get currently owned clothing IDs
    owned_ids = {clothing.id for clothing in user.owned_clothes}

    # Filter available clothes
    available_clothes = [clothing for clothing in all_clothes if clothing.id not in owned_ids]

    if len(available_clothes) < item_count:
        return None, f"Not enough available clothes. Only {len(available_clothes)} available that user doesn't already own."

    # Randomly select and assign
    selected_clothes = random.sample(available_clothes, item_count)
    for clothing in selected_clothes:
        user.owned_clothes.append(clothing)

    await db.commit()
    return len(selected_clothes), None


async def assign_random_clothes_to_all_users(db: AsyncSession, item_count: int):
    """Assign random clothes to all users"""
    # Get all users with relationships
    stmt_users = select(User).options(selectinload(User.owned_clothes))
    result_users = await db.execute(stmt_users)
    all_users = result_users.scalars().all()

    # Get all available clothes
    stmt_clothes = select(Clothing)
    result_clothes = await db.execute(stmt_clothes)
    all_clothes = result_clothes.scalars().all()

    if len(all_clothes) < item_count:
        return 0, f"Not enough clothes in master list. Only {len(all_clothes)} available."

    assigned_count = 0
    for user in all_users:
        # Get currently owned clothing IDs
        owned_ids = {clothing.id for clothing in user.owned_clothes}

        # Filter available clothes
        available_clothes = [clothing for clothing in all_clothes if clothing.id not in owned_ids]

        # Use available clothes (might be less than requested)
        actual_count = min(item_count, len(available_clothes))
        if actual_count > 0:
            selected_clothes = random.sample(available_clothes, actual_count)
            for clothing in selected_clothes:
                user.owned_clothes.append(clothing)
                assigned_count += 1

    await db.commit()
    return assigned_count, None