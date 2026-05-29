from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    permissions: Optional[List[dict]] = None


class PermissionSchema(BaseModel):
    resource: str
    action: str


class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    permissions: List[PermissionSchema] = []


class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str


class UserRoleResponse(BaseModel):
    role_id: str
    role_name: str
    assigned_at: datetime


class UserPermissionsResponse(BaseModel):
    user_id: str
    permissions: List[PermissionSchema]
