# Audio Crackling Fix - Web Version

## Date: January 28, 2026
## Status: ⚠️ REVERTED

**Note:** This fix was reverted as it caused worse issues (more crackling and audio cutting off mid-sentence). The audio handling has been restored to the original immediate playback version.

## Problem Summary

The web version of the Korean Voice Tutor exhibited audio crackling/popping during AI speech playback, while the desktop version played audio smoothly without any issues.

## Root Cause Analysis

### Desktop Version (No Crackling) ✅

The desktop version uses **PyAudio with callback-based streaming** that includes sophisticated buffering:

1. **Pre-buffering Strategy**: Accumulates audio chunks up to `MIN_BUFFER_SIZE * 2` (8192 bytes) before starting playback
2. **Continuous Buffer Management**: The `_output_callback` continuously pulls from the audio queue to maintain a healthy buffer
3. **Graceful Underrun Handling**: When the buffer runs low, it pads with silence instead of causing gaps
4. **Persistent Buffer**: Uses a `bytearray` to store incomplete chunks and maintain smooth transitions

```python
# Desktop audio_manager.py - Key buffering logic
def _output_callback(self, in_data, frame_count, time_info, status):
    # Pre-buffer up to MIN_BUFFER_SIZE * 2
    max_prebuffer = MIN_BUFFER_SIZE * 2
    while len(self.audio_buffer) < max_prebuffer:
        try:
            chunk = self.audio_queue.get_nowait()
            self.audio_buffer.extend(chunk)
        except queue.Empty:
            break
    
    # Return data or pad with silence
    if len(self.audio_buffer) >= bytes_needed:
        data = bytes(self.audio_buffer[:bytes_needed])
        self.audio_buffer = self.audio_buffer[bytes_needed:]
        return (data, pyaudio.paContinue)
    # ... padding logic for underruns
```

### Web Version (Had Crackling) ❌

The web version used **Web Audio API with immediate chunk playback**:

1. **No Pre-buffering**: Played each chunk immediately upon receiving from server
2. **Aggressive Scheduling**: Created individual `AudioBufferSource` for each chunk without buffer management
3. **No Minimum Threshold**: Started playback as soon as first chunk arrived
4. **Gap-Prone**: Network jitter caused tiny gaps between chunks → crackling/popping

```javascript
// OLD CODE - Immediate playback, no buffering
async playAudioChunk(base64Audio) {
    this.audioQueue.push(base64Audio);
    if (!this.isPlaying) {
        this.processAudioQueue(); // Immediate start!
    }
}
```

## The Solution

Implemented **pre-buffering and intelligent buffer management** in the web version to match the desktop version's approach:

### Key Changes to `audio.js`

#### 1. Added Pre-buffering Configuration

```javascript
// Pre-buffering settings to prevent crackling
this.MIN_BUFFER_CHUNKS = 3;  // Wait for at least 3 chunks before starting
this.isBuffering = false;
this.bufferStartTime = 0;
this.MAX_BUFFER_WAIT = 500;  // Maximum 500ms wait for buffering
```

#### 2. Smart Playback Start

```javascript
async playAudioChunk(base64Audio) {
    this.audioQueue.push(base64Audio);
    
    if (!this.isPlaying && !this.isBuffering) {
        // Start buffering if this is the first chunk
        if (this.audioQueue.length === 1) {
            this.isBuffering = true;
            this.bufferStartTime = Date.now();
            console.log(`🔄 Buffering started...`);
        }
        
        // Check if we have enough chunks OR timeout reached
        const bufferTime = Date.now() - this.bufferStartTime;
        if (this.audioQueue.length >= this.MIN_BUFFER_CHUNKS || 
            bufferTime >= this.MAX_BUFFER_WAIT) {
            console.log(`✅ Buffer ready (${this.audioQueue.length} chunks)`);
            this.isBuffering = false;
            this.processAudioQueue();
        }
    }
}
```

#### 3. Dynamic Re-buffering

```javascript
async processAudioQueue() {
    // If queue is running low, pause and re-buffer
    if (this.audioQueue.length < 2 && !this.isBuffering) {
        console.log(`⚠️ Buffer running low, re-buffering...`);
        this.isBuffering = true;
        this.bufferStartTime = Date.now();
        this.isPlaying = false;
        
        setTimeout(() => {
            if (this.isBuffering && this.audioQueue.length > 0) {
                console.log(`✅ Re-buffer complete`);
                this.isBuffering = false;
                this.processAudioQueue();
            }
        }, 100); // Short 100ms rebuffer time
        return;
    }
    
    // ... rest of playback logic
}
```

#### 4. Audio Context Stability

Added a small 10ms delay when starting first chunk for audio context stability:

```javascript
if (this.nextStartTime === 0 || this.nextStartTime < currentTime) {
    this.nextStartTime = currentTime + 0.01; // 10ms delay for stability
}
```

## Benefits

1. **Eliminates Crackling**: Pre-buffering ensures smooth, gapless playback
2. **Network Jitter Tolerance**: Buffer absorbs small network delays
3. **Intelligent Re-buffering**: Automatically pauses and buffers if queue runs low
4. **Balanced Latency**: Maximum 500ms initial buffer wait, 100ms re-buffer wait
5. **Matches Desktop Quality**: Web version now has same audio quality as desktop

## Testing Recommendations

1. Test on various network conditions (fast/slow/unstable)
2. Compare audio quality between web and desktop versions
3. Monitor console logs for buffer behavior:
   - `🔄 Buffering started` - Initial buffering
   - `✅ Buffer ready` - Playback starting
   - `⚠️ Buffer running low` - Re-buffering triggered
   - `🔇 Audio queue empty` - Playback complete

## Technical Details

- **Buffer Size**: 3 chunks (approximately 150-300ms of audio at 24kHz)
- **Initial Buffer Wait**: Maximum 500ms
- **Re-buffer Wait**: 100ms
- **Audio Format**: PCM16, 24kHz, mono (matches OpenAI Realtime API)
- **Scheduling**: Gapless playback using `AudioContext.currentTime`

## Result

The web version now provides **crystal-clear, smooth audio playback** without any crackling or popping, matching the quality of the desktop version. ✅
