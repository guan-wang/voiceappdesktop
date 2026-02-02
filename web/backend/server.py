"""
FastAPI Server - Main entry point for Korean Voice Tutor web app
Serves frontend and handles WebSocket connections
"""

import os
import sys
import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
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

# Handle imports - works both for direct execution and as module
try:
    # Try relative imports first (Railway deployment, run as module)
    from .session_store import session_store
    from .realtime_bridge import RealtimeBridge
except ImportError:
    # Fall back to absolute imports (local development, direct execution)
    # Add parent directory to path for imports
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    web_dir = os.path.dirname(backend_dir)
    project_dir = os.path.dirname(web_dir)
    sys.path.insert(0, project_dir)
    
    from web.backend.session_store import session_store
    from web.backend.realtime_bridge import RealtimeBridge

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    print("🚀 Korean Voice Tutor Web Server")
    print(f"📊 API Key: {'✓' if os.getenv('OPENAI_API_KEY') else '✗'}")
    
    # Start session cleanup task
    session_store.start_cleanup_task()
    
    yield
    
    # Shutdown
    print("\n👋 Shutting down...")
    try:
        await asyncio.wait_for(
            session_store.shutdown_all_sessions(),
            timeout=5.0
        )
        print("✅ All sessions cleaned up")
    except asyncio.TimeoutError:
        print("⚠️ Cleanup timeout - forcing shutdown")
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")


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


@app.post("/api/submit_survey")
async def submit_survey(request: Request):
    """Save survey responses to assessment JSON"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        responses = data.get("responses")
        
        if not session_id:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "session_id required"}
            )
        
        if not responses:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "responses required"}
            )
        
        # Append survey to assessment file
        filepath = session_store.append_survey_to_assessment(session_id, responses)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Survey saved successfully",
                "file": os.path.basename(filepath)
            }
        )
        
    except FileNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": str(e)}
        )
    except Exception as e:
        print(f"❌ Error saving survey: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": session_store.get_active_session_count(),
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY"))
    }


@app.get("/api/reports")
async def list_reports():
    """List all assessment reports"""
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        
        # Create directory if it doesn't exist
        if not os.path.exists(reports_dir):
            return {"reports": [], "count": 0}
        
        # Get all JSON files
        files = [f for f in os.listdir(reports_dir) if f.endswith('.json') and not f.startswith('.')]
        
        # Sort by date (newest first) - filename format: web_assessment_YYYYMMDD_HHMMSS.json
        files.sort(reverse=True)
        
        # Get file details
        file_details = []
        for filename in files:
            file_path = os.path.join(reports_dir, filename)
            file_size = os.path.getsize(file_path)
            file_details.append({
                "filename": filename,
                "size": file_size,
                "download_url": f"/api/reports/{filename}"
            })
        
        return {
            "reports": file_details,
            "count": len(files)
        }
        
    except Exception as e:
        print(f"❌ Error listing reports: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    """Download a specific report"""
    try:
        # Security: prevent directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid filename"}
            )
        
        reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        file_path = os.path.join(reports_dir, filename)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(
                file_path,
                filename=filename,
                media_type="application/json"
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "File not found"}
            )
            
    except Exception as e:
        print(f"❌ Error downloading report: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


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
    
    print(f"🔌 [{session.session_id[:8]}] Connected")
    
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
                break
            
            else:
                print(f"⚠️ [{session.session_id[:8]}] Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        print(f"🔌 [{session.session_id[:8]}] Disconnected")
    
    except Exception as e:
        print(f"❌ [{session.session_id[:8]}] Error: {e}")
    
    finally:
        # Cleanup
        session.is_active = False
        
        # Cleanup bridge and its background tasks
        try:
            await bridge.cleanup()
        except Exception as e:
            print(f"⚠️ [{session.session_id[:8]}] Bridge cleanup error: {e}")
        
        # Cancel OpenAI task with timeout
        if not openai_task.done():
            openai_task.cancel()
            try:
                await asyncio.wait_for(openai_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        # Remove session
        session_store.remove_session(session.session_id)


def main():
    """Run the server"""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please create a .env file with your OpenAI API key")
        print("   Example: OPENAI_API_KEY=sk-...")
        return
    
    # Run server
    port = int(os.getenv("PORT", 8080))  # Default to 8080 for Railway
    
    # Check if SSL certificates exist
    cert_file = os.path.join(os.path.dirname(__file__), "cert.pem")
    key_file = os.path.join(os.path.dirname(__file__), "key.pem")
    use_ssl = os.path.exists(cert_file) and os.path.exists(key_file)
    
    protocol = "https" if use_ssl else "http"
    
    print(f"\n🌐 Server: {protocol}://localhost:{port}")
    if use_ssl:
        print(f"🔒 HTTPS enabled")
    else:
        print(f"⚠️  HTTP only (run .\\setup_https_python.ps1 for mobile access)")
    
    print("\nPress Ctrl+C to stop\n")
    
    # Configure uvicorn with proper timeouts
    config = {
        "app": app,
        "host": "0.0.0.0",
        "port": port,
        "log_level": "info",
        "timeout_graceful_shutdown": 5  # Force shutdown after 5 seconds
    }
    
    # Add SSL if certificates exist
    if use_ssl:
        config["ssl_keyfile"] = key_file
        config["ssl_certfile"] = cert_file
    
    uvicorn.run(**config)


if __name__ == "__main__":
    main()
