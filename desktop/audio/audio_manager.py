"""
AudioManager - Handles all audio I/O operations
Manages PyAudio streams, queues, and buffers
"""

import pyaudio
import queue
from .audio_config import CHUNK, FORMAT, CHANNELS, RATE, BYTES_PER_SAMPLE


class AudioManager:
    """Manages audio input/output streams and buffers"""
    
    def __init__(self):
        """Initialize audio manager with streams and buffers"""
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.audio_queue = queue.Queue()
        self.audio_buffer = bytearray()  # Buffer for incomplete audio chunks
        
    def setup_streams(self):
        """Setup audio input and output streams"""
        try:
            # Input stream (microphone) - no callback, we'll read directly
            self.input_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            # Output stream (speakers) - with callback for playback
            self.output_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK,
                stream_callback=self._output_callback
            )
            
            print("✅ Audio streams initialized")
            
        except Exception as e:
            print(f"❌ Error setting up audio: {e}")
            raise
    
    def _output_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio output - plays audio from API"""
        # Calculate how many bytes we need (frame_count * bytes_per_sample * channels)
        bytes_needed = frame_count * BYTES_PER_SAMPLE * CHANNELS
        
        # First, try to get data from buffer
        if len(self.audio_buffer) >= bytes_needed:
            data = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
            return (data, pyaudio.paContinue)
        
        # If buffer doesn't have enough, try to get from queue
        try:
            while len(self.audio_buffer) < bytes_needed:
                chunk = self.audio_queue.get_nowait()
                self.audio_buffer.extend(chunk)
            
            data = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
            return (data, pyaudio.paContinue)
            
        except queue.Empty:
            # Not enough data available - return silence
            return (b'\x00' * bytes_needed, pyaudio.paContinue)
    
    def start_streams(self):
        """Start audio input and output streams"""
        if self.input_stream:
            self.input_stream.start_stream()
        if self.output_stream:
            self.output_stream.start_stream()
    
    def stop_streams(self):
        """Stop audio input and output streams"""
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
            except Exception:
                pass
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
            except Exception:
                pass
    
    def read_input_chunk(self):
        """Read a chunk of audio from the microphone"""
        if not self.input_stream:
            return None
        return self.input_stream.read(CHUNK, exception_on_overflow=False)
    
    def queue_output_audio(self, audio_bytes: bytes):
        """Queue audio bytes for playback"""
        self.audio_queue.put(audio_bytes)
    
    def cleanup(self):
        """Clean up audio resources"""
        self.stop_streams()
        
        if self.input_stream:
            try:
                self.input_stream.close()
            except Exception:
                pass
            
        if self.output_stream:
            try:
                self.output_stream.close()
            except Exception:
                pass
            
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
        
        # Clear buffers
        self.audio_buffer.clear()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def is_running(self):
        """Check if streams are active"""
        return (self.input_stream and self.input_stream.is_active() and
                self.output_stream and self.output_stream.is_active())
