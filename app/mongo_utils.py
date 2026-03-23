from __future__ import annotations

from typing import Any, Dict

from bson import ObjectId


def to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc
