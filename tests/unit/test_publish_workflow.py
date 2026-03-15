from pathlib import Path


def test_publish_workflow_runs_on_master_push():
    workflow = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert "- master" in workflow
