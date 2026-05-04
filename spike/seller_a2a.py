# (Historical -- written under the project's previous name "neuro-spati", now called "chaos".)
# =====================================================================
# SUPERSEDED — historical A2A spike, kept for reference only.
# The project chose MCP after the MCP spike passed. See
# spike/MCP_SPIKE_REPORT.md for the verdict and spike/seller_mcp.py /
# spike/buyer_mcp.py for the live wire.
# Do NOT copy this code into seller/ or buyer/ — the production scaffold
# is built on FastMCP, not on ACP/A2A.
# =====================================================================
"""
seller_a2a.py — A2A seller spike. Starlette app on localhost:7421
exposing an A2A JSON-RPC endpoint. AgentExecutor responds to any
prompt with text + binary PNG + binary report (all as A2A `Part`s).

Run directly:
    python3 seller_a2a.py            # binds to 127.0.0.1:7421

Or have buyer_a2a.py spawn this as a subprocess.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import sys
import time

import uvicorn
from starlette.applications import Starlette

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_jsonrpc_routes, create_agent_card_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    AgentInterface,
    Artifact,
    Message,
    Part,
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
import uuid
def new_artifact_id() -> str:
    return str(uuid.uuid4())


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[seller] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = int(os.environ.get("A2A_PORT", "7421"))

# Same test bytes the buyer expects — SHA-256 must match.
TEST_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c63f8cfc0000000020001e22165"
    "850000000049454e44ae426082"
)
TEST_REPORT_BYTES = (
    b"INSPECTION REPORT (test)\n"
    b"Item: 2018 Mazda 6 hatchback\n"
    b"VIN ending: 8K2J\n"
    b"Mileage at inspection: 65,432 km\n"
    b"Tires: Continental PremiumContact, ~5000 km wear\n"
    b"Body: no rust, no panel repaint indicators\n"
    b"Mechanical: clean, no codes\n"
    b"Verdict: pass\n"
)


class SellerExecutor(AgentExecutor):
    """A2A AgentExecutor that streams PNG + report on every prompt."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or context.message.task_id
        ctx_id = context.context_id

        log.info("execute task=%s ctx=%s", task_id, ctx_id)

        # 1. Emit the initial Task object (the SDK requires this before
        # any TaskStatusUpdateEvent / TaskArtifactUpdateEvent).
        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=ctx_id,
                status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
            )
        )

        # 2. Build the artifact: 1 text Part + 1 image Part + 1 report Part
        text_part = Part(text="Photo + inspection report for the 2018 Mazda 6.")
        image_part = Part(
            raw=TEST_PNG_BYTES,
            filename="exterior_front.png",
            media_type="image/png",
        )
        report_part = Part(
            raw=TEST_REPORT_BYTES,
            filename="inspection-report.txt",
            media_type="text/plain",
        )
        artifact = Artifact(
            artifact_id=new_artifact_id(),
            name="seller-response",
            description="Photos and inspection report.",
            parts=[text_part, image_part, report_part],
        )
        log.info(
            "emit artifact image_sha=%s… report_sha=%s…",
            hashlib.sha256(TEST_PNG_BYTES).hexdigest()[:12],
            hashlib.sha256(TEST_REPORT_BYTES).hexdigest()[:12],
        )

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=ctx_id,
                artifact=artifact,
                last_chunk=True,
            )
        )

        # 3. Mark completed
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=ctx_id,
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        log.info("cancel called — no-op for spike")


def build_agent_card() -> AgentCard:
    return AgentCard(
        name="neuro-spati-spike-seller",
        description="A2A spike: streams a PNG + inspection report on any prompt.",
        version="0.0.1",
        supported_interfaces=[
            AgentInterface(protocol_binding="JSONRPC", url=f"http://{HOST}:{PORT}/")
        ],
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain", "image/png"],
        skills=[
            AgentSkill(
                id="send_photos",
                name="Send photos",
                description="Returns photos and inspection report as A2A Parts.",
                tags=["cars", "marketplace", "spike"],
            )
        ],
    )


def build_app() -> Starlette:
    card = build_agent_card()
    handler = DefaultRequestHandler(
        agent_card=card,
        agent_executor=SellerExecutor(),
        task_store=InMemoryTaskStore(),
    )
    routes = []
    routes += create_agent_card_routes(card)
    routes += create_jsonrpc_routes(handler, rpc_url="/")
    return Starlette(routes=routes)


def main() -> None:
    log.info("Starting A2A seller on http://%s:%d/", HOST, PORT)
    uvicorn.run(build_app(), host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
