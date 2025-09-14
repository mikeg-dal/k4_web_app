import os
import time
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect
from starlette.middleware.base import BaseHTTPMiddleware

from connection import k4_tcp_reader
from config import pan_config, audio_config, web_config, k4_config, CAT_MODE_MAP
from radios.radio_config import get_radio_manager, get_current_radio_config

app = FastAPI()

# Security middleware for HTTP headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' ws: wss:;"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware using configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=web_config.CORS_ALLOWED_ORIGINS,
    allow_credentials=web_config.CORS_ALLOW_CREDENTIALS,
    allow_methods=web_config.CORS_ALLOWED_METHODS,
    allow_headers=web_config.CORS_ALLOWED_HEADERS,
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

clients = []

@app.get("/")
async def index():
    """Serve the main index.html from static directory"""
    return FileResponse("static/index.html", media_type="text/html")


@app.get("/config/panadapter")
async def get_panadapter_config():
    """Get panadapter configuration for JavaScript sync"""
    return JSONResponse({
        "DEFAULT_CENTER_FREQ": pan_config.DEFAULT_CENTER_FREQ,
        "DEFAULT_SPAN": pan_config.DEFAULT_SPAN,
        "DEFAULT_REF_LEVEL": pan_config.DEFAULT_REF_LEVEL,
        "DEFAULT_SCALE": pan_config.DEFAULT_SCALE,
        "DEFAULT_NOISE_FLOOR": pan_config.DEFAULT_NOISE_FLOOR,
        "MAX_WATERFALL_LINES": pan_config.MAX_WATERFALL_LINES,
        "WATERFALL_HISTORY_SIZE": pan_config.WATERFALL_HISTORY_SIZE,
        "DEFAULT_WATERFALL_HEIGHT": pan_config.DEFAULT_WATERFALL_HEIGHT,
        "DEFAULT_SPECTRUM_AVERAGING": pan_config.DEFAULT_SPECTRUM_AVERAGING,
        "DEFAULT_WATERFALL_AVERAGING": pan_config.DEFAULT_WATERFALL_AVERAGING
    })

@app.get("/config/audio")
async def get_audio_config():
    """Get audio configuration for JavaScript sync"""
    return JSONResponse({
        "INPUT_SAMPLE_RATE": audio_config.INPUT_SAMPLE_RATE,
        "OUTPUT_SAMPLE_RATE": audio_config.OUTPUT_SAMPLE_RATE,
        "K4_FRAME_SIZE": audio_config.K4_FRAME_SIZE,  # Legacy RX frame size
        "K4_TX_FRAME_SIZE": audio_config.K4_TX_FRAME_SIZE,  # New TX frame size
        "K4_RX_FRAME_SIZE": audio_config.K4_RX_FRAME_SIZE,  # Explicit RX frame size
        "WORKLET_FRAME_SIZE": audio_config.WORKLET_FRAME_SIZE,
        "DEFAULT_MODE": audio_config.DEFAULT_MODE,
        "DEFAULT_MIC_GAIN": audio_config.DEFAULT_MIC_GAIN,
        "K4_ATTENUATION_FACTOR": audio_config.K4_ATTENUATION_FACTOR,
        "DEFAULT_BUFFER_SIZE": web_config.DEFAULT_BUFFER_SIZE,
        "DEFAULT_MASTER_VOLUME": web_config.DEFAULT_MASTER_VOLUME
    })

@app.get("/api/config/all")
async def get_all_configuration():
    """Return complete application configuration for frontend initialization
    
    This endpoint provides a comprehensive configuration object that can be used
    by the frontend to eliminate hardcoded values. All existing functionality
    remains unchanged - this is purely additive for future use.
    """
    try:
        return {
            "audio": {
                "mic_gain": audio_config.DEFAULT_MIC_GAIN,
                "input_sample_rate": audio_config.INPUT_SAMPLE_RATE,
                "output_sample_rate": audio_config.OUTPUT_SAMPLE_RATE,
                "frame_size": audio_config.K4_FRAME_SIZE,
                "volume": {
                    "user_min": web_config.VOLUME_USER_MIN,
                    "user_max": web_config.VOLUME_USER_MAX,
                    "internal_max": web_config.VOLUME_INTERNAL_MAX,
                    "master_internal_max": web_config.VOLUME_MASTER_INTERNAL_MAX,
                    "default_main": web_config.DEFAULT_USER_MAIN_VOLUME,
                    "default_sub": web_config.DEFAULT_USER_SUB_VOLUME,
                    "default_master": web_config.DEFAULT_USER_MASTER_VOLUME
                }
            },
            "network": {
                "k4_host": k4_config.DEFAULT_HOST,
                "k4_port": k4_config.DEFAULT_PORT,
                "web_port": web_config.DEFAULT_PORT,
                "keepalive_interval": k4_config.KEEPALIVE_INTERVAL
            },
            "vfo": {
                "freq_min": web_config.VFO_FREQ_MIN,
                "freq_max": web_config.VFO_FREQ_MAX
            },
            "panadapter": {
                "center_freq": pan_config.DEFAULT_CENTER_FREQ,
                "span": pan_config.DEFAULT_SPAN,
                "ref_level": pan_config.DEFAULT_REF_LEVEL,
                "scale": pan_config.DEFAULT_SCALE,
                "noise_floor": pan_config.DEFAULT_NOISE_FLOOR,
                "waterfall_height": pan_config.DEFAULT_WATERFALL_HEIGHT,
                "waterfall_lines": pan_config.MAX_WATERFALL_LINES,
                "spectrum_averaging": pan_config.DEFAULT_SPECTRUM_AVERAGING,
                "waterfall_averaging": pan_config.DEFAULT_WATERFALL_AVERAGING,
                "waterfall_thresholds": {
                    "pink": pan_config.WATERFALL_PINK_THRESHOLD,
                    "orange": pan_config.WATERFALL_ORANGE_THRESHOLD,
                    "green": pan_config.WATERFALL_GREEN_THRESHOLD,
                    "blue": pan_config.WATERFALL_BLUE_THRESHOLD,
                    "royal": pan_config.WATERFALL_ROYAL_THRESHOLD,
                    "black": pan_config.WATERFALL_BLACK_THRESHOLD
                }
            },
            "modes": {
                "cat_mode_map": CAT_MODE_MAP
            },
            "version": "1.0.0",
            "timestamp": int(time.time())
        }
    except Exception as e:
        # Fallback response if any config module has issues
        print(f"⚠️ Configuration API error: {e}")
        return {
            "error": "Configuration unavailable",
            "fallback": True,
            "audio": {"mic_gain": 0.1},
            "network": {"k4_host": "192.168.1.10", "k4_port": 9205},
            "panadapter": {"center_freq": 14086500, "span": 50000}
        }

