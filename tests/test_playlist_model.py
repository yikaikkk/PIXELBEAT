"""Unit tests for playlist model behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from models.playlist_model import PlaylistModel
except ModuleNotFoundError as exc:  # pragma: no cover
    PlaylistModel = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class PlaylistModelTest(unittest.TestCase):
    """Verify indexing, navigation, and serialization behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        if IMPORT_ERROR is not None:
            raise unittest.SkipTest(f"Dependency missing for PlaylistModel tests: {IMPORT_ERROR}")

    def test_add_and_navigation(self) -> None:
        model = PlaylistModel()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            a = base / "a.mp3"
            b = base / "b.wav"
            a.write_bytes(b"x")
            b.write_bytes(b"y")

            added = model.add_files([str(a), str(b)])
            self.assertEqual(added, 2)
            self.assertEqual(model.current_track.title, "a")

            nxt = model.next_track()
            self.assertIsNotNone(nxt)
            self.assertEqual(nxt.title, "b")

            prev = model.previous_track()
            self.assertIsNotNone(prev)
            self.assertEqual(prev.title, "a")

    def test_replace_and_serialize(self) -> None:
        model = PlaylistModel()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "song.ogg"
            p.write_bytes(b"x")
            model.replace_files([str(p)])
            paths = model.to_path_list()
            self.assertEqual(paths, [str(p)])


if __name__ == "__main__":
    unittest.main()
