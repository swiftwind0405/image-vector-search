# Stage 1: Build React frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY src/image_vector_search/frontend/package.json src/image_vector_search/frontend/package-lock.json ./
RUN npm ci
COPY src/image_vector_search/frontend/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_RETRIES=10

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

# Copy built frontend into the Python package
COPY --from=frontend /app/frontend/dist ./src/image_vector_search/frontend/dist

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-build-isolation --prefer-binary .

EXPOSE 8000

CMD ["uvicorn", "image_vector_search.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
