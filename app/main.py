import asyncio
import json
import random

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from sqlalchemy.orm import selectinload
from pathlib import Path

from starlette.websockets import WebSocketDisconnect

from app.crud.admin import get_users_with_stats, assign_random_clothes_to_user, assign_random_clothes_to_all_users

# Import config and database
from app.config import config
from app.crud.outfits import delete_outfit, update_outfit, get_user_outfits, create_outfit
from app.database.connection import get_db, init_db, close_db, AsyncSessionLocal
from app.database.models import User, Clothing, Outfit
from app.schemas import OutfitCreate

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Dependency to get current user - can be used in Depends()"""
    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None

        # Verify user still exists in database
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            return None

        return username
    except jwt.JWTError:
        return None

async def get_current_user_as_dependency(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> str:
    """Dependency version that can raise HTTPException"""
    username = await get_current_user(request, db)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return username


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    await close_db()


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "error": error,
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION
        }
    )


@app.post("/")
async def login_or_register(request: Request, db: AsyncSession = Depends(get_db)):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    action = form_data.get("action")  # "login" or "register"

    if not username or not password:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Username and password required",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

    if action == "register":
        # Check if username already exists in database
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "error": "Username already exists",
                    "app_name": config.APP_NAME,
                    "app_version": config.APP_VERSION
                }
            )

        # Create new user in database
        hashed_password = hash_password(password)
        new_user = User(username=username, password=hashed_password)

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Create token for new user
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        response = RedirectResponse(url="/app", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        return response

    elif action == "login":
        # Find user in database
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password):
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "error": "Invalid username or password",
                    "app_name": config.APP_NAME,
                    "app_version": config.APP_VERSION
                }
            )

        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        response = RedirectResponse(url="/app", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        return response

    else:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Invalid action",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )


@app.get("/app", response_class=HTMLResponse)
async def app_main(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    username = await get_current_user(request, db)
    if not username:
        return RedirectResponse(url="/")

    # Get current user with owned_clothes eagerly loaded
    stmt_user = select(User).where(User.username == username).options(
        selectinload(User.owned_clothes)
    )
    result_user = await db.execute(stmt_user)
    current_user = result_user.scalar_one_or_none()

    if not current_user:
        return RedirectResponse(url="/")

    # Get only the clothes owned by the current user
    wardrobe_data = []
    for clothing in current_user.owned_clothes:
        wardrobe_data.append({
            "id": clothing.id,
            "name": clothing.name,
            "category": clothing.category if clothing.category else "Не указано",
            "image_url": clothing.image_url,
            "color": clothing.color,
            "price": clothing.price,
            "item_url": clothing.item_url
        })

    return templates.TemplateResponse(
        "app/main.html",
        {
            "request": request,
            "username": username,
            "wardrobe_items": wardrobe_data,
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION,
            "category_names": config.CATEGORY_NAMES,
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Handle real-time communication here
            # For now, just echo back
            await websocket.send_text(f"Message received: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.websocket("/ws/outfits")
async def websocket_outfits(websocket: WebSocket):
    await websocket.accept()
    print(f"WebSocket connected: {websocket.client}")

    # Create a database session for the entire WebSocket connection
    db = AsyncSessionLocal()

    try:
        while True:
            # Add timeout to prevent hanging
            data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            print(f"Received WebSocket message: {data}")

            if data["type"] == "create_outfit":
                print("Handling create_outfit request")
                await handle_create_outfit(websocket, db, data)

            elif data["type"] == "get_outfits":
                print("Handling get_outfits request")
                await handle_get_outfits(websocket, db, data)

            elif data["type"] == "update_outfit":
                await handle_update_outfit(websocket, db, data)

            elif data["type"] == "delete_outfit":
                await handle_delete_outfit(websocket, db, data)
            else:
                # Check if connection is still open before sending
                if websocket.client_state.CONNECTED:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {data['type']}"
                    })

    except asyncio.TimeoutError:
        print("WebSocket timeout - closing connection")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        # Check if connection is still open before sending
        if websocket.client_state.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON format"
            })
    except WebSocketDisconnect:
        print("WebSocket disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Only send error if connection is still open
        if websocket.client_state.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "message": "Internal server error"
            })
    finally:
        # Close the database session when WebSocket closes
        await db.close()
        print(f"WebSocket connection closed: {websocket.client}")

async def handle_create_outfit(websocket: WebSocket, db: AsyncSession, data: dict):
    """Handle outfit creation via WebSocket"""
    try:
        username = data.get("username")
        if not username:
            if websocket.client_state.CONNECTED:
                await websocket.send_json({
                    "type": "error",
                    "message": "User not authenticated"
                })
            return

        # Get user ID
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await websocket.send_json({
                "type": "error",
                "message": "User not found"
            })
            return

        # Validate input data
        if "outfit" not in data or "name" not in data["outfit"] or "item_ids" not in data["outfit"]:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid outfit data format"
            })
            return

        # Create outfit
        outfit_data = OutfitCreate(
            name=data["outfit"]["name"],
            clothing_ids=data["outfit"]["item_ids"]
        )

        outfit = await create_outfit(db, outfit_data, user.id)

        # Convert to serializable format
        outfit_dict = {
            "id": outfit.id,
            "name": outfit.name,
            "items": [
                {
                    "id": clothing.id,
                    "name": clothing.name,
                    "image_url": clothing.image_url,
                    "category": clothing.category
                }
                for clothing in outfit.clothes
            ]
        }
        await websocket.send_json({
            "type": "outfit_created",
            "outfit": outfit_dict
        })
    except ValueError as e:
        if websocket.client_state.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
    except Exception as e:
        print(f"Error in handle_create_outfit: {e}")
        if websocket.client_state.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to create outfit: {str(e)}"
            })


async def handle_get_outfits(websocket: WebSocket, db: AsyncSession, data: dict):
    """Handle fetching user's outfits via WebSocket"""
    username = data.get("username")
    if not username:
        await websocket.send_json({
            "type": "error",
            "message": "User not authenticated"
        })
        return

    # Get user ID
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await websocket.send_json({
            "type": "error",
            "message": "User not found"
        })
        return

    # Get user's outfits
    outfits = await get_user_outfits(db, user.id)

    outfit_list = []
    for outfit in outfits:
        outfit_list.append({
            "id": outfit.id,
            "name": outfit.name,
            "items": [
                {
                    "id": clothing.id,
                    "name": clothing.name,
                    "image_url": clothing.image_url,
                    "category": clothing.category
                }
                for clothing in outfit.clothes
            ]
        })

    await websocket.send_json({
        "type": "outfits_list",
        "outfits": outfit_list
    })


