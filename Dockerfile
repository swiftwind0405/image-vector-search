FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install .

EXPOSE 8000

CMD ["uvicorn", "image_search_mcp.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
