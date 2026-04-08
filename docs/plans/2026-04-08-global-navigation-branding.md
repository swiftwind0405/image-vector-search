# Global Navigation Branding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add site favicon assets to the frontend HTML entry and show the shared `logo.svg` in the global navigation brand area.

**Architecture:** The Vite app uses a single `index.html` entry for head metadata, so favicon links belong there for global coverage. The persistent sidebar lives in `src/components/Layout.tsx`, making it the correct place to add the shared brand mark without touching per-page content.

**Tech Stack:** Vite, React, React Router, Vitest, Testing Library

---

### Task 1: Brand navigation shell

**Files:**
- Modify: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`
- Modify: `src/image_vector_search/frontend/src/components/Layout.tsx`

**Step 1: Write the failing test**

Add a test expectation that the navigation shell renders the shared logo image alongside the existing brand text.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: FAIL because the logo image is not rendered yet.

**Step 3: Write minimal implementation**

Import `logo.svg` into `Layout.tsx` and render it in the sidebar brand block with accessible alt text.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: PASS

### Task 2: Global favicon links

**Files:**
- Create: `src/image_vector_search/frontend/src/test/index-html.test.ts`
- Modify: `src/image_vector_search/frontend/index.html`

**Step 1: Write the failing test**

Add a small Vitest file that reads `index.html` and asserts links for `/favicon.ico` and `/favicon.png` exist.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/index-html.test.ts`
Expected: FAIL because the favicon link tags are not present.

**Step 3: Write minimal implementation**

Add standard favicon link tags to `index.html`.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/index-html.test.ts`
Expected: PASS
