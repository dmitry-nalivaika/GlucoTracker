"""Entry point for the GlucoTrack sandbox.

Run with:
    python -m sandbox.main            (from project root)
    python sandbox/main.py            (from project root)

Then open http://localhost:8765 in your browser.
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# Suppress noisy SQLAlchemy echo
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _check_imports() -> None:
    """Fail fast with a helpful message if glucotrack is not installed."""
    try:
        import glucotrack  # noqa: F401
    except ImportError:
        print(
            "\nERROR: 'glucotrack' package not found.\n"
            "Install it in development mode from the project root:\n\n"
            "    pip install -e .\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        print(
            "\nERROR: Sandbox dependencies not installed.\n"
            "Install them from the project root:\n\n"
            "    pip install -e '.[sandbox]'\n"
            "  or:\n"
            "    pip install fastapi uvicorn[standard]\n",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    _check_imports()

    import uvicorn

    print("\n" + "=" * 60)
    print("  GlucoTrack Sandbox — Visual Workflow Inspector")
    print("=" * 60)
    print("  Open in browser: http://localhost:8765")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    uvicorn.run(
        "sandbox.app:app",
        host="127.0.0.1",
        port=8765,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
