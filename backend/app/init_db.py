"""Non-destructive, resumable development database bootstrap.

Only create missing collections/indexes. Matching objects are untouched. Conflicting
validators/options/indexes cause a preflight failure, requiring an explicit migration.
No application documents, permission changes, drops, updates or collMod calls.
"""
import asyncio
import logging

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.config import get_settings
from app.schema import INDEXES, VALIDATORS


class SchemaConflict(RuntimeError):
    pass


def index_matches(actual, desired):
    return (
        list(actual["key"].items()) == list(desired["key"].items())
        and bool(actual.get("unique", False)) == bool(desired.get("unique", False))
        and actual.get("partialFilterExpression") == desired.get("partialFilterExpression")
        and not actual.get("sparse", False)
        and "expireAfterSeconds" not in actual
        and not actual.get("hidden", False)
        and "collation" not in actual
    )


def options_match(actual, validator):
    return (
        actual.get("validator") == validator
        and actual.get("validationLevel", "strict") == "strict"
        and actual.get("validationAction", "error") == "error"
        and not actual.get("capped", False)
        and not any(key in actual for key in ("timeseries", "clusteredIndex", "collation", "viewOn"))
    )


async def inspect(db):
    cursor = await db.list_collections()
    return {item["name"]: item async for item in cursor}


async def preflight(db):
    existing = await inspect(db)
    conflicts = []
    for name, validator in VALIDATORS.items():
        if name not in existing:
            continue
        if existing[name].get("type") != "collection" or not options_match(existing[name].get("options", {}), validator):
            conflicts.append(name + ": validator or collection options differ")
        actual_indexes = await db[name].index_information()
        for model in INDEXES[name]:
            desired = model.document
            for actual_name, actual in actual_indexes.items():
                same_key = list(actual["key"]) == list(desired["key"].items())
                if actual_name == desired["name"] or same_key:
                    # index_information represents keys as pairs, unlike list_indexes.
                    normal = {**actual, "key": dict(actual["key"])}
                    if actual_name != desired["name"] or not index_matches(normal, desired):
                        conflicts.append(name + ": conflicting index " + actual_name)
    if conflicts:
        raise SchemaConflict("; ".join(conflicts))
    return existing


async def verify(db):
    existing = await inspect(db)
    result = {}
    for name, validator in VALIDATORS.items():
        if name not in existing or not options_match(existing[name].get("options", {}), validator):
            raise SchemaConflict(name + ": collection validator verification failed")
        cursor = await db[name].list_indexes()
        indexes = {item["name"]: item async for item in cursor}
        for model in INDEXES[name]:
            desired = model.document
            if desired["name"] not in indexes or not index_matches(indexes[desired["name"]], desired):
                raise SchemaConflict(name + ": index verification failed")
        result[name] = {"documents": await db[name].count_documents({}), "indexes": len(indexes)}
    return result


async def initialise_database(db):
    existing = await preflight(db)  # All conflicts checked before any mutation.
    created = []
    for name, validator in VALIDATORS.items():
        if name not in existing:
            await db.create_collection(name, validator=validator, validationLevel="strict", validationAction="error")
            created.append(name)
        # createIndexes is idempotent for identical named specs. Never drop/rebuild.
        await db[name].create_indexes(INDEXES[name])
    verified = await verify(db)
    return {"created": created, "verified": verified}


async def initialise():
    settings = get_settings()
    if settings.app_env != "development" or settings.mongodb_database != "solaris":
        raise SystemExit("Refusing setup: requires APP_ENV=development and MONGODB_DATABASE=solaris")
    if not settings.mongodb_uri.get_secret_value():
        raise SystemExit("Set MONGODB_URI in backend/.env first")
    async with AsyncMongoClient(settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=15000) as client:
        result = await initialise_database(client[settings.mongodb_database])
        print("Created collections: " + (", ".join(result["created"]) or "none (already initialised)"))
        for name, details in result["verified"].items():
            print(f"VERIFIED {name}: strict validator, {details['indexes']} indexes, {details['documents']} documents")
        print(f"Verified {len(result['verified'])} collections; no application records inserted or modified")
    return result


if __name__ == "__main__":
    logging.getLogger("pymongo").setLevel(logging.CRITICAL)
    try:
        asyncio.run(initialise())
    except SchemaConflict as exc:
        raise SystemExit("Schema conflict (no automatic replacement): " + str(exc)) from None
    except PyMongoError as exc:
        # Driver errors can embed hostnames, credentials or document contents.
        raise SystemExit(f"Database setup failed: {type(exc).__name__}; code={getattr(exc, 'code', None)}. No permissions changed. Completed steps are safe to rerun.") from None
    except Exception as exc:
        raise SystemExit(f"Setup failed: {type(exc).__name__}. Details suppressed to protect configuration.") from None
