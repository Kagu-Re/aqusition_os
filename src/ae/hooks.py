from __future__ import annotations

"""Hook / subscription system (v1).

- Code-first subscriptions
- Topic matching supports exact match and prefix match via pattern ending with ".*"
- Safety guards: hook failures are caught and logged to activity_log

v1 dispatch is synchronous and best-effort; it never blocks event persistence.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import OpEvent
from .repo_activity import append_activity
from .repo_hook_retries import enqueue_hook_retry


HookFn = Callable[[str, OpEvent], None]


@dataclass(frozen=True)
class HookSpec:
    name: str
    pattern: str
    fn: HookFn


class HookRegistry:
    def __init__(self) -> None:
        self._hooks: List[HookSpec] = []

    def subscribe(self, *, name: str, pattern: str, fn: HookFn) -> None:
        if not name:
            raise ValueError("Hook name is required")
        if not pattern:
            raise ValueError("Hook pattern is required")
        self._hooks.append(HookSpec(name=name, pattern=pattern, fn=fn))

    def list(self) -> List[HookSpec]:
        return list(self._hooks)

    def get_by_name(self, name: str) -> Optional[HookSpec]:
        for h in self._hooks:
            if h.name == name:
                return h
        return None

    @staticmethod
    def _match(pattern: str, topic: str) -> bool:
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix)
        return pattern == topic

    def dispatch(self, db_path: str, event: OpEvent) -> None:
        for spec in self._hooks:
            if not self._match(spec.pattern, event.topic):
                continue
            try:
                spec.fn(db_path, event)
            except Exception as e:
                # Enqueue retry (best-effort). Never blocks persistence.
                try:
                    enqueue_hook_retry(
                        db_path,
                        event_id=event.event_id,
                        hook_name=spec.name,
                        topic=event.topic,
                        error=f"{type(e).__name__}: {e}",
                    )
                except Exception:
                    pass

                # Best-effort logging, never raise
                try:
                    append_activity(
                        db_path,
                        action="hook_error",
                        entity_type="op_event",
                        entity_id=event.event_id,
                        actor=event.actor,
                        details={
                            "hook": spec.name,
                            "pattern": spec.pattern,
                            "topic": event.topic,
                            "error": f"{type(e).__name__}: {e}",
                        },
                    )
                except Exception:
                    pass


# Global registry used by default
GLOBAL_HOOKS = HookRegistry()


def subscribe_hook(*, name: str, pattern: str, fn: HookFn) -> None:
    """Register a hook into the global hook registry."""
    GLOBAL_HOOKS.subscribe(name=name, pattern=pattern, fn=fn)
