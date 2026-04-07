# Gemini Embedding 2 Preview Support Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add optional support for Google `gemini-embedding-2-preview` as an embedding provider for text-to-image search and image-to-image search, without regressing the existing Jina-based workflow.

**Architecture:** Keep the existing `EmbeddingClient` abstraction, introduce a provider factory in runtime wiring, and add a dedicated Gemini adapter that can embed both text and images into a shared vector space. Treat provider changes as an indexing migration concern: each provider/model/version combination should be considered a distinct embedding space and should rebuild vectors into a clean Milvus collection or index root when dimensions differ.

**Tech Stack:** Python 3.12, FastAPI, Pydantic Settings, httpx, Milvus Lite / pymilvus, pytest, respx

---

## Scope Decisions

### In scope
- Add a Gemini embedding adapter that supports both `embed_texts()` and `embed_images()`.
- Make embedding provider selection runtime-configurable.
- Preserve existing search/index service interfaces.
- Document and enforce an index migration strategy for provider/model swaps.
- Add focused unit and integration coverage for Gemini wiring.

### Out of scope
- Running multiple vector dimensions in the same Milvus collection.
- Building a UI workflow for switching providers from the admin console.
- Supporting every Google auth mode on day one; API-key-based access is sufficient for the first implementation.
- Migrating existing Jina vectors in place.

### Key constraints to preserve
- Text search and image similarity search must continue to use one shared embedding space per configured provider/model/version.
- Existing Jina deployments must remain the default behavior.
- Provider-specific HTTP payloads must stay inside adapter classes rather than leaking into services.

---

## Implementation Overview

### Current-state observations
- `EmbeddingClient` already defines the right abstraction surface: `embed_texts()`, `embed_images()`, and `vector_dimension()`. This is a strong foundation for a second provider.
- Runtime wiring is still Jina-specific today: `build_runtime_services()` always constructs `JinaEmbeddingClient`, and settings only expose `jina_api_key`.
- Search and indexing both require image embeddings, so Gemini support is only viable if we use a model that supports multimodal embeddings in a shared space.
- Milvus collection dimensions are fixed. A provider/model switch that changes vector dimension must use a new collection or a fresh index root.

### Recommended rollout shape
1. Add config knobs for Gemini credentials and provider selection.
2. Introduce a `GeminiEmbeddingClient` implementing `EmbeddingClient`.
3. Replace direct `JinaEmbeddingClient` construction with a provider factory.
4. Add tests for provider-specific payloads and runtime selection.
5. Document reindex/rebuild expectations when switching models.

---

### Task 1: Extend settings for provider-specific configuration

**Files:**
- Modify: `src/image_vector_search/config.py`
- Modify: `tests/unit/test_config.py`

**Step 1: Write the failing test**

Add tests covering:
- `embedding_provider="jina"` remains the default.
- Gemini-specific settings load from environment, e.g. API key and optional output dimensionality.
- Unsupported provider values are rejected or normalized through a helper.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL because Gemini-specific settings and provider validation do not exist yet.

**Step 3: Write minimal implementation**

Extend `Settings` with fields such as:
- `google_api_key: str = ""`
- `gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"`
- `embedding_output_dimensionality: int | None = None`

Optionally add a validation/helper method so provider-specific requirements are explicit rather than implied.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/config.py tests/unit/test_config.py
git commit -m "feat: add gemini embedding settings"
```

---

### Task 2: Implement a Gemini embedding adapter

**Files:**
- Create: `src/image_vector_search/adapters/embedding/gemini.py`
- Modify: `src/image_vector_search/adapters/embedding/__init__.py` (if package exports are introduced)
- Create: `tests/unit/test_gemini_embedding_client.py`

**Step 1: Write the failing test**

Add unit tests that verify:
- `embed_texts()` sends the expected Gemini embeddings request shape.
- `embed_images()` base64-encodes image bytes into the expected request parts.
- response parsing returns one vector per input item.
- retry behavior for transient HTTP failures mirrors the Jina client.
- `vector_dimension()` returns configured dimensionality when provided, otherwise `None`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_gemini_embedding_client.py -v`
Expected: FAIL because the module does not exist.

**Step 3: Write minimal implementation**

Implement `GeminiEmbeddingClient` with the same public shape as `JinaEmbeddingClient`:
- accept `api_key`, `model`, optional `output_dimensionality`, optional `base_url`
- support both text and image inputs
- keep retryable HTTP handling inside the adapter
- expose provider/model/version accessors if those remain useful operationally

Prefer keeping protocol conversion fully encapsulated so services still pass only strings or `Path` objects.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_gemini_embedding_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/adapters/embedding/gemini.py tests/unit/test_gemini_embedding_client.py
git commit -m "feat: add gemini embedding adapter"
```

---

### Task 3: Replace runtime hard-coding with a provider factory

**Files:**
- Modify: `src/image_vector_search/runtime.py`
- Possibly Modify: `src/image_vector_search/adapters/embedding/base.py`
- Create or Modify: `tests/integration/test_app_bootstrap.py`

**Step 1: Write the failing test**

Add bootstrap tests covering:
- Jina remains the default provider.
- `embedding_provider="gemini"` constructs the Gemini adapter.
- Missing provider credentials fail early with a clear error.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_app_bootstrap.py -v`
Expected: FAIL because runtime wiring always constructs `JinaEmbeddingClient`.

