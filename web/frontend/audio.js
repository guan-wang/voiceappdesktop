/**
 * Audio Manager - Handles browser audio recording and playback
 * Manages MediaRecorder for PTT input and Web Audio API for output
 */

class AudioManager {
    constructor() {
        this.mediaRecorder = null;
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.chunks = [];
        this.stream = null;
        
        // Audio settings to match OpenAI Realtime API
        this.sampleRate = 24000;
        this.targetSampleRate = 24000;
        
        // For gapless playback
        this.nextStartTime = 0;
        this.scheduledSources = [];
    }
    
    async initialize() {
        try {
            console.log('🎤 Requesting microphone access...');
            
            // Check if getUserMedia is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Your browser does not support audio recording. Please use Chrome, Firefox, or Safari.');
            }
            
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            console.log('✅ Microphone access granted');
            
            // Initialize audio context for playback
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.targetSampleRate
            });
            
            console.log('✅ Audio context created');
            console.log('✅ Audio initialized successfully');
            return true;
        } catch (error) {
            console.error('❌ Error initializing audio:', error);
            
            // Provide specific error messages
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                throw new Error('Microphone permission denied. Please allow microphone access in your browser settings.');
            } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                throw new Error('No microphone found. Please connect a microphone and refresh the page.');
            } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
                throw new Error('Microphone is already in use by another application. Please close other apps using the microphone.');
            } else {
                throw new Error(`Microphone error: ${error.message}`);
            }
        }
    }
    
    startRecording() {
        if (!this.stream) {
            console.error('❌ Stream not initialized');
            throw new Error('Audio not initialized. Please refresh the page.');
        }
        
        this.chunks = [];
        
        // Check MediaRecorder support
        if (!window.MediaRecorder) {
            throw new Error('Your browser does not support audio recording. Please use Chrome, Firefox, or Safari.');
        }
        
        // Check supported mimeTypes
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/webm')
            ? 'audio/webm'
            : MediaRecorder.isTypeSupported('audio/mp4')
            ? 'audio/mp4'
            : '';
        
        if (!mimeType) {
            throw new Error('Your browser does not support any compatible audio format.');
        }
        
        console.log('🎤 Using audio format:', mimeType);
        
        // Create MediaRecorder
        const options = {
            mimeType: mimeType,
            audioBitsPerSecond: 16000
        };
        
        try {
            this.mediaRecorder = new MediaRecorder(this.stream, options);
        } catch (error) {
            console.error('❌ MediaRecorder creation failed:', error);
            throw new Error(`Failed to create audio recorder: ${error.message}`);
        }
        
        // Collect audio chunks
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.chunks.push(event.data);
            }
        };
        
        // Add error handler for MediaRecorder
        this.mediaRecorder.onerror = (event) => {
            console.error('❌ MediaRecorder error:', event.error);
        };
        
        // Start recording
        try {
            this.mediaRecorder.start();
            console.log('🎤 Recording started successfully');
        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            throw new Error(`Failed to start recording: ${error.message}`);
        }
    }
    
    async stopRecording(discard = false) {
        if (!this.mediaRecorder || this.mediaRecorder.state !== 'recording') {
            return null;
        }
        
        return new Promise((resolve) => {
            if (discard) {
                // Just stop and discard
                this.mediaRecorder.onstop = () => {
                    console.log('🗑️ Recording discarded');
                    this.chunks = [];
                    resolve(null);
                };
                this.mediaRecorder.stop();
            } else {
                // Stop and process audio
                this.mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(this.chunks, { type: 'audio/webm' });
                    
                    // Convert to PCM16 and base64
                    try {
                        const base64Audio = await this.convertToBase64PCM(audioBlob);
                        this.chunks = [];
                        resolve(base64Audio);
                    } catch (error) {
                        console.error('❌ Error converting audio:', error);
                        this.chunks = [];
                        resolve(null);
                    }
                };
                this.mediaRecorder.stop();
                console.log('🛑 Recording stopped');
            }
        });
    }
    
    async convertToBase64PCM(audioBlob) {
        // Read blob as array buffer
        const arrayBuffer = await audioBlob.arrayBuffer();
        
        // Decode audio data
        const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
        
        // Get raw PCM data (mono, 24kHz)
        let channelData = audioBuffer.getChannelData(0);
        
        // Resample if necessary
        if (audioBuffer.sampleRate !== this.targetSampleRate) {
            channelData = this.resample(channelData, audioBuffer.sampleRate, this.targetSampleRate);
        }
        
        // Convert float32 to int16 (PCM16)
        const pcm16 = new Int16Array(channelData.length);
        for (let i = 0; i < channelData.length; i++) {
            const s = Math.max(-1, Math.min(1, channelData[i]));
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        // Convert to base64
        const uint8Array = new Uint8Array(pcm16.buffer);
        const base64 = this.arrayBufferToBase64(uint8Array);
        
        return base64;
    }
    
    resample(audioData, fromSampleRate, toSampleRate) {
        // Simple linear interpolation resampling
        const ratio = fromSampleRate / toSampleRate;
        const newLength = Math.round(audioData.length / ratio);
        const result = new Float32Array(newLength);
        
        for (let i = 0; i < newLength; i++) {
            const srcIndex = i * ratio;
            const srcIndexFloor = Math.floor(srcIndex);
            const srcIndexCeil = Math.min(srcIndexFloor + 1, audioData.length - 1);
            const t = srcIndex - srcIndexFloor;
            
            result[i] = audioData[srcIndexFloor] * (1 - t) + audioData[srcIndexCeil] * t;
        }
        
        return result;
    }
    
    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }
    
    async playAudioChunk(base64Audio) {
        // Queue audio for playback
        this.audioQueue.push(base64Audio);
        
        if (!this.isPlaying) {
            this.processAudioQueue();
        }
    }
    
    async processAudioQueue() {
        if (this.audioQueue.length === 0) {
            this.isPlaying = false;
            return;
        }
        
        this.isPlaying = true;
        const base64Audio = this.audioQueue.shift();
        
        try {
            // Decode base64 to array buffer
            const binaryString = window.atob(base64Audio);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Convert PCM16 to float32 for Web Audio API
            const int16Array = new Int16Array(bytes.buffer);
            const float32Array = new Float32Array(int16Array.length);
            for (let i = 0; i < int16Array.length; i++) {
                float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
            }
            
            // Create audio buffer
            const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, this.targetSampleRate);
            audioBuffer.getChannelData(0).set(float32Array);
            
            // Create source and connect
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            
            // GAPLESS PLAYBACK: Schedule this chunk to start exactly when the previous ends
            const currentTime = this.audioContext.currentTime;
            const chunkDuration = audioBuffer.duration;
            
            // If this is the first chunk or there's a gap, start immediately
            if (this.nextStartTime === 0 || this.nextStartTime < currentTime) {
                this.nextStartTime = currentTime;
            }
            
            // Schedule playback at precise time
            source.start(this.nextStartTime);
            
            // Calculate when next chunk should start (exactly after this one)
            this.nextStartTime += chunkDuration;
            
            // Clean up when finished
            source.onended = () => {
                // Remove from scheduled sources
                const index = this.scheduledSources.indexOf(source);
                if (index > -1) {
                    this.scheduledSources.splice(index, 1);
                }
                
                // Process next chunk
                this.processAudioQueue();
            };
            
            // Track scheduled sources
            this.scheduledSources.push(source);
            
        } catch (error) {
            console.error('❌ Error playing audio:', error);
            this.processAudioQueue();
        }
    }
    
    clearQueue() {
        this.audioQueue = [];
        
        // Stop all scheduled audio sources
        this.scheduledSources.forEach(source => {
            try {
                source.stop();
            } catch (e) {
                // Source might have already ended
            }
        });
        this.scheduledSources = [];
        
        // Reset timing
        this.nextStartTime = 0;
        this.isPlaying = false;
    }
    
    cleanup() {
        if (this.mediaRecorder) {
            this.mediaRecorder.stop();
        }
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
}
