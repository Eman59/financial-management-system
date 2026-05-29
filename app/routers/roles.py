from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.role import Role, Permission, UserRole
from app.schemas.role import (
    RoleCreate,
    RoleResponse,
    RoleWithPermissions,
    AssignRoleRequest,
    UserRoleResponse,
    UserPermissionsResponse,
    PermissionSchema,
)
from app.services.auth_service import get_current_user, check_permission

router = APIRouter(tags=["Roles & Permissions"])


@router.post("/roles/create", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("*", "*")),
):
    """Create a new role with optional permissions (admin only)."""
    # Check if role already exists
    result = await db.execute(select(Role).where(Role.name == role_data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists",
        )

    role = Role(name=role_data.name, description=role_data.description)
    db.add(role)
    await db.flush()

    # Add permissions if provided
    if role_data.permissions:
        for perm_data in role_data.permissions:
            perm = Permission(
                role_id=role.id,
                resource=perm_data.get("resource", "*"),
                action=perm_data.get("action", "*"),
            )
            db.add(perm)
        await db.flush()

    await db.refresh(role)
    return role


@router.post("/users/assign-role", status_code=status.HTTP_200_OK)
async def assign_role(
    request: AssignRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("*", "*")),
):
    """Assign a role to a user (admin only)."""
    # Verify user exists
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify role exists
    result = await db.execute(select(Role).where(Role.id == request.role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Check if already assigned
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == request.user_id, UserRole.role_id == request.role_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already assigned to user",
        )

    user_role = UserRole(user_id=request.user_id, role_id=request.role_id)
    db.add(user_role)
    await db.flush()

    return {"message": f"Role '{role.name}' assigned to user '{user.username}'"}


@router.get("/users/{user_id}/roles", response_model=list[UserRoleResponse])
async def get_user_roles(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get roles assigned to a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    user_roles = result.scalars().all()

    roles_response = []
    for ur in user_roles:
        role_result = await db.execute(select(Role).where(Role.id == ur.role_id))
        role = role_result.scalar_one_or_none()
        if role:
            roles_response.append(
                UserRoleResponse(
                    role_id=role.id,
                    role_name=role.name,
                    assigned_at=ur.assigned_at,
                )
            )

    return roles_response


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """View user permissions based on assigned roles."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    user_roles = result.scalars().all()

    permissions = []
    for ur in user_roles:
        role_result = await db.execute(
            select(Role).where(Role.id == ur.role_id)
        )
        role = role_result.scalar_one_or_none()
        if role:
            perm_result = await db.execute(
                select(Permission).where(Permission.role_id == role.id)
            )
            perms = perm_result.scalars().all()
            for p in perms:
                permissions.append(PermissionSchema(resource=p.resource, action=p.action))

    return UserPermissionsResponse(user_id=user_id, permissions=permissions)
