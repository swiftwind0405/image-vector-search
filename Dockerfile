# Stage 1: Build React frontend
FROM node:20-alpine AS frontend
WORKDIR /app/web
COPY src/image_search_mcp/web/package.json src/image_search_mcp/web/package-lock.json ./
RUN npm ci
COPY src/image_search_mcp/web/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

# Copy built frontend into the Python package
COPY --from=frontend /app/web/dist ./src/image_search_mcp/web/dist

RUN pip install .

EXPOSE 8000

CMD ["uvicorn", "image_search_mcp.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
