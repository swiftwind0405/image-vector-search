from pathlib import Path


def test_makefile_defines_dev_targets() -> None:
    makefile = Path("Makefile")

    assert makefile.exists()

    text = makefile.read_text(encoding="utf-8")

    assert ".PHONY: dev dev-backend dev-frontend" in text
    assert "dev:" in text
    assert "dev-backend:" in text
    assert "dev-frontend:" in text
    assert ".venv/bin/python -m image_vector_search" in text
    assert "npm run dev -- --host 0.0.0.0" in text
    assert "--open false" not in text
