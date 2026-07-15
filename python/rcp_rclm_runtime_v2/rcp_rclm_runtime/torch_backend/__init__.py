"""Optional untrusted PyTorch proposal pilot.

The package initializer intentionally imports no PyTorch-facing module.  This keeps the
checker, promotion, and replay import surfaces model-free and lets independent replay
run after the training backend source has been removed.
"""

from typing import Final

PILOT_ID: Final[str] = "rcp-rclm-pytorch-cpu-one-step-linear-v1"

__all__ = ["PILOT_ID"]
