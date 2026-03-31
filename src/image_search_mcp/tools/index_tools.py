from typing import Literal

from image_search_mcp.tools._helpers import maybe_await
from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import registry


@registry.tool(
    name="get_index_status",
    description="Get current index statistics and recent job history",
)
async def get_index_status(ctx: ToolContext) -> dict:
    status = await maybe_await(ctx.status_service.get_index_status())
    jobs = await maybe_await(ctx.status_service.list_recent_jobs(limit=5))
    return {
        "status": status.model_dump(),
        "recent_jobs": [job.model_dump() for job in jobs],
    }


@registry.tool(
    name="trigger_index",
    description="Trigger an indexing job (incremental or full_rebuild)",
)
async def trigger_index(
    ctx: ToolContext,
    mode: Literal["incremental", "full_rebuild"],
) -> dict:
    job = await maybe_await(ctx.job_runner.enqueue(mode))
    payload = job.model_dump() if hasattr(job, "model_dump") else dict(job)
    if "mode" not in payload and "job_type" in payload:
        payload["mode"] = payload["job_type"]
    return {"job": payload}
