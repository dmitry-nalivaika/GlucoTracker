"""Synthetic test data for sandbox workflow execution.

All values are realistic but fictional — no real user data.

Image bytes are loaded from sandbox/assets/ (generated PNG files that the real
Claude vision API can analyse).  If the asset files are missing (e.g. in CI
without the pre-generated assets), we fall back to a minimal 1×1 JPEG so the
storage and DB pipeline can still be exercised without real photos.

To (re-)generate the assets run:
    python -m sandbox.generate_test_images
"""

from __future__ import annotations

from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"

# Minimal valid 1×1 JPEG — kept as a fallback for CI / environments without
# the pre-generated PNG assets.  The fake bytes are intentionally small.
_FAKE_JPEG_BYTES: bytes = bytes(
    [
        0xFF,
        0xD8,
        0xFF,
        0xE0,
        0x00,
        0x10,
        0x4A,
        0x46,
        0x49,
        0x46,
        0x00,
        0x01,
        0x01,
        0x00,
        0x00,
        0x01,
        0x00,
        0x01,
        0x00,
        0x00,
        0xFF,
        0xDB,
        0x00,
        0x43,
        0x00,
        0x08,
        0x06,
        0x06,
        0x07,
        0x06,
        0x05,
        0x08,
        0x07,
        0x07,
        0x07,
        0x09,
        0x09,
        0x08,
        0x0A,
        0x0C,
        0x14,
        0x0D,
        0x0C,
        0x0B,
        0x0B,
        0x0C,
        0x19,
        0x12,
        0x13,
        0x0F,
        0x14,
        0x1D,
        0x1A,
        0x1F,
        0x1E,
        0x1D,
        0x1A,
        0x1C,
        0x1C,
        0x20,
        0x24,
        0x2E,
        0x27,
        0x20,
        0x22,
        0x2C,
        0x23,
        0x1C,
        0x1C,
        0x28,
        0x37,
        0x29,
        0x2C,
        0x30,
        0x31,
        0x34,
        0x34,
        0x34,
        0x1F,
        0x27,
        0x39,
        0x3D,
        0x38,
        0x32,
        0x3C,
        0x2E,
        0x33,
        0x34,
        0x32,
        0xFF,
        0xC0,
        0x00,
        0x0B,
        0x08,
        0x00,
        0x01,
        0x00,
        0x01,
        0x01,
        0x01,
        0x11,
        0x00,
        0xFF,
        0xC4,
        0x00,
        0x1F,
        0x00,
        0x00,
        0x01,
        0x05,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0xFF,
        0xDA,
        0x00,
        0x08,
        0x01,
        0x01,
        0x00,
        0x00,
        0x3F,
        0x00,
        0xFB,
        0xD5,
        0xFF,
        0xD9,
    ]
)


def _load_asset(filename: str) -> bytes:
    """Load a pre-generated PNG asset, falling back to the minimal fake JPEG."""
    path = _ASSETS / filename
    if path.exists():
        return path.read_bytes()
    return _FAKE_JPEG_BYTES


FOOD_PHOTO_BYTES: bytes = _load_asset("food_test.png")
CGM_SCREENSHOT_BYTES: bytes = _load_asset("cgm_test.png")

# Synthetic user identifiers
SANDBOX_USER_ID: int = 999_000_001
SANDBOX_CHAT_ID: int = 999_000_001

# Fake Telegram file IDs (unique per entry type)
FOOD_TELEGRAM_FILE_ID: str = "AgACAgIAAxkBAAIBsGVsandbox_food_001"
CGM_TELEGRAM_FILE_ID: str = "AgACAgIAAxkBAAIBsGVsandbox_cgm_001"

# Synthetic session context
ACTIVITY_DESCRIPTION: str = "30 min moderate-pace walk before lunch"
CGM_TIMING_LABEL: str = "1h_post_meal"
