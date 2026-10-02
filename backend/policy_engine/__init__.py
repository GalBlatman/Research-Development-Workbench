"""Pure v4 calculation API. No network, model, storage or database access."""

from .engine import evaluate

__all__ = ["evaluate"]
