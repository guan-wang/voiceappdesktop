/**
 * Main App - Handles WebSocket connection, PTT logic, and UI updates
 */

class KoreanVoiceTutor {
    constructor() {
        this.ws = null;
        this.audioManager = new AudioManager();
        this.sessionId = null;
        this.isRecording = false;
        this.isConnected = false;
        this.isAISpeaking = false;
        
        // PTT timing
        this.pressStartTime = null;
        this.minHoldDuration = 500; // 500ms minimum
        this.maxHoldDuration = 60000; // 60s maximum
        
        // UI elements
        this.pttButton = document.getElementById('pttButton');
        this.pttHint = document.getElementById('pttHint');
        this.status = document.getElementById('status');
        this.statusText = this.status.querySelector('.status-text');
        this.transcriptContainer = document.getElementById('transcriptContainer');
        
        this.init();
    }
    
    async init() {
        try {
            console.log('🚀 Initializing app...');
            
            // Initialize audio
            await this.audioManager.initialize();
            console.log('✅ Audio manager initialized');
            
            this.updateStatus('connecting', 'Connecting to server...');
            
            // Connect to WebSocket
            this.connect();
            
            // Setup PTT button
            this.setupPTTButton();
            
            console.log('✅ App initialized successfully');
            
        } catch (error) {
            console.error('❌ Initialization error:', error);
            this.updateStatus('error', 'Initialization failed');
            
            // Show detailed error message
            this.showMessage('system', error.message || 'Failed to initialize. Please check browser permissions.');
            
            // Keep button disabled
            this.pttButton.disabled = true;
            this.pttHint.textContent = error.message || 'Initialization failed';
        }
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('🔌 Connecting to:', wsUrl);
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.updateStatus('connecting', 'Connected, starting session...');
        };
        
        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
        
