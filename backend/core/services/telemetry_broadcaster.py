"""
Real-Time Telemetry Broadcaster for Server-Sent Events (SSE)

Provides a lightweight, fail-safe, in-memory Pub/Sub event bus per blueprint.
Supports:
- Per-blueprint subscriber channel isolation.
- 50-event ring buffer for late-connecting subscribers.
- Thread-safe synchronous and asynchronous event publishing.
- Periodic heartbeat pings to keep connections alive through reverse proxies.
- Zero-impact disconnect handling (client disconnects never impact generation workers).
"""

import asyncio
import collections
import datetime
import json
import logging
import threading
from typing import Any, AsyncGenerator, Dict, Optional, Set

logger = logging.getLogger(__name__)

BUFFER_MAX_LEN = 50
HEARTBEAT_INTERVAL_SECONDS = 15.0


class TelemetryBroadcaster:
    """
    Singleton in-memory telemetry broadcaster for generation progress events.
    """
    _instance: Optional["TelemetryBroadcaster"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "TelemetryBroadcaster":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelemetryBroadcaster, cls).__new__(cls)
                cls._instance._subscribers: Dict[str, Set[asyncio.Queue]] = collections.defaultdict(set)
                cls._instance._event_buffers: Dict[str, collections.deque] = collections.defaultdict(
                    lambda: collections.deque(maxlen=BUFFER_MAX_LEN)
                )
                cls._instance._sub_lock = threading.Lock()
            return cls._instance

    def broadcast(
        self,
        blueprint_id: str,
        event_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Thread-safe event broadcast to all active subscribers for a blueprint_id.
        Stores the event in the blueprint's replay ring buffer.
        """
        if not blueprint_id:
            return {}

        payload = {
            "event": event_type,
            "blueprint_id": blueprint_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **(data or {})
        }

        with self._sub_lock:
            # 1. Append to ring buffer
            self._event_buffers[blueprint_id].append(payload)

            # 2. Distribute to all registered queues
            queues = list(self._subscribers.get(blueprint_id, set()))

        for q in queues:
            try:
                # Use put_nowait so slow consumers don't block the publisher
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning(f"[Broadcaster] Queue full for subscriber on blueprint {blueprint_id}, dropping event.")
            except Exception as e:
                logger.debug(f"[Broadcaster] Failed to dispatch event to queue: {e}")

        return payload

    async def stream_events(
        self,
        blueprint_id: str,
        include_buffer: bool = True,
        heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS
    ) -> AsyncGenerator[str, None]:
        """
        Async generator yielding SSE-formatted data for a blueprint.
        Replays buffered events first, then streams live events with periodic heartbeats.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        with self._sub_lock:
            if include_buffer and blueprint_id in self._event_buffers:
                # Pre-populate queue with buffered historical events
                for buffered_event in list(self._event_buffers[blueprint_id]):
                    queue.put_nowait(buffered_event)
            self._subscribers[blueprint_id].add(queue)

        try:
            # Initial connection confirmation
            init_event = {
                "event": "STREAM_CONNECTED",
                "blueprint_id": blueprint_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "message": f"Connected to live telemetry stream for {blueprint_id}"
            }
            yield f"data: {json.dumps(init_event)}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                    yield f"data: {json.dumps(event)}\n\n"

                    # If this is a terminal event, stream can gracefully finish after yielding
                    if event.get("event") in ["ASSEMBLY_COMPLETE", "GENERATION_FAILED", "JOB_FAILED"]:
                        # Yield one final sync tick before terminating
                        break

                except asyncio.TimeoutError:
                    # Send periodic keep-alive heartbeat comment
                    yield f": heartbeat {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n\n"

        except asyncio.CancelledError:
            # Client disconnected gracefully
            logger.info(f"[Broadcaster] Client disconnected from stream for blueprint {blueprint_id}")
        except Exception as err:
            logger.warning(f"[Broadcaster] Stream encountered error for blueprint {blueprint_id}: {err}")
        finally:
            with self._sub_lock:
                if blueprint_id in self._subscribers:
                    self._subscribers[blueprint_id].discard(queue)
                    if not self._subscribers[blueprint_id]:
                        del self._subscribers[blueprint_id]


# Global singleton instance
broadcaster = TelemetryBroadcaster()


def broadcast_event(blueprint_id: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper function to broadcast telemetry events globally."""
    return broadcaster.broadcast(blueprint_id=blueprint_id, event_type=event_type, data=data)
