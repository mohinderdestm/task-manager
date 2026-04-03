from fastapi import APIRouter, HTTPException, Depends
from .schemas import UserUpdate
from .crud import get_user, update_user, get_all_users
from .auth import validate_token, require_roles

router = APIRouter(prefix="/users", tags=["Users"])


# --------------------------
# ADMIN ONLY - GET ALL USERS List
# --------------------------
@router.get("/")
async def list_users(token_data: dict = Depends(require_roles(["admin"]))):
    
    users = await get_all_users()
    return {
        "total": len(users),
        "users": users
    }


# --------------------------
# MANAGER ONLY - GET TEAM
# --------------------------
@router.get("/team")
async def get_team(token_data: dict = Depends(require_roles(["manager"]))):
    """
    Manager can get team members.
    (Currently returning all users, can later filter by manager_id)
    """
    users = await get_all_users()
    return {
        "total": len(users),
        "users": users
    }

# --------------------------
# PUBLIC USERS LIST
# --------------------------
@router.get("/public")
async def list_users_public(token_data: dict = Depends(validate_token)):
    users = await get_all_users()

    return [
        {
            "id": str(user.get("_id") or user.get("id")),
            "name": user.get("name") or user.get("email") or "Unknown User"
        }
        for user in users
    ]


# --------------------------
# PUBLIC USER BY ID
# --------------------------
@router.get("/public/{user_id}")
async def get_user_public(
    user_id: str,
    token_data: dict = Depends(validate_token)
):
    user = await get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user.get("_id") or user.get("id")),
        "name": user.get("name") or user.get("email") or "Unknown User"
    }



# --------------------------
# GET USER PROFILE
# --------------------------
@router.get("/{user_id}")
async def get_user_profile(
    user_id: str,
    token_data: dict = Depends(validate_token)
):
    """
    - Employee → can only see their own profile
    - Admin → can see any profile
    - Manager → can see any profile
    """
    user = await get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Self access OR admin/manager access
    if token_data["user_id"] != user_id and token_data.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    return user


# --------------------------
# UPDATE USER PROFILE
# --------------------------
@router.put("/{user_id}")
async def update_user_profile(
    user_id: str,
    user_data: UserUpdate,
    token_data: dict = Depends(validate_token)
):
    """
    - Employee → can update their own profile
    - Admin → can update any user
    """

    user = await get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Self update OR admin update
    if token_data["user_id"] != user_id and token_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    updated_user = await update_user(
        user_id,
        user_data.model_dump(exclude_unset=True)
    )

    return {
        "message": "User updated successfully",
        "user": updated_user
    }

