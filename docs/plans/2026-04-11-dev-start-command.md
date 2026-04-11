# Dev Start Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a single development command that starts the backend and frontend together without opening a browser.

**Architecture:** Add a root `Makefile` as the top-level developer entrypoint. The `dev` target supervises backend and frontend child processes, while `dev-backend` and `dev-frontend` keep the underlying commands explicit and individually runnable.

**Tech Stack:** GNU Make, Python backend module entrypoint, Vite frontend dev server, pytest

---

### Task 1: Lock the expected developer interface

**Files:**
- Create: `tests/unit/test_makefile.py`
- Test: `tests/unit/test_makefile.py`

**Step 1: Write the failing test**

Add a test that asserts a root `Makefile` exists and contains `dev`, `dev-backend`, and `dev-frontend` targets plus the concrete backend/frontend launch commands.

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_makefile.py -v`
Expected: FAIL because `Makefile` does not exist yet.

**Step 3: Write minimal implementation**

Create `Makefile` with separate backend/frontend targets and a combined `dev` target that starts both processes and cleans them up on exit.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/unit/test_makefile.py -v`
Expected: PASS

### Task 2: Document the new command

**Files:**
- Modify: `README.md`
- Test: `tests/unit/test_readme.py`

**Step 1: Write the failing test**

Extend README coverage so local development docs must mention `make dev`.

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_readme.py -v`
Expected: FAIL because README does not mention the new command yet.

**Step 3: Write minimal implementation**

Document `make dev`, plus the single-surface `make dev-backend` and `make dev-frontend` variants.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/unit/test_readme.py -v`
Expected: PASS
