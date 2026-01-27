"""Audio management module for handling audio I/O operations"""

from .audio_manager import AudioManager
from .audio_config import (
    CHUNK,
    FORMAT,
    CHANNELS,
    RATE,
    BYTES_PER_SAMPLE
)

__all__ = [
    'AudioManager',
    'CHUNK',
    'FORMAT',
    'CHANNELS',
    'RATE',
    'BYTES_PER_SAMPLE'
]
