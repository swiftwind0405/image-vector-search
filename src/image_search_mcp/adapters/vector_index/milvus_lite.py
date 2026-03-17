from pathlib import Path
from threading import Lock
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
    _SERVER_REFCOUNTS: dict[str, int] = {}
    _SERVER_REFCOUNTS_LOCK = Lock()

    def __init__(self, db_path: Path, collection_name: str) -> None:
        self.db_path = db_path.absolute().resolve()
        self.collection_name = collection_name
        self.client = None
        self._closed = False
        uri = server_manager_instance.start_and_get_uri(str(self.db_path))
        if uri is None:
            raise RuntimeError(f"Failed to start Milvus Lite for {self.db_path}")
        # MilvusClient's local .db shortcut does not forward the unix socket address
        # into the gRPC handler correctly. Reusing the resolved UDS fixes local access.
        try:
            self.client = MilvusClient(uri=uri, address=uri)
        except Exception:
            self._closed = True
            server_manager_instance.release_server(str(self.db_path))
            raise
        self._register_server_reference()

    def close(self) -> None:
        if self._closed:
            return

        client = self.client
        try:
            client.close()
        finally:
            self.client = None
            self._closed = True
            if self._release_server_reference():
                server_manager_instance.release_server(str(self.db_path))

    def ensure_collection(self, dimension: int, embedding_key: str) -> None:
        self._parse_embedding_key(embedding_key)
        client = self._client()
        if client.has_collection(self.collection_name):
            self._validate_existing_collection(dimension)
            return

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
        client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )

    def upsert_embeddings(self, records: list[dict]) -> None:
        if not records:
            return
        client = self._client()
        if not client.has_collection(self.collection_name):
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

        client.upsert(self.collection_name, payload)

    def has_embedding(self, content_hash: str, embedding_key: str) -> bool:
        client = self._client()
        if not client.has_collection(self.collection_name):
            return False

        query = client.query_iterator(
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

    def search(
        self,
        vector: list[float],
        limit: int,
        embedding_key: str,
        content_hash_filter: set[str] | None = None,
    ) -> list[dict]:
        client = self._client()
        if not client.has_collection(self.collection_name):
            return []

        filter_expr = self._embedding_filter(embedding_key)
        if content_hash_filter is not None:
            escaped = [self._escape_filter_value(h) for h in content_hash_filter]
            in_list = ", ".join(f'"{v}"' for v in escaped)
            filter_expr += f" and {self._PK_FIELD} in [{in_list}]"

        hits = client.search(
            self.collection_name,
            data=[vector],
            limit=limit,
            filter=filter_expr,
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
        client = self._client()
        if not client.has_collection(self.collection_name):
            return 0

        query = client.query_iterator(
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

    def _client(self) -> MilvusClient:
        if self._closed or self.client is None:
            raise RuntimeError("Milvus client is closed")
        return self.client

    def _validate_existing_collection(self, dimension: int) -> None:
        description = self._client().describe_collection(self.collection_name)
        if description.get("auto_id"):
            raise ValueError("Existing Milvus collection must use explicit content_hash primary keys")
        if description.get("enable_dynamic_field"):
            raise ValueError("Existing Milvus collection must disable dynamic fields")

        fields_by_name = {
            field["name"]: field for field in description.get("fields", []) if "name" in field
        }
        required_fields = {
            self._PK_FIELD,
            self._EMBEDDING_KEY_FIELD,
            self._EMBEDDING_PROVIDER_FIELD,
            self._EMBEDDING_MODEL_FIELD,
            self._EMBEDDING_VERSION_FIELD,
            self._VECTOR_FIELD,
        }
        missing_fields = required_fields - fields_by_name.keys()
        if missing_fields:
            missing_list = ", ".join(sorted(missing_fields))
            raise ValueError(f"Existing Milvus collection is missing required fields: {missing_list}")

        primary_field = fields_by_name[self._PK_FIELD]
        if primary_field.get("type") != DataType.VARCHAR or not primary_field.get("is_primary"):
            raise ValueError("Existing Milvus collection must use a VARCHAR content_hash primary key")

        vector_field = fields_by_name[self._VECTOR_FIELD]
        existing_dimension = vector_field.get("params", {}).get("dim")
        if vector_field.get("type") != DataType.FLOAT_VECTOR:
            raise ValueError("Existing Milvus collection embedding field must be a FLOAT_VECTOR")
        if existing_dimension != dimension:
            raise ValueError(
                "Existing Milvus collection dimension "
                f"{existing_dimension} does not match requested dimension {dimension}"
            )

        for field_name in (
            self._EMBEDDING_KEY_FIELD,
            self._EMBEDDING_PROVIDER_FIELD,
            self._EMBEDDING_MODEL_FIELD,
            self._EMBEDDING_VERSION_FIELD,
        ):
            if fields_by_name[field_name].get("type") != DataType.VARCHAR:
                raise ValueError(
                    f"Existing Milvus collection field {field_name!r} must be VARCHAR"
                )

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

    def _register_server_reference(self) -> None:
        with self._SERVER_REFCOUNTS_LOCK:
            key = str(self.db_path)
            self._SERVER_REFCOUNTS[key] = self._SERVER_REFCOUNTS.get(key, 0) + 1

    def _release_server_reference(self) -> bool:
        with self._SERVER_REFCOUNTS_LOCK:
            key = str(self.db_path)
            remaining = self._SERVER_REFCOUNTS.get(key, 0) - 1
            if remaining > 0:
                self._SERVER_REFCOUNTS[key] = remaining
                return False
            self._SERVER_REFCOUNTS.pop(key, None)
            return True

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
