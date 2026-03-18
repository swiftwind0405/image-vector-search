from pathlib import Path


def test_docker_workflow_publishes_to_ghcr_on_tag_push():
    workflow = Path(".github/workflows/docker.yml").read_text(encoding="utf-8")

    assert "tags:" in workflow
    assert "'v[0-9]+.*'" in workflow
    assert "ghcr.io" in workflow
