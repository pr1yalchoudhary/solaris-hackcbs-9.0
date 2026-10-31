import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.init_db import SchemaConflict, index_matches, initialise_database, options_match
from app.schema import INDEXES, SCHEMAS, VALIDATORS


def cursor(items):
    async def generate():
        for item in items:
            yield item
    return generate()


def fake_database():
    state = {}
    db = MagicMock()
    db.list_collections = AsyncMock(side_effect=lambda: cursor([
        {"name": name, "type": "collection", "options": value["options"]}
        for name, value in state.items()
    ]))

    async def create(name, **options):
        state[name] = {"options": deepcopy(options), "indexes": {"_id_": {"name": "_id_", "key": {"_id": 1}}}}
    db.create_collection = AsyncMock(side_effect=create)
    collections = {}

    def collection(name):
        if name not in collections:
            coll = MagicMock()

            async def create_indexes(models):
                for model in models:
                    state[name]["indexes"][model.document["name"]] = deepcopy(dict(model.document))
            coll.create_indexes = AsyncMock(side_effect=create_indexes)
            coll.index_information = AsyncMock(side_effect=lambda: {
                key: {**value, "key": list(value["key"].items())}
                for key, value in state[name]["indexes"].items()
            })
            coll.list_indexes = AsyncMock(side_effect=lambda: cursor(state[name]["indexes"].values()))
            coll.count_documents = AsyncMock(return_value=0)
            collections[name] = coll
        return collections[name]
    db.__getitem__.side_effect = collection
    return db, state


def test_initialise_twice_without_replacing_existing_objects():
    async def check():
        db, state = fake_database()
        first = await initialise_database(db)
        before = deepcopy(state)
        second = await initialise_database(db)
        assert set(first["created"]) == set(SCHEMAS)
        assert second["created"] == []
        assert state == before
        assert db.create_collection.await_count == len(SCHEMAS)
        db.command.assert_not_called()  # No collMod, drop or permission commands.
    asyncio.run(check())


def test_conflicting_validator_aborts_before_any_creation():
    async def check():
        db, state = fake_database()
        state["users"] = {"options": {"validator": {}}, "indexes": {}}
        with pytest.raises(SchemaConflict):
            await initialise_database(db)
        db.create_collection.assert_not_awaited()
        db.command.assert_not_called()
    asyncio.run(check())


def test_collection_and_index_contracts():
    assert set(SCHEMAS) == set(VALIDATORS) == set(INDEXES)
    for name, schema in SCHEMAS.items():
        assert schema["additionalProperties"] is False
        assert "pattern" in schema["properties"]["_id"]
        names = [model.document["name"] for model in INDEXES[name]]
        assert len(names) == len(set(names))
    spec = INDEXES["exit_transactions"][0].document
    assert index_matches(spec, spec)
    assert not index_matches({**spec, "unique": False}, spec)
    assert not options_match({"validator": VALIDATORS["users"], "validationAction": "warn"}, VALIDATORS["users"])
    assert SCHEMAS["households"]["properties"]["monthly_consumption_wh"]["anyOf"][1] == {"bsonType": "null"}


def test_conflicting_unique_index_aborts_without_replacement():
    async def check():
        db, state = fake_database()
        spec = deepcopy(dict(INDEXES["users"][0].document))
        spec["unique"] = False
        state["users"] = {
            "options": {"validator": VALIDATORS["users"], "validationLevel": "strict", "validationAction": "error"},
            "indexes": {spec["name"]: spec},
        }
        before = deepcopy(state)
        with pytest.raises(SchemaConflict):
            await initialise_database(db)
        assert state == before
        db.create_collection.assert_not_awaited()
    asyncio.run(check())
