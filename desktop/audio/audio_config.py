"""Audio configuration constants"""

import pyaudio

# Audio configuration
CHUNK = 2048  # Frames per buffer (increased from 1024 for smoother playback)
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 1  # Mono
RATE = 24000  # OpenAI Realtime API uses 24kHz
BYTES_PER_SAMPLE = 2  # 16-bit = 2 bytes per sample
MIN_BUFFER_SIZE = CHUNK * BYTES_PER_SAMPLE * 2  # Minimum buffer to prevent underruns
