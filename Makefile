.PHONY: dev dev-backend dev-frontend

dev-backend:
	.venv/bin/python -m image_vector_search

dev-frontend:
	cd src/image_vector_search/frontend && npm run dev -- --host 0.0.0.0

dev:
	@set -eu; \
	$(MAKE) dev-backend & backend_pid=$$!; \
	$(MAKE) dev-frontend & frontend_pid=$$!; \
	cleanup() { \
		kill $$backend_pid $$frontend_pid 2>/dev/null || true; \
		wait $$backend_pid $$frontend_pid 2>/dev/null || true; \
	}; \
	trap 'cleanup; exit 130' INT TERM; \
	trap cleanup EXIT; \
	while kill -0 $$backend_pid 2>/dev/null && kill -0 $$frontend_pid 2>/dev/null; do \
		sleep 1; \
	done; \
	exit 1
