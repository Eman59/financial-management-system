"""
Seed script to create default roles and permissions.
Run: python seed_roles.py
"""

import asyncio
from app.database import async_session, init_db
from app.models.role import Role, Permission
from sqlalchemy import select


DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Full access to all resources",
        "permissions": [{"resource": "*", "action": "*"}],
    },
    {
        "name": "analyst",
        "description": "Upload and edit documents",
        "permissions": [
            {"resource": "documents", "action": "upload"},
            {"resource": "documents", "action": "read"},
            {"resource": "documents", "action": "edit"},
            {"resource": "rag", "action": "search"},
            {"resource": "rag", "action": "index"},
        ],
    },
    {
        "name": "auditor",
        "description": "Review documents (read-only access)",
        "permissions": [
            {"resource": "documents", "action": "read"},
            {"resource": "rag", "action": "search"},
        ],
    },
    {
        "name": "client",
        "description": "View company documents only",
        "permissions": [
            {"resource": "documents", "action": "read"},
        ],
    },
]


async def seed():
    await init_db()

    async with async_session() as session:
        for role_data in DEFAULT_ROLES:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"Role '{role_data['name']}' already exists, skipping.")
                continue

            role = Role(name=role_data["name"], description=role_data["description"])
            session.add(role)
            await session.flush()

            for perm_data in role_data["permissions"]:
                perm = Permission(
                    role_id=role.id,
                    resource=perm_data["resource"],
                    action=perm_data["action"],
                )
                session.add(perm)

            print(f"Created role: {role_data['name']}")

        await session.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
