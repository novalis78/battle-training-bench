"""battle_training — a minimal Python client for the battle.training API.

Standard library only. Public reads need no key; account and bot writes
use the account key from ``api_key=...`` or the ``BATTLE_TRAINING_KEY``
environment variable.
"""

from .client import Client, DEFAULT_BASE_URL
from .errors import ApiError, AuthenticationError, NotFoundError, ValidationError

__all__ = [
    "Client",
    "DEFAULT_BASE_URL",
    "ApiError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
]

__version__ = "0.1.0"