**Step 3: Write minimal implementation**

Refactor runtime wiring to:
- type `RuntimeServices.embedding_client` as `EmbeddingClient`
- delegate adapter construction to a helper such as `_build_embedding_client(settings)`
- enforce provider-specific credential checks in one place

Keep service construction unchanged so indexing/search layers remain provider-agnostic.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_app_bootstrap.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/runtime.py src/image_vector_search/adapters/embedding/base.py tests/integration/test_app_bootstrap.py
git commit -m "refactor: select embedding client by provider"
```

---

### Task 4: Define and enforce vector migration expectations

**Files:**
- Modify: `src/image_vector_search/services/indexing.py`
- Modify: `src/image_vector_search/services/status.py`
- Modify: `docs/usage.md`
- Create or Modify: `tests/integration/test_indexing_service.py`

**Step 1: Write the failing test**

Add coverage for one or more of the following behaviors:
- a dimension mismatch against an existing Milvus collection produces a clear operational error
- status output clearly reports the active provider/model/version
- rebuilding under a new provider/model/version writes vectors under the new embedding key after a clean index reset

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_indexing_service.py -v`
Expected: FAIL because migration/documentation behavior is not explicit enough yet.

**Step 3: Write minimal implementation**

Do not try to support in-place cross-dimension coexistence. Instead:
- make errors clearer when collection dimensions do not match
- document that switching provider/model/version should use a new collection or a cleared index root
- ensure status output helps operators confirm which embedding space is active

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_indexing_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/services/indexing.py src/image_vector_search/services/status.py docs/usage.md tests/integration/test_indexing_service.py
git commit -m "docs: clarify embedding migration workflow"
```

---

### Task 5: Add regression coverage for search flows under a non-Jina provider

**Files:**
- Modify: `tests/unit/test_search_service.py`
- Modify: `tests/integration/conftest.py`
- Create or Modify: `tests/integration/test_end_to_end_search.py`

**Step 1: Write the failing test**

Add focused coverage showing that the search/index services remain provider-agnostic by using a fake Gemini-like embedding client or test double.

Suggested checks:
- text search still calls `embed_texts()` and filters by embedding key
- image similarity search still calls `embed_images()` and excludes the query image
- indexing reuses existing images but inserts missing embeddings for the active embedding key

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_search_service.py tests/integration/test_end_to_end_search.py -v`
Expected: FAIL if any test assumptions are still Jina-specific.

**Step 3: Write minimal implementation**

Remove Jina-specific assumptions from service-level tests while preserving the current behavior. Keep protocol-specific assertions in adapter tests only.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_search_service.py tests/integration/test_end_to_end_search.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_search_service.py tests/integration/conftest.py tests/integration/test_end_to_end_search.py
git commit -m "test: verify provider-agnostic search flows"
```

---

### Task 6: Run focused verification

**Files:**
- No code changes required unless failures are found

**Step 1: Run unit tests for adapters and config**

Run: `pytest tests/unit/test_config.py tests/unit/test_jina_embedding_client.py tests/unit/test_gemini_embedding_client.py -v`
Expected: PASS

**Step 2: Run integration tests for bootstrap and indexing/search paths**

Run: `pytest tests/integration/test_app_bootstrap.py tests/integration/test_indexing_service.py tests/integration/test_end_to_end_search.py -v`
Expected: PASS

**Step 3: Run the full test suite**

Run: `pytest`
Expected: PASS

**Step 4: Commit final adjustments if needed**

```bash
git add <any changed files>
git commit -m "test: verify gemini embedding support"
```

---

## Operational Notes

### Recommended first release policy
- Keep Jina as the default provider.
- Enable Gemini only through explicit environment configuration.
- Treat provider/model/version changes as a reindex event.

### Recommended environment variables
- `IMAGE_SEARCH_EMBEDDING_PROVIDER=jina|gemini`
- `IMAGE_SEARCH_EMBEDDING_MODEL=jina-clip-v2|gemini-embedding-2-preview`
- `IMAGE_SEARCH_EMBEDDING_VERSION=<provider-specific version label>`
- `IMAGE_SEARCH_JINA_API_KEY=...`
- `IMAGE_SEARCH_GOOGLE_API_KEY=...`
- `IMAGE_SEARCH_EMBEDDING_OUTPUT_DIMENSIONALITY=3072` (optional)

### Open questions before implementation
- Should the first Gemini release support only API-key auth, or also Vertex AI credentials?
- Do we want to expose output dimensionality as an operator setting, or hard-code a safe default such as 3072?
- Should provider/model changes automatically fail fast if an old Milvus database is present, or merely surface a clearer error with remediation steps?
