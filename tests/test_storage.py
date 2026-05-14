"""Unit tests for app-state persistence helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from utils import storage


class StorageTest(unittest.TestCase):
    """Validate state load/save roundtrip."""

    def test_state_roundtrip(self) -> None:
        # Isolate test output by monkeypatching state path factory.
        test_path = Path("assets/test_state.json").resolve()
        original_factory = storage._state_path
        storage._state_path = lambda: test_path  # type: ignore[assignment]
        try:
            payload = {"theme": "GameBoy Green", "play_mode": "LIST_LOOP"}
            storage.save_state(payload)
            loaded = storage.load_state()
            self.assertEqual(loaded, payload)
        finally:
            storage._state_path = original_factory  # type: ignore[assignment]
            if test_path.exists():
                test_path.unlink()


if __name__ == "__main__":
    unittest.main()
