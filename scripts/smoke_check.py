"""Lightweight integration check for module imports."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    # Import modules that represent the application's critical path.
    try:
        import core.audio_engine  # noqa: F401
        import models.playlist_model  # noqa: F401
        import ui.main_window  # noqa: F401
        import ui.widgets.spectrum_widget  # noqa: F401
        import ui.widgets.spin_sprite_widget  # noqa: F401
        import utils.spectrum_analyzer  # noqa: F401
        import utils.storage  # noqa: F401
    except ModuleNotFoundError as exc:
        print(f"SMOKE_CHECK_SKIPPED: missing dependency -> {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
