"""Authoritative media selections for the active conversation branch."""

from __future__ import annotations

import copy
import threading
from collections.abc import Iterable
from typing import Any

from sdk.messages import PresentationMessage


class PresentationSelectionState:
    """Keep resolved media separate from the LLM's source dialog.

    Entries use the persisted LLM message count as their history boundary.  This
    lets reroll, revert, and branch fork trim presentation choices without
    rewriting the model output that produced them.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: list[dict[str, Any]] = []

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._entries)

    def restore(self, entries: object) -> None:
        normalized: list[dict[str, Any]] = []
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                try:
                    message_count = max(0, int(entry.get("messageCount") or 0))
                except (TypeError, ValueError):
                    continue
                kind = str(entry.get("kind") or "").strip()
                name = str(entry.get("name") or "").strip()
                asset_id = entry.get("assetId")
                if not kind or asset_id is None:
                    continue
                normalized.append(
                    {
                        "assetId": str(asset_id),
                        "catalogKey": str(entry.get("catalogKey") or ""),
                        "kind": kind,
                        "messageCount": message_count,
                        "name": name,
                        "path": str(entry.get("path") or ""),
                        "turnId": entry.get("turnId"),
                    }
                )
        with self._lock:
            self._entries = normalized

    def record(
        self,
        *,
        kind: str,
        name: str,
        asset_id: str,
        message_count: int,
        turn_id: int | None = None,
        path: str = "",
        catalog_key: str = "",
    ) -> None:
        entry = {
            "assetId": str(asset_id),
            "catalogKey": str(catalog_key or ""),
            "kind": str(kind),
            "messageCount": max(0, int(message_count)),
            "name": str(name),
            "path": str(path or ""),
            "turnId": turn_id,
        }
        with self._lock:
            self._entries.append(entry)

    def clear(self) -> None:
        self.restore([])

    def prune(self, message_count: int) -> None:
        boundary = max(0, int(message_count))
        with self._lock:
            self._entries = [
                entry
                for entry in self._entries
                if int(entry.get("messageCount") or 0) <= boundary
            ]

    def latest(
        self,
        kind: str,
        *,
        name: str | None = None,
        catalog_key: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            for entry in reversed(self._entries):
                if entry.get("kind") != kind:
                    continue
                if name is not None and entry.get("name") != name:
                    continue
                if catalog_key is not None and entry.get("catalogKey") != catalog_key:
                    continue
                return copy.deepcopy(entry)
        return None


def catalog_key(candidates: Iterable[Any]) -> str:
    """Return a stable key that invalidates remembered ids after config edits."""

    return "\x1f".join(
        f"{getattr(item, 'asset_id', '')}\x1e{getattr(item, 'path', '')}\x1e{getattr(item, 'tags', '')}"
        for item in candidates
    )


def replay_presentation_selections(
    state: PresentationSelectionState,
    presentation_queue: Any,
    *,
    include_sprite: bool = True,
) -> bool:
    """Replay the latest branch-owned scene, BGM, and character sprite."""

    restored_sprite = False
    entries = state.snapshot()
    latest_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        latest_by_key[(str(entry.get("kind")), str(entry.get("name")))] = entry

    for kind in ("scene", "bgm"):
        matches = [
            entry
            for (entry_kind, _), entry in latest_by_key.items()
            if entry_kind == kind
        ]
        if not matches:
            continue
        entry = max(matches, key=lambda item: int(item.get("messageCount") or 0))
        presentation_queue.put(
            PresentationMessage(
                audio_path=str(entry.get("path") or ""),
                name="SCENE" if kind == "scene" else "bgm",
                text="",
                asset_id=str(entry.get("assetId")),
                is_system_message=True,
                timeout=0,
            )
        )

    sprite_entries = [
        entry for (kind, _), entry in latest_by_key.items() if kind == "sprite"
    ]
    if sprite_entries and include_sprite:
        entry = max(sprite_entries, key=lambda item: int(item.get("messageCount") or 0))
        presentation_queue.put(
            PresentationMessage(
                audio_path="",
                name=str(entry.get("name") or ""),
                text="",
                asset_id=str(entry.get("assetId")),
                is_system_message=False,
                timeout=0,
            )
        )
        restored_sprite = True
    return restored_sprite


__all__ = [
    "PresentationSelectionState",
    "catalog_key",
    "replay_presentation_selections",
]