async def handle_update_outfit(websocket: WebSocket, db: AsyncSession, data: dict):
    """Handle outfit update via WebSocket"""
    username = data.get("username")
    if not username:
        await websocket.send_json({
            "type": "error",
            "message": "User not authenticated"
        })
        return

    # Get user ID
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await websocket.send_json({
            "type": "error",
            "message": "User not found"
        })
        return

    try:
        outfit_data = OutfitCreate(
            name=data["outfit"]["name"],
            clothing_ids=data["outfit"]["item_ids"]
        )

        outfit = await update_outfit(db, data["outfit_id"], user.id, outfit_data)

        # Convert to serializable format
        outfit_dict = {
            "id": outfit.id,
            "name": outfit.name,
            "items": [
                {
                    "id": clothing.id,
                    "name": clothing.name,
                    "image_url": clothing.image_url,
                    "category": clothing.category
                }
                for clothing in outfit.clothes
            ]
        }

        await websocket.send_json({
            "type": "outfit_updated",
            "outfit": outfit_dict
        })

    except ValueError as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


async def handle_delete_outfit(websocket: WebSocket, db: AsyncSession, data: dict):
    """Handle outfit deletion via WebSocket"""
    username = data.get("username")
    if not username:
        await websocket.send_json({
            "type": "error",
            "message": "User not authenticated"
        })
        return

    # Get user ID
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await websocket.send_json({
            "type": "error",
            "message": "User not found"
        })
        return

    success = await delete_outfit(db, data["outfit_id"], user.id)

    if success:
        await websocket.send_json({
            "type": "outfit_deleted",
            "outfit_id": data["outfit_id"]
        })
    else:
        await websocket.send_json({
            "type": "error",
            "message": "Outfit not found or access denied"
        })