        this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.updateStatus('error', 'Connection error');
        };
        
        this.ws.onclose = () => {
            console.log('🔌 WebSocket closed');
            this.updateStatus('error', 'Disconnected');
            this.isConnected = false;
            this.pttButton.disabled = true;
            
            // Attempt reconnection after 3 seconds
            setTimeout(() => {
                if (!this.isConnected) {
                    this.showMessage('system', 'Attempting to reconnect...');
                    this.connect();
                }
            }, 3000);
        };
    }
    
    handleMessage(message) {
        const { type } = message;
        
        switch (type) {
            case 'session_created':
                this.sessionId = message.session_id;
                console.log('📝 Session ID:', this.sessionId);
                break;
            
            case 'session_started':
                this.isConnected = true;
                this.updateStatus('connected', 'Loading interview protocol...');
                this.pttButton.disabled = true;  // Keep disabled until setup complete
                this.pttHint.textContent = 'Loading...';
                this.clearWelcome();
                this.showMessage('system', 'Initializing interview...');
                break;
            
            case 'setup_complete':
                // Interview guidance loaded, now ready for user
                this.updateStatus('connected', 'Ready to speak');
                this.pttButton.disabled = false;
                this.pttHint.textContent = 'Hold button to speak in Korean';
                this.showMessage('system', message.message || 'Ready! Hold the button to speak.');
                break;
            
            case 'user_transcript':
                this.showMessage('user', message.text);
                break;
            
            case 'ai_transcript':
                this.showMessage('ai', message.text);
                break;
            
            case 'ai_audio':
                // Play AI audio
                if (!this.isAISpeaking) {
                    this.isAISpeaking = true;
                    this.pttButton.disabled = true; // Disable PTT while AI speaks
                    console.log('🔊 AI started speaking');
                }
                this.audioManager.playAudioChunk(message.audio);
                break;
            
            case 'response_complete':
                // AI finished responding
                console.log('✅ AI response complete');
                this.isAISpeaking = false;
                if (this.isConnected) {
                    this.pttButton.disabled = false;
                    this.pttHint.textContent = 'Ready - Hold button to speak';
                }
                break;
            
            case 'assessment_triggered':
                this.showMessage('system', '📊 Assessment triggered. Preparing your evaluation...');
                this.pttButton.disabled = true;
                this.pttHint.textContent = 'Assessment in progress...';
                break;
            
            case 'assessment_complete':
                this.showMessage('system', '✅ Assessment complete! Listen to your results.');
                console.log('📊 Assessment report:', message.report);
                // Report is available in message.report
                // Summary being spoken by AI
                break;
            
            case 'error':
                console.error('❌ Server error:', message.message);
                this.showMessage('system', `Error: ${message.message}`);
                break;
        }
    }
    
    setupPTTButton() {
        // Handle both touch and mouse events for broad compatibility
        
        // Touch events (mobile)
        this.pttButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        
        this.pttButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording();
        });
        
        this.pttButton.addEventListener('touchcancel', (e) => {
            e.preventDefault();
            this.stopRecording();
        });
        
        // Mouse events (desktop)
        this.pttButton.addEventListener('mousedown', (e) => {
            if (!('ontouchstart' in window)) { // Only for non-touch devices
                this.startRecording();
            }
        });
        
        this.pttButton.addEventListener('mouseup', (e) => {
            if (!('ontouchstart' in window)) {
                this.stopRecording();
            }
        });
        
        this.pttButton.addEventListener('mouseleave', (e) => {
            if (!('ontouchstart' in window) && this.isRecording) {
                this.stopRecording();
            }
        });
        
        // Prevent context menu on long press
        this.pttButton.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });
    }
    
    startRecording() {
        if (!this.isConnected || this.isRecording || this.isAISpeaking) {
            return;
        }
        
        this.isRecording = true;
        this.pressStartTime = Date.now();
        
        // Visual feedback
        this.pttButton.classList.add('recording');
        this.pttButton.querySelector('.ptt-text').textContent = 'Recording...';
        this.pttHint.textContent = 'Release to send';
        
        // Haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        // Start audio recording
        try {
            console.log('🎤 Starting recording...');
            this.audioManager.startRecording((audioData) => {
                console.log('📤 Audio data ready to send');
                this.sendAudio(audioData);
            });
            console.log('✅ Recording started successfully');
        } catch (error) {
            console.error('❌ Recording error:', error);
            this.showMessage('system', error.message || 'Recording failed. Please refresh the page and try again.');
            this.isRecording = false;
            this.resetPTTButton();
        }
    }
    
    stopRecording() {
        if (!this.isRecording) {
            return;
        }
        
        const holdDuration = Date.now() - this.pressStartTime;
        
        // Check minimum hold duration
        if (holdDuration < this.minHoldDuration) {
            console.log('⚠️ Too short:', holdDuration, 'ms');
            this.showMessage('system', 'Hold the button longer to speak');
            this.audioManager.stopRecording();
            this.isRecording = false;
            this.resetPTTButton();
            return;
        }
        
        // Check maximum hold duration
        if (holdDuration > this.maxHoldDuration) {
            console.log('⚠️ Too long:', holdDuration, 'ms');
            this.showMessage('system', 'Message too long. Please speak more concisely.');
        }
        
        // Stop recording
        this.audioManager.stopRecording();
        this.isRecording = false;
        
        // Visual feedback
        this.pttButton.querySelector('.ptt-text').textContent = 'Processing...';
        this.pttHint.textContent = 'Sending audio...';
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([50, 50, 50]);
        }
        
        console.log('✅ Recorded:', holdDuration, 'ms');
    }
    
    sendAudio(audioData) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('❌ WebSocket not connected');
            this.showMessage('system', 'Connection lost. Please refresh.');
            this.resetPTTButton();
            return;
        }
        
        try {
            this.ws.send(JSON.stringify({
                type: 'audio',
                data: audioData
            }));
            console.log('📤 Audio sent');
            this.resetPTTButton();
        } catch (error) {
            console.error('❌ Send error:', error);
            this.showMessage('system', 'Failed to send audio');
            this.resetPTTButton();
        }
    }
    
    resetPTTButton() {
        this.pttButton.classList.remove('recording');
        this.pttButton.querySelector('.ptt-text').textContent = 'Hold to Speak';
        this.pttHint.textContent = 'Hold button to speak in Korean';
    }
    
    updateStatus(state, text) {
        this.status.className = 'status ' + state;
        this.statusText.textContent = text;
    }
    
    clearWelcome() {
        const welcome = this.transcriptContainer.querySelector('.transcript-welcome');
        if (welcome) {
            welcome.remove();
        }
    }
    
    showMessage(role, text) {
        this.clearWelcome();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `transcript-message ${role}`;
        
        if (role !== 'system') {
            const label = document.createElement('div');
            label.className = 'transcript-label';
            label.textContent = role === 'user' ? 'You' : 'AI';
            messageDiv.appendChild(label);
        }
        
        const textDiv = document.createElement('div');
        textDiv.className = 'transcript-text';
        textDiv.textContent = text;
        messageDiv.appendChild(textDiv);
        
        this.transcriptContainer.appendChild(messageDiv);
        
        // Auto-scroll to bottom
        this.transcriptContainer.scrollTop = this.transcriptContainer.scrollHeight;
    }
    
    cleanup() {
        if (this.ws) {
            this.ws.close();
        }
        if (this.audioManager) {
            this.audioManager.cleanup();
        }
    }
}

// Initialize app when page loads
window.addEventListener('DOMContentLoaded', () => {
    window.app = new KoreanVoiceTutor();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.app) {
        window.app.cleanup();
    }
});

// Prevent screen sleep during session
if ('wakeLock' in navigator) {
    let wakeLock = null;
    const requestWakeLock = async () => {
        try {
            wakeLock = await navigator.wakeLock.request('screen');
            console.log('🔆 Wake lock enabled');
        } catch (err) {
            console.log('Wake lock not available:', err);
        }
    };
    requestWakeLock();
}
