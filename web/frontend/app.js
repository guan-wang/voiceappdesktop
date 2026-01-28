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
        this.isAssessing = false;
        this.isInitialized = false;
        this.assessmentComplete = false;
        this.hasInteractedWithMic = false; // Track if user has pressed mic
        
        // PTT timing
        this.pressStartTime = null;
        this.minHoldDuration = 1000; // 1000ms minimum (changed from 500ms)
        this.maxHoldDuration = 60000; // 60s maximum
        
        // Streaming state
        this.streamingText = '';
        this.streamingInterval = null;
        
        // Track AI messages for rolling view (keep last 3)
        this.aiMessages = [];
        
        // UI elements
        this.micButton = document.getElementById('micButton');
        this.micHint = document.getElementById('micHint');
        this.micTip = document.getElementById('micTip');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.statusDot = this.statusIndicator.querySelector('.status-dot');
        this.aiTranscript = document.getElementById('aiTranscript');
        this.userTranscript = document.getElementById('userTranscript');
        this.loadingState = document.getElementById('loadingState');
        this.systemMessage = document.getElementById('systemMessage');
        this.welcomeOverlay = document.getElementById('welcomeOverlay');
        this.startButton = document.getElementById('startButton');
        this.beginnerLink = document.getElementById('beginnerLink');
        this.beginnerModal = document.getElementById('beginnerModal');
        this.modalCloseButton = document.getElementById('modalCloseButton');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.nextButtonContainer = document.getElementById('nextButtonContainer');
        this.nextButton = document.getElementById('nextButton');
        
        // Survey elements
        this.surveyOverlay = document.getElementById('surveyOverlay');
        this.surveyForm = document.getElementById('surveyForm');
        this.surveySuccess = document.getElementById('surveySuccess');
        this.surveySkipLink = document.getElementById('surveySkipLink');
        this.surveyCloseButton = document.getElementById('surveyCloseButton');
        
        // Setup welcome screen
        this.setupWelcomeScreen();
        
        // Setup next button
        this.setupNextButton();
        
        // Setup survey
        this.setupSurvey();
    }
    
    setupWelcomeScreen() {
        // Handle START button
        this.startButton.addEventListener('click', () => {
            // Hide welcome overlay with animation
            this.welcomeOverlay.classList.add('hidden');
            
            // Start initialization after animation
            setTimeout(() => {
                this.init();
            }, 300);
        });
        
        // Handle beginner link
        this.beginnerLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.showBeginnerModal();
        });
        
        // Handle modal close button
        this.modalCloseButton.addEventListener('click', () => {
            this.hideBeginnerModal();
        });
        
        // Handle clicking outside modal to close
        this.beginnerModal.addEventListener('click', (e) => {
            if (e.target === this.beginnerModal) {
                this.hideBeginnerModal();
            }
        });
    }
    
    showBeginnerModal() {
        this.beginnerModal.classList.add('active');
    }
    
    hideBeginnerModal() {
        this.beginnerModal.classList.remove('active');
    }
    
    setupNextButton() {
        this.nextButton.addEventListener('click', () => {
            console.log('📝 Next button clicked - showing survey');
            // Hide next button and show survey
            this.nextButtonContainer.style.display = 'none';
            this.showSurvey();
        });
    }
    
    setupSurvey() {
        // Handle survey form submission
        this.surveyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(this.surveyForm);
            const responses = {
                comfort_level: formData.get('comfort_level'),
                feedback_usefulness: formData.get('feedback_usefulness'),
                name: formData.get('name'),
                email: formData.get('email')
            };
            
            console.log('📋 Survey responses:', responses);
            
            // Disable submit button
            const submitBtn = this.surveyForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Saving...';
            
            try {
                // Send to backend
                const response = await fetch('/api/submit_survey', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: this.sessionId,
                        responses: responses
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    console.log('✅ Survey saved:', result);
                    this.showSurveySuccess();
                } else {
                    console.error('❌ Survey save failed:', result);
                    alert('Failed to save survey. Please try again.');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Save My Report & Start Learning 🚀';
                }
            } catch (error) {
                console.error('❌ Survey error:', error);
                alert('Failed to save survey. Please try again.');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Save My Report & Start Learning 🚀';
            }
        });
        
        // Handle skip link
        this.surveySkipLink.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('⏭️ Survey skipped');
            this.closeSurvey();
        });
        
        // Handle close button (after success)
        this.surveyCloseButton.addEventListener('click', () => {
            this.closeSurvey();
        });
    }
    
    showSurvey() {
        this.surveyOverlay.style.display = 'flex';
        this.surveyForm.style.display = 'flex';
        this.surveySuccess.style.display = 'none';
        console.log('📋 Survey displayed');
    }
    
    showSurveySuccess() {
        this.surveyForm.style.display = 'none';
        this.surveySuccess.style.display = 'block';
    }
    
    closeSurvey() {
        this.surveyOverlay.style.display = 'none';
        console.log('👋 Survey closed - reloading app');
        // Reload to start fresh
        setTimeout(() => {
            window.location.reload();
        }, 500);
    }
    
    async init() {
        if (this.isInitialized) {
            return;
        }
        
        try {
            console.log('🚀 Initializing app...');
            this.isInitialized = true;
            
            // Show loading state
            this.showLoading();
            this.setMicButtonState('inactive');
            
            // Initialize audio
            await this.audioManager.initialize();
            console.log('✅ Audio manager initialized');
            
            // Connect to WebSocket
            this.connect();
            
            // Setup mic button
            this.setupMicButton();
            
            console.log('✅ App initialized successfully');
            
        } catch (error) {
            console.error('❌ Initialization error:', error);
            this.hideLoading();
            this.showEphemeralMessage('Failed to initialize. Please refresh the page.');
            this.setMicButtonState('inactive');
        }
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('🔌 Connecting to:', wsUrl);
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.statusDot.classList.add('connected');
        };
        
        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
        
        this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.statusDot.classList.add('error');
            this.showEphemeralMessage('Connection error');
        };
        
        this.ws.onclose = () => {
            console.log('🔌 WebSocket closed');
            this.statusDot.classList.add('error');
            this.isConnected = false;
            this.setMicButtonState('inactive');
            
            // Attempt reconnection after 3 seconds
            setTimeout(() => {
                if (!this.isConnected) {
                    this.showEphemeralMessage('Attempting to reconnect...');
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
                this.statusDot.classList.add('connected');
                console.log('✅ Session started, loading guidance...');
                break;
            
            case 'setup_complete':
                // Interview guidance loaded, ready for user
                console.log('✅ Setup complete, ready to speak');
                this.hideLoading();
                this.setMicButtonState('ready');
                this.micHint.textContent = '버튼을 누르고 말하세요';
                break;
            
            case 'user_transcript':
                this.streamUserTranscript(message.text);
                break;
            
            case 'ai_transcript':
                this.streamAITranscript(message.text);
                break;
            
            case 'ai_audio':
                // Play AI audio
                if (!this.isAISpeaking) {
                    this.isAISpeaking = true;
                    this.setMicButtonState('inactive'); // Disable while AI speaks
                    console.log('🔊 AI started speaking');
                }
                this.audioManager.playAudioChunk(message.audio);
                break;
            
            case 'response_complete':
                // AI finished responding
                console.log('✅ AI response complete');
                this.isAISpeaking = false;
                
                // If assessment is complete, show Next button instead of re-enabling mic
                if (this.assessmentComplete) {
                    console.log('📋 Assessment report finished - showing Next button');
                    this.showNextButton();
                } else if (this.isConnected && !this.isAssessing) {
                    // Re-enable button after AI finishes (normal conversation)
                    this.setMicButtonState('ready');
                }
                break;
            
            case 'assessment_triggered':
                console.log('📊 Assessment triggered');
                this.setMicButtonState('inactive');
                this.isAssessing = true;
                // Show loading overlay
                this.showLoadingOverlay();
                break;
            
            case 'assessment_complete':
                console.log('📊 Assessment complete:', message.report);
                this.isAssessing = false;
                this.assessmentComplete = true;
                // Hide loading overlay - return to conversation
                this.hideLoadingOverlay();
                // AI will now speak the report, so keep mic disabled
                this.setMicButtonState('inactive');
                this.micButton.disabled = true;
                break;
            
            case 'error':
                console.error('❌ Server error:', message.message);
                this.showEphemeralMessage('Error: ' + message.message);
                break;
        }
    }
    
    setupMicButton() {
        // Touch events (mobile)
        this.micButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        
        this.micButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording();
        });
        
        this.micButton.addEventListener('touchcancel', (e) => {
            e.preventDefault();
            this.stopRecording();
        });
        
        // Mouse events (desktop)
        this.micButton.addEventListener('mousedown', (e) => {
            if (!('ontouchstart' in window)) {
                this.startRecording();
            }
        });
        
        this.micButton.addEventListener('mouseup', (e) => {
            if (!('ontouchstart' in window)) {
                this.stopRecording();
            }
        });
        
        this.micButton.addEventListener('mouseleave', (e) => {
            if (!('ontouchstart' in window) && this.isRecording) {
                this.stopRecording();
            }
        });
        
        // Prevent context menu
        this.micButton.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });
    }
    
    startRecording() {
        if (!this.isConnected || this.isRecording || this.isAISpeaking || this.isAssessing || 
            this.micButton.classList.contains('state-inactive')) {
            return;
        }
        
        // Hide tip on first mic interaction
        if (!this.hasInteractedWithMic) {
            this.hasInteractedWithMic = true;
            this.micTip.classList.add('hidden');
        }
        
        this.isRecording = true;
        this.pressStartTime = Date.now();
        
        // Visual feedback
        this.setMicButtonState('recording');
        this.micHint.textContent = '말하는 중...';
        
        // Clear user transcript
        this.userTranscript.textContent = '';
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        // Start audio recording
        try {
            console.log('🎤 Starting recording...');
            this.audioManager.startRecording((audioData) => {
                this.sendAudio(audioData);
            });
        } catch (error) {
            console.error('❌ Recording error:', error);
            this.showEphemeralMessage('Recording failed. Please try again.');
            this.isRecording = false;
            this.setMicButtonState('ready');
        }
    }
    
    stopRecording() {
        if (!this.isRecording) {
            return;
        }
        
        const holdDuration = Date.now() - this.pressStartTime;
        
        // Check minimum hold duration (1000ms)
        if (holdDuration < this.minHoldDuration) {
            console.log('⚠️ Too short:', holdDuration, 'ms');
            this.showEphemeralMessage('Hold the button longer to speak');
            this.audioManager.stopRecording();
            this.isRecording = false;
            this.setMicButtonState('ready');
            this.micHint.textContent = '버튼을 누르고 말하세요';
            return;
        }
        
        // Check maximum hold duration
        if (holdDuration > this.maxHoldDuration) {
            console.log('⚠️ Too long:', holdDuration, 'ms');
            this.showEphemeralMessage('Message too long. Please speak more concisely.');
        }
        
        // Stop recording
        this.audioManager.stopRecording();
        this.isRecording = false;
        
        // Visual feedback
        this.setMicButtonState('inactive');
        this.micHint.textContent = '처리 중...';
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([50, 50, 50]);
        }
        
        console.log('✅ Recorded:', holdDuration, 'ms');
    }
    
    sendAudio(audioData) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('❌ WebSocket not connected');
            this.showEphemeralMessage('Connection lost. Please refresh.');
            this.setMicButtonState('ready');
            return;
        }
        
        try {
            this.ws.send(JSON.stringify({
                type: 'audio',
                data: audioData
            }));
            console.log('📤 Audio sent');
        } catch (error) {
            console.error('❌ Send error:', error);
            this.showEphemeralMessage('Failed to send audio');
            this.setMicButtonState('ready');
        }
    }
    
    // Mic button state management
    setMicButtonState(state) {
        this.micButton.className = 'mic-button state-' + state;
        this.micButton.disabled = (state === 'inactive');
    }
    
    // Loading state
    showLoading() {
        this.loadingState.classList.add('active');
    }
    
    hideLoading() {
        this.loadingState.classList.remove('active');
    }
    
    // Ephemeral system message
    showEphemeralMessage(text, duration = 3000) {
        this.systemMessage.textContent = text;
        this.systemMessage.classList.add('show');
        
        setTimeout(() => {
            this.systemMessage.classList.remove('show');
        }, duration);
    }
    
    // Stream AI transcript character by character with rolling view
    streamAITranscript(text) {
        if (this.streamingInterval) {
            clearInterval(this.streamingInterval);
        }
        
        // Add new message to array
        this.aiMessages.push(text);
        
        // Keep only last 3 messages
        if (this.aiMessages.length > 3) {
            this.aiMessages.shift();
        }
        
        // Clear and rebuild the transcript container
        this.aiTranscript.innerHTML = '';
        
        // Add all messages (showing last 3)
        this.aiMessages.forEach((msg, index) => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'ai-transcript-message';
            messageDiv.textContent = '';
            this.aiTranscript.appendChild(messageDiv);
            
            // Stream only the latest message, show others instantly
            if (index === this.aiMessages.length - 1) {
                // Stream the latest message character by character
                let charIndex = 0;
                this.streamingInterval = setInterval(() => {
                    if (charIndex < msg.length) {
                        messageDiv.textContent += msg[charIndex];
                        charIndex++;
                    } else {
                        clearInterval(this.streamingInterval);
                        this.streamingInterval = null;
                    }
                }, 30); // 30ms per character
            } else {
                // Show older messages instantly
                messageDiv.textContent = msg;
            }
        });
    }
    
    // Stream user transcript character by character
    streamUserTranscript(text) {
        this.userTranscript.textContent = '';
        let charIndex = 0;
        
        const interval = setInterval(() => {
            if (charIndex < text.length) {
                this.userTranscript.textContent += text[charIndex];
                charIndex++;
            } else {
                clearInterval(interval);
            }
        }, 30); // 30ms per character
    }
    
    showLoadingOverlay() {
        this.loadingOverlay.style.display = 'flex';
    }
    
    hideLoadingOverlay() {
        this.loadingOverlay.style.display = 'none';
    }
    
    showNextButton() {
        this.nextButtonContainer.style.display = 'block';
    }
    
    cleanup() {
        if (this.streamingInterval) {
            clearInterval(this.streamingInterval);
        }
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