# Radio Management API Endpoints

@app.get("/api/radios")
async def get_all_radios():
    """Get all configured radios"""
    radio_manager = get_radio_manager()
    radios = radio_manager.get_all_radios()
    active_id = radio_manager.get_active_radio_id()
    
    return {
        "radios": {radio_id: radio.to_dict() for radio_id, radio in radios.items()},
        "active_radio_id": active_id,
        "total_count": len(radios)
    }

@app.get("/api/radios/active")
async def get_active_radio():
    """Get the currently active radio configuration"""
    active_radio = get_current_radio_config()
    radio_manager = get_radio_manager()
    
    if active_radio:
        return {
            "radio_id": radio_manager.get_active_radio_id(),
            "config": active_radio.to_dict()
        }
    else:
        return {"error": "No active radio configured"}, 404

@app.post("/api/radios")
async def create_radio(radio_data: dict):
    """Create a new radio configuration"""
    radio_manager = get_radio_manager()
    
    # Validate required fields
    required_fields = ["name", "host", "port", "password"]
    for field in required_fields:
        if field not in radio_data:
            return {"error": f"Missing required field: {field}"}, 400
    
    try:
        radio_id = radio_manager.add_radio(
            name=radio_data["name"],
            host=radio_data["host"],
            port=int(radio_data["port"]),
            password=radio_data["password"],
            description=radio_data.get("description", ""),
            enabled=radio_data.get("enabled", True)
        )
        
        radio = radio_manager.get_radio(radio_id)
        return {
            "message": "Radio created successfully",
            "radio_id": radio_id,
            "config": radio.to_dict()
        }
        
    except Exception as e:
        return {"error": f"Failed to create radio: {str(e)}"}, 500

@app.put("/api/radios/{radio_id}")
async def update_radio(radio_id: str, radio_data: dict):
    """Update an existing radio configuration"""
    radio_manager = get_radio_manager()
    
    if not radio_manager.get_radio(radio_id):
        return {"error": "Radio not found"}, 404
    
    try:
        success = radio_manager.update_radio(radio_id, **radio_data)
        if success:
            radio = radio_manager.get_radio(radio_id)
            return {
                "message": "Radio updated successfully",
                "radio_id": radio_id,
                "config": radio.to_dict()
            }
        else:
            return {"error": "Failed to update radio"}, 500
            
    except Exception as e:
        return {"error": f"Failed to update radio: {str(e)}"}, 500

@app.delete("/api/radios/{radio_id}")
async def delete_radio(radio_id: str):
    """Delete a radio configuration"""
    radio_manager = get_radio_manager()
    
    if not radio_manager.get_radio(radio_id):
        return {"error": "Radio not found"}, 404
    
    success = radio_manager.remove_radio(radio_id)
    if success:
        return {"message": "Radio deleted successfully"}
    else:
        return {"error": "Cannot delete the only remaining radio"}, 400

@app.post("/api/radios/{radio_id}/activate")
async def activate_radio(radio_id: str):
    """Set a radio as the active radio"""
    radio_manager = get_radio_manager()
    
    if not radio_manager.get_radio(radio_id):
        return {"error": "Radio not found"}, 404
    
    success = radio_manager.set_active_radio(radio_id)
    if success:
        radio = radio_manager.get_radio(radio_id)
        return {
            "message": "Radio activated successfully",
            "radio_id": radio_id,
            "config": radio.to_dict()
        }
    else:
        return {"error": "Failed to activate radio"}, 500

@app.websocket("/ws")
async def websocket_handler(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        await k4_tcp_reader(ws)
    except WebSocketDisconnect:
        pass  # Normal disconnection
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if ws in clients:
            clients.remove(ws)



if __name__ == "__main__":
    import uvicorn
    
    print("Starting K4 Web Control Server...")
    
    if os.path.exists("certs/cert.pem") and os.path.exists("certs/key.pem"):
        print(f"HTTPS server starting on port {web_config.DEFAULT_PORT}")
        uvicorn.run(app, host="0.0.0.0", port=web_config.DEFAULT_PORT, ssl_keyfile="certs/key.pem", ssl_certfile="certs/cert.pem")
    else:
        print(f"HTTP server starting on port {web_config.DEFAULT_PORT}")
        uvicorn.run(app, host="0.0.0.0", port=web_config.DEFAULT_PORT)