async def verify_admin_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Verify the user is authenticated AND is the admin (Micos)"""
    username = await get_current_user(request, db)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Check if the user is the admin (Micos)
    if username != "Micos":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return username


@app.get("/admin/fill", response_class=HTMLResponse)
async def admin_fill(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    users = await get_users_with_stats(db)

    return templates.TemplateResponse(
        "admin/fill.html",
        {
            "request": request,
            "users": users,
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION
        }
    )


@app.post("/admin/fill/single")
async def fill_single_user(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    form_data = await request.form()
    user_id = int(form_data.get("user_id"))
    item_count = int(form_data.get("item_count"))

    assigned_count, error = await assign_random_clothes_to_user(db, user_id, item_count)

    users = await get_users_with_stats(db)

    if error:
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": error,
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

    return templates.TemplateResponse(
        "admin/fill.html",
        {
            "request": request,
            "users": users,
            "success": f"Successfully assigned {assigned_count} random clothes to user",
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION
        }
    )


@app.post("/admin/fill/all")
async def fill_all_users(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    form_data = await request.form()
    item_count = int(form_data.get("all_users_count"))

    assigned_count, error = await assign_random_clothes_to_all_users(db, item_count)

    users = await get_users_with_stats(db)

    if error:
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": error,
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

    return templates.TemplateResponse(
        "admin/fill.html",
        {
            "request": request,
            "users": users,
            "success": f"Successfully assigned clothes to all users ({assigned_count} total assignments)",
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION
        }
    )


from sqlalchemy import text

async def update_clothing_sequence(db: AsyncSession):
    """Update the clothing ID sequence to avoid conflicts with manually set IDs"""
    try:
        # Get the maximum ID currently in use
        result = await db.execute(text("SELECT COALESCE(MAX(id), 0) FROM clothing"))
        max_id = result.scalar()

        # Update the sequence to start from max_id + 1
        await db.execute(text(f"SELECT setval('clothing_id_seq', {max_id + 1})"))
        await db.commit()
    except Exception as e:
        print(f"Warning: Could not update sequence: {e}")

@app.post("/admin/fill/import-clothes")
async def import_clothes_from_file(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    try:
        # Read the JSON file
        file_path = Path("data/raw.txt")
        if not file_path.exists():
            users = await get_users_with_stats(db)
            return templates.TemplateResponse(
                "admin/fill.html",
                {
                    "request": request,
                    "users": users,
                    "error": "File data/raw.txt not found",
                    "app_name": config.APP_NAME,
                    "app_version": config.APP_VERSION
                }
            )

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process each clothing item
        imported_count = 0
        skipped_count = 0

        for item_id, item_data in data.items():
            # Convert item_id to integer
            try:
                clothing_id = int(item_id)
            except ValueError:
                # Skip if ID is not a valid integer
                skipped_count += 1
                continue

            # Check if clothing with this ID already exists
            stmt = select(Clothing).where(Clothing.id == clothing_id)
            result = await db.execute(stmt)
            existing_clothing = result.scalar_one_or_none()

            if existing_clothing:
                skipped_count += 1
                continue

            # Clean price - remove currency symbol and spaces, convert to float
            price_str = item_data['price'].replace('₽', '').replace(' ', '').strip()
            try:
                price = float(price_str) if price_str else None
            except (ValueError, TypeError):
                price = None

            # Create new clothing item with the original JSON ID
            new_clothing = Clothing(
                id=clothing_id,  # Set the ID from JSON
                name=item_data['name'],
                color=item_data['color'],
                image_url=item_data['image_url'],
                item_url=item_data['item_url'],
                price=price
            )

            db.add(new_clothing)
            imported_count += 1

        await db.commit()

        # Update the sequence after import
        await update_clothing_sequence(db)

        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "success": f"Successfully imported {imported_count} new clothing items. Skipped {skipped_count} duplicates.",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

    except json.JSONDecodeError as e:
        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": f"Invalid JSON format in file: {str(e)}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )
    except Exception as e:
        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": f"Error importing clothes: {str(e)}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

@app.post("/admin/clear/clothes")
async def clear_clothes(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    try:
        # First clear the association tables that reference clothing
        await db.execute(text("DELETE FROM outfit_clothing"))
        await db.execute(text("DELETE FROM user_clothing"))

        # Then clear the clothes table
        await db.execute(text("DELETE FROM clothing"))
        await db.commit()

        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "success": "All clothes and their associations cleared successfully",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )
    except Exception as e:
        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": f"Error clearing clothes: {str(e)}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

@app.post("/admin/clear/ownings")
async def clear_ownings(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    try:
        await db.execute(text("DELETE FROM user_clothing"))
        await db.commit()

        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "success": "All clothing ownerships cleared successfully",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )
    except Exception as e:
        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": f"Error clearing ownings: {str(e)}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

@app.post("/admin/clear/outfits")
async def clear_outfits(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    try:
        await db.execute(text("DELETE FROM outfit_clothing"))
        await db.execute(text("DELETE FROM outfits"))
        await db.commit()

        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "success": "All outfits cleared successfully",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )
    except Exception as e:
        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": f"Error clearing outfits: {str(e)}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

@app.post("/admin/clear/users")
async def clear_users(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    try:
        # Clear association tables first
        await db.execute(text("DELETE FROM outfit_clothing"))
        await db.execute(text("DELETE FROM user_clothing"))

        # Clear outfits (they reference users)
        await db.execute(text("DELETE FROM outfits"))

        # Finally clear users (except the current admin)
        await db.execute(text("DELETE FROM users WHERE username != :admin_username"),
                         {"admin_username": username})
        await db.commit()

        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "success": "All users (except you) and their data cleared successfully",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )
    except Exception as e:
        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": f"Error clearing users: {str(e)}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )


@app.post("/admin/fill/assign-categories")
async def assign_categories(
        request: Request,
        db: AsyncSession = Depends(get_db),
        username: str = Depends(verify_admin_user)
):
    try:
        # Get all clothing items
        stmt = select(Clothing)
        result = await db.execute(stmt)
        all_clothes = result.scalars().all()

        assigned_count = 0
        unknown_categories = set()

        for clothing in all_clothes:
            if not clothing.item_url:
                continue

            # Parse the URL to extract category
            try:
                # Split URL by slashes and find the segment after /catalog/
                url_parts = clothing.item_url.split('/')
                if 'catalog' in url_parts:
                    catalog_index = url_parts.index('catalog')
                    if catalog_index + 1 < len(url_parts):
                        category_slug = url_parts[catalog_index + 1]

                        # Map to display name using config
                        if category_slug in config.CATEGORY_NAMES:
                            clothing.category = config.CATEGORY_NAMES[category_slug]
                            assigned_count += 1
                        else:
                            unknown_categories.add(category_slug)
            except (IndexError, ValueError, AttributeError):
                # Skip if URL parsing fails
                pass

        await db.commit()

        users = await get_users_with_stats(db)

        unknown_msg = ""
        if unknown_categories:
            unknown_msg = f" Unknown categories found: {', '.join(unknown_categories)}"

        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "success": f"Categories assigned to {assigned_count} items.{unknown_msg}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )

    except Exception as e:
        users = await get_users_with_stats(db)
        return templates.TemplateResponse(
            "admin/fill.html",
            {
                "request": request,
                "users": users,
                "error": f"Error assigning categories: {str(e)}",
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION
            }
        )




def run():
    import uvicorn
    uvicorn.run(
        app,
        host=config.HOST_URL,
        port=config.HOST_PORT
    )


if __name__ == "__main__":
    run()