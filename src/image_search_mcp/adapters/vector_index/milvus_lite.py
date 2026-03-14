from pathlib import Path
from typing import Any

from milvus_lite.server_manager import server_manager_instance
from pymilvus import DataType, MilvusClient

from image_search_mcp.adapters.vector_index.base import VectorIndex


class MilvusLiteIndex(VectorIndex):
    _PK_FIELD = "content_hash"
    _VECTOR_FIELD = "embedding"
    _EMBEDDING_KEY_FIELD = "embedding_key"
    _EMBEDDING_PROVIDER_FIELD = "embedding_provider"
    _EMBEDDING_MODEL_FIELD = "embedding_model"
    _EMBEDDING_VERSION_FIELD = "embedding_version"

    def __init__(self, db_path: Path, collection_name: str) -> None:
        uri = server_manager_instance.start_and_get_uri(str(db_path))
        if uri is None:
            raise RuntimeError(f"Failed to start Milvus Lite for {db_path}")
        # MilvusClient's local .db shortcut does not forward the unix socket address
        # into the gRPC handler correctly. Reusing the resolved UDS fixes local access.
        self.client = MilvusClient(uri=uri, address=uri)
        self.collection_name = collection_name

    def ensure_collection(self, dimension: int, embedding_key: str) -> None:
        if self.client.has_collection(self.collection_name):
            return

        self._parse_embedding_key(embedding_key)
        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field(
            field_name=self._PK_FIELD,
            datatype=DataType.VARCHAR,
            is_primary=True,
            max_length=128,
        )
        schema.add_field(
            field_name=self._EMBEDDING_KEY_FIELD,
            datatype=DataType.VARCHAR,
            max_length=256,
        )
        schema.add_field(
            field_name=self._EMBEDDING_PROVIDER_FIELD,
            datatype=DataType.VARCHAR,
            max_length=64,
        )
        schema.add_field(
            field_name=self._EMBEDDING_MODEL_FIELD,
            datatype=DataType.VARCHAR,
            max_length=128,
        )
        schema.add_field(
            field_name=self._EMBEDDING_VERSION_FIELD,
            datatype=DataType.VARCHAR,
            max_length=128,
        )
        schema.add_field(
            field_name=self._VECTOR_FIELD,
            datatype=DataType.FLOAT_VECTOR,
            dim=dimension,
        )

        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(field_name=self._VECTOR_FIELD, metric_type="COSINE")
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )

    def upsert_embeddings(self, records: list[dict]) -> None:
        if not records:
            return
        if not self.client.has_collection(self.collection_name):
            raise RuntimeError("Milvus collection is missing; call ensure_collection first")

        payload: list[dict[str, Any]] = []
        for record in records:
            content_hash = str(record["content_hash"])
            vector = record.get("embedding")
            if vector is None:
                vector = record["vector"]

            embedding_key = record.get("embedding_key")
            if embedding_key is None:
                provider = str(record["embedding_provider"])
                model = str(record["embedding_model"])
                version = str(record["embedding_version"])
                embedding_key = f"{provider}:{model}:{version}"
            else:
                provider, model, version = self._parse_embedding_key(str(embedding_key))

            payload.append(
                {
                    self._PK_FIELD: content_hash,
                    self._VECTOR_FIELD: vector,
                    self._EMBEDDING_KEY_FIELD: embedding_key,
                    self._EMBEDDING_PROVIDER_FIELD: provider,
                    self._EMBEDDING_MODEL_FIELD: model,
                    self._EMBEDDING_VERSION_FIELD: version,
                }
            )

        self.client.upsert(self.collection_name, payload)

    def has_embedding(self, content_hash: str, embedding_key: str) -> bool:
        if not self.client.has_collection(self.collection_name):
            return False

        query = self.client.query_iterator(
            self.collection_name,
            batch_size=1,
            limit=1,
            filter=self._embedding_filter(embedding_key, content_hash=content_hash),
            output_fields=[self._PK_FIELD],
        )
        try:
            return bool(query.next())
        finally:
            query.close()

    def search(self, vector: list[float], limit: int, embedding_key: str) -> list[dict]:
        if not self.client.has_collection(self.collection_name):
            return []

        hits = self.client.search(
            self.collection_name,
            data=[vector],
            limit=limit,
            filter=self._embedding_filter(embedding_key),
            output_fields=[
                self._PK_FIELD,
                self._EMBEDDING_KEY_FIELD,
                self._EMBEDDING_PROVIDER_FIELD,
                self._EMBEDDING_MODEL_FIELD,
                self._EMBEDDING_VERSION_FIELD,
            ],
            search_params={"metric_type": "COSINE"},
        )
        if not hits:
            return []

        results: list[dict[str, Any]] = []
        for hit in hits[0]:
            entity = hit.get("entity", {})
            results.append(
                {
                    "content_hash": entity.get(self._PK_FIELD, hit.get("id")),
                    "score": hit.get("distance", hit.get("score")),
                    "embedding_key": entity.get(self._EMBEDDING_KEY_FIELD, embedding_key),
                    "embedding_provider": entity.get(self._EMBEDDING_PROVIDER_FIELD),
                    "embedding_model": entity.get(self._EMBEDDING_MODEL_FIELD),
                    "embedding_version": entity.get(self._EMBEDDING_VERSION_FIELD),
                }
            )
        return results

    def count(self, embedding_key: str) -> int:
        if not self.client.has_collection(self.collection_name):
            return 0

        query = self.client.query_iterator(
            self.collection_name,
            batch_size=1_000,
            filter=self._embedding_filter(embedding_key),
            output_fields=[self._PK_FIELD],
        )
        count = 0
        try:
            while True:
                page = query.next()
                if not page:
                    break
                count += len(page)
        finally:
            query.close()
        return count

    def _embedding_filter(self, embedding_key: str, content_hash: str | None = None) -> str:
        escaped_embedding_key = self._escape_filter_value(embedding_key)
        expression = f'{self._EMBEDDING_KEY_FIELD} == "{escaped_embedding_key}"'
        if content_hash is None:
            return expression
        escaped_content_hash = self._escape_filter_value(content_hash)
        return f'{expression} and {self._PK_FIELD} == "{escaped_content_hash}"'

    def _parse_embedding_key(self, embedding_key: str) -> tuple[str, str, str]:
        provider, model, version = embedding_key.split(":", 2)
        if not provider or not model or not version:
            raise ValueError(
                "embedding_key must use provider:model:version format, "
                f"got {embedding_key!r}"
            )
        return provider, model, version

    def _escape_filter_value(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
