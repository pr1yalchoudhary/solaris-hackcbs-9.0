"""Explicit setup only; never runs on web-server startup."""
import asyncio

from pymongo import AsyncMongoClient

from app.config import get_settings
from app.schema import INDEXES, SCHEMAS


async def initialise():
    settings = get_settings()
    if not settings.mongodb_uri.get_secret_value():
        raise SystemExit("Set MONGODB_URI in backend/.env first")
    async with AsyncMongoClient(settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000) as client:
        db = client[settings.mongodb_database]
        existing = await db.list_collection_names()
        for name, validator in SCHEMAS.items():
            options = {"validator": {"$jsonSchema": validator}, "validationLevel": "strict", "validationAction": "error"}
            if name in existing:
                await db.command({"collMod": name, **options})
            else:
                await db.create_collection(name, **options)
            await db[name].create_indexes(INDEXES[name])
        print(f"Validated {len(SCHEMAS)} collection definitions and indexes")


if __name__ == "__main__":
    asyncio.run(initialise())
