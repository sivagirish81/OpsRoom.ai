import asyncio
import logging
from functools import partial

from backend.graph import run_incident_workflow
from backend.streams import ALERTS, read_group_events

logger = logging.getLogger(__name__)


async def consume_incident_events(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    reader = partial(read_group_events, "opsroom-backend", 1000)
    while not stop.is_set():
        try:
            events = await loop.run_in_executor(None, reader)
            incident_ids = {
                str(event["incident_id"])
                for event in events
                if event["stream"] == ALERTS and event.get("incident_id")
            }
            for incident_id in incident_ids:
                await loop.run_in_executor(None, run_incident_workflow, incident_id, "")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Incident stream worker failed; retrying.")
            await asyncio.sleep(2)

