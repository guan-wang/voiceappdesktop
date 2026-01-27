"""Audio configuration constants"""

import pyaudio

# Audio configuration
CHUNK = 1024  # Frames per buffer
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 1  # Mono
RATE = 24000  # OpenAI Realtime API uses 24kHz
BYTES_PER_SAMPLE = 2  # 16-bit = 2 bytes per sample
