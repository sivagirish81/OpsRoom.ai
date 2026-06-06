import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
import weave
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery

from backend.config import get_settings

VECTOR_DIMS = 256
INDEX_NAME = "opsroom-runbooks"
PREFIX = "opsroom:runbook"


def _embedding(text: str) -> list[float]:
    vector = np.zeros(VECTOR_DIMS, dtype=np.float32)
    tokens = [token.strip(".,:;!?()[]{}").lower() for token in text.split()]
    for token in filter(None, tokens):
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % VECTOR_DIMS
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(float(np.dot(vector, vector))) or 1.0
    return (vector / norm).tolist()


def get_index() -> SearchIndex:
    schema = {
        "index": {"name": INDEX_NAME, "prefix": f"{PREFIX}:", "storage_type": "hash"},
        "fields": [
            {"name": "title", "type": "text"},
            {"name": "category", "type": "tag"},
            {"name": "content", "type": "text"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "dims": VECTOR_DIMS,
                    "distance_metric": "cosine",
                    "algorithm": "flat",
                    "datatype": "float32",
                },
            },
        ],
    }
    return SearchIndex.from_dict(schema, redis_url=get_settings().redis_url)


@weave.op()
def create_runbook_index() -> None:
    index = get_index()
    try:
        index.create(overwrite=False)
    except Exception as exc:
        if "already exists" not in str(exc).lower():
            raise


@weave.op()
def seed_runbooks(runbook_dir: str) -> int:
    index = get_index()
    create_runbook_index()
    documents = []
    keys = []
    for path in sorted(Path(runbook_dir).glob("*.md")):
        content = path.read_text()
        title = content.splitlines()[0].lstrip("# ").strip()
        documents.append(
            {
                "title": title,
                "category": path.stem,
                "content": content,
                "embedding": np.array(_embedding(content), dtype=np.float32).tobytes(),
            }
        )
        keys.append(path.stem)
    if documents:
        index.load(documents, id_field=None, keys=keys)
    return len(documents)


@weave.op()
def search_runbooks(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    vector_query = VectorQuery(
        vector=_embedding(query),
        vector_field_name="embedding",
        return_fields=["title", "category", "content"],
        num_results=top_k,
    )
    results = get_index().query(vector_query)
    return [
        {
            "title": row["title"],
            "category": row["category"],
            "content": row["content"],
            "score": round(1.0 - float(row["vector_distance"]), 3),
        }
        for row in results
    ]

