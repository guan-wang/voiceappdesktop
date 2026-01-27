"""
FastAPI Server - Main entry point for Korean Voice Tutor web app
Serves frontend and handles WebSocket connections
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from dotenv import load_dotenv
import uvicorn

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

from session_store import session_store
from realtime_bridge import RealtimeBridge

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    print("🚀 Starting Korean Voice Tutor Web Server...")
    print(f"📊 API Key configured: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    # Start session cleanup task
    session_store.start_cleanup_task()
    print("✅ Session cleanup task started")
    
    yield
    
    # Shutdown (if needed)
    print("👋 Shutting down server...")


# Initialize FastAPI app with lifespan
app = FastAPI(title="Korean Voice Tutor", version="2.0", lifespan=lifespan)

# Mount frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "../frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def read_root():
    """Serve the main frontend HTML"""
    index_path = os.path.join(frontend_dir, "index.html")
    return FileResponse(index_path)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": session_store.get_active_session_count(),
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY"))
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for browser clients
    Handles PTT audio and bidirectional communication
    """
    await websocket.accept()
    
    # Create new session
    session = session_store.create_session()
    session.is_active = True
    
    print(f"🔌 [{session.session_id[:8]}] Client connected")
    
    # Send session ID to client
    await websocket.send_json({
        "type": "session_created",
        "session_id": session.session_id
    })
    
    # Create bridge to OpenAI
    bridge = RealtimeBridge(session, websocket)
    
    # Start OpenAI connection in background
    openai_task = asyncio.create_task(bridge.connect_to_openai())
    session.openai_task = openai_task
    
    try:
        # Handle messages from client
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            
            if message_type == "audio":
                # PTT audio message from client
                audio_data = message.get("data")
                if audio_data:
                    await bridge.handle_client_audio(audio_data)
                    session.update_activity()
            
            elif message_type == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})
                session.update_activity()
            
            elif message_type == "end_session":
                # Client requested to end session
                print(f"👋 [{session.session_id[:8]}] Client ended session")
                break
            
            else:
                print(f"⚠️ [{session.session_id[:8]}] Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        print(f"🔌 [{session.session_id[:8]}] Client disconnected")
    
    except Exception as e:
        print(f"❌ [{session.session_id[:8]}] WebSocket error: {e}")
    
    finally:
        # Cleanup
        session.is_active = False
        
        # Cancel OpenAI task
        if not openai_task.done():
            openai_task.cancel()
            try:
                await openai_task
            except asyncio.CancelledError:
                pass
        
        # Remove session
        session_store.remove_session(session.session_id)
        
        print(f"✅ [{session.session_id[:8]}] Session cleanup complete")


def main():
    """Run the server"""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please create a .env file with your OpenAI API key")
        print("   Example: OPENAI_API_KEY=sk-...")
        return
    
    # Run server
    port = int(os.getenv("PORT", 7860))  # Default to 7860 for HuggingFace Spaces
    
    # Check if SSL certificates exist
    cert_file = os.path.join(os.path.dirname(__file__), "cert.pem")
    key_file = os.path.join(os.path.dirname(__file__), "key.pem")
    use_ssl = os.path.exists(cert_file) and os.path.exists(key_file)
    
    protocol = "https" if use_ssl else "http"
    
    print(f"\n🌐 Starting server on {protocol}://localhost:{port}")
    print(f"📱 Open in browser: {protocol}://localhost:{port}")
    
    if use_ssl:
        print(f"🔒 HTTPS enabled (SSL certificates found)")
        print(f"   Certificate: cert.pem")
        print(f"   Key: key.pem")
    else:
        print(f"⚠️  HTTP only (no SSL certificates)")
        print(f"   For mobile microphone access, run: .\\setup_https_python.ps1")
    
    print("\nPress Ctrl+C to stop\n")
    
    # Run with SSL if certificates exist
    if use_ssl:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            ssl_keyfile=key_file,
            ssl_certfile=cert_file,
            log_level="info"
        )
    else:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )


if __name__ == "__main__":
    main()
