"""
K4 Packet Handler Module - Clean Version
Processes incoming K4 packets (CAT, audio, panadapter), routes to WebSocket clients

CLEANED VERSION: Using centralized debug_helper for all logging
"""

import struct
import json
import time
from fastapi import WebSocket

# Import centralized configuration
from config import k4_config, PacketType

# Import debug helper for controlled debugging
from debug_helper import debug_print, is_debug_enabled

# Import command parser
from k4_commands import get_command_handler

# Keep all your existing imports exactly as they are
try:
    from audio.decoder import decode_opus_float
    from audio.controls import set_main_volume, set_sub_volume, set_sub_receiver_enabled, set_audio_routing, get_audio_settings
    from config import CAT_MODE_MAP
    debug_print("GENERAL", "✅ Audio modules imported successfully")
except ImportError as e:
    debug_print("CRITICAL", f"❌ Error importing audio modules: {e}")
    def decode_opus_float(payload): return b""
    def set_main_volume(vol): pass
    def set_sub_volume(vol): pass  
    def set_sub_receiver_enabled(enabled): pass
    def set_audio_routing(routing): pass
    def get_audio_settings(): return {}

try:
    from panadapter import get_panadapter, handle_panadapter_command
    debug_print("GENERAL", "✅ Panadapter module imported successfully")
except ImportError as e:
    debug_print("CRITICAL", f"❌ Error importing panadapter module: {e}")
    def get_panadapter():
        class DummyPanadapter:
            def process_pan_packet(self, payload): return None
            def process_mini_pan_packet(self, payload): return None
        return DummyPanadapter()
    def handle_panadapter_command(cmd): return False

# Use config values instead of redefining
START_MARKER = k4_config.START_MARKER
END_MARKER = k4_config.END_MARKER

# Keep all your existing counters
pan_packet_count = 0
mini_pan_packet_count = 0
spectrum_data_sent_count = 0
cat_packet_count = 0
audio_packet_count = 0

def is_websocket_connected(ws: WebSocket) -> bool:
    """Check if WebSocket is still connected and can receive messages"""
    try:
        return hasattr(ws, 'client_state') and ws.client_state.value == 1
    except Exception:
        return False

async def safe_send_text(ws: WebSocket, data: str) -> bool:
    """Safely send text data to WebSocket with connection checking"""
    try:
        if is_websocket_connected(ws):
            await ws.send_text(data)
            return True
        else:
            debug_print("NETWORK", "⚠️ WebSocket not connected, skipping send")
            return False
    except Exception as e:
        debug_print("CRITICAL", f"❌ WebSocket send failed: {e}")
        return False

async def safe_send_bytes(ws: WebSocket, data: bytes) -> bool:
    """Safely send binary data to WebSocket with connection checking"""
    try:
        if is_websocket_connected(ws):
            await ws.send_bytes(data)
            return True
        else:
            debug_print("NETWORK", "⚠️ WebSocket not connected, skipping send")
            return False
    except Exception as e:
        debug_print("CRITICAL", f"❌ WebSocket send failed: {e}")
        return False

async def handle_packet(packet: bytes, ws: WebSocket):
    """
    Packet handler with PAN DATA PRIORITY for broad spectrum monitoring
    """
    global pan_packet_count, mini_pan_packet_count, spectrum_data_sent_count
    global cat_packet_count, audio_packet_count
    
    if not packet.startswith(START_MARKER) or not packet.endswith(END_MARKER):
        debug_print("CRITICAL", "❌ Invalid packet boundary")
        return

    try:
        length = struct.unpack(">I", packet[4:8])[0]
        payload = packet[8:8 + length]
        if not payload:
            debug_print("CRITICAL", "❌ Empty payload")
            return

        pkt_type = payload[0]
        

        if pkt_type == PacketType.CAT:  # CAT COMMAND
            cat_packet_count += 1
            try:
                text = payload[3:].decode("ascii")
                
                # Process command with old handler approach
                updates = {}
                
                # Simple command parsing for UI updates
                if text.strip():
                    debug_print("CAT", f"📡 RX: {text.strip()}")
                
                
                handle_panadapter_command(text)
                
                # CHECK FOR PENDING BOUNDARY UPDATES: Send immediately after CAT command
                if 'panadapter' in globals():
                    panadapter = get_panadapter()
                    pending_update = panadapter.get_pending_boundary_update()
                    if pending_update:
                        await send_boundary_update(ws, pending_update)
                
                success = await safe_send_text(ws, json.dumps({
                    "type": "cat", 
                    "text": text,
                    "updates": updates
                }))
                
                    
            except Exception as e:
                debug_print("CRITICAL", f"❌ CAT decode error: {e}")

        elif pkt_type == PacketType.AUDIO:  # AUDIO DATA
            audio_packet_count += 1
            
            try:
                audio_bytes = decode_opus_float(payload)
                
                if audio_bytes:
                    await safe_send_bytes(ws, audio_bytes)
                else:
                    debug_print("CRITICAL", "❌ Audio decode returned empty result")
                    
            except Exception as e:
                debug_print("CRITICAL", f"❌ Audio decoding error: {e}")

        elif pkt_type == PacketType.PAN:  # PAN DATA - PRIORITIZED FOR BROAD SPECTRUM
            pan_packet_count += 1
            
            try:
                panadapter = get_panadapter()
                spectrum_data = panadapter.process_pan_packet(payload)
                
                if spectrum_data:
                    try:
                        json_data = json.dumps(spectrum_data)
                        success = await safe_send_text(ws, json_data)
                        
                        if success:
                            spectrum_data_sent_count += 1
                        
                    except Exception as e:
                        debug_print("CRITICAL", f"❌ Failed to send PAN spectrum data: {e}")
                
                # Check for pending filter updates and send to UI
                filter_updates = panadapter.get_pending_filter_updates()
                if filter_updates:
                    for vfo, filter_data in filter_updates.items():
                        # Validate filter_data before sending
                        if filter_data is None:
                            debug_print("CRITICAL", f"❌ Filter data is None for VFO {vfo}")
                            continue
                            
                        filter_packet = {
                            'type': 'filter_update',
                            'vfo': vfo,
                            'filter_data': filter_data
                        }
                        try:
                            json_data = json.dumps(filter_packet)
                            await safe_send_text(ws, json_data)
                            debug_print("GENERAL", f"📡 Filter update sent: VFO {vfo} mode={filter_data.get('mode', 'unknown')}")
                        except Exception as e:
                            debug_print("CRITICAL", f"❌ Failed to send filter update for VFO {vfo}: {e}")
                            debug_print("CRITICAL", f"❌ Filter data was: {filter_data}")
                            import traceback
                            traceback.print_exc()
                else:
                    # debug_print("CRITICAL", "❌ PAN packet processing returned None")
                    pass
            except Exception as e:
                debug_print("CRITICAL", f"❌ PAN packet processing error: {e}")
                import traceback
                traceback.print_exc()

        elif pkt_type == PacketType.MINI_PAN:  # MINI-PAN DATA - DEPRIORITIZED FOR BROAD SPECTRUM MONITORING
            mini_pan_packet_count += 1

        else:
            debug_print("CRITICAL", f"❌ Unknown payload type: {pkt_type}")

    except Exception as e:
        debug_print("CRITICAL", f"❌ Packet handling error: {e}")
        import traceback
        traceback.print_exc()


# VFO Command Handlers - Centralized Protocol Logic
def format_frequency_command(vfo: str, frequency: int) -> str:
    """Format frequency command for K4 protocol"""
    freq_str = str(frequency).zfill(11)  # Pad to 11 digits
    return f"F{vfo}{freq_str};"

def format_mode_command(vfo: str, mode: str) -> str:
    """Format mode command for K4 protocol"""
    # Reverse lookup from mode name to code
    mode_to_code = {v: k for k, v in CAT_MODE_MAP.items()}
    mode_code = mode_to_code.get(mode.upper())
    if not mode_code:
        raise ValueError(f"Unknown mode: {mode}")
    
    if vfo.upper() == 'B':
        return f"MD${mode_code};"
    else:
        return f"MD{mode_code};"

def format_noise_command(vfo: str, noise_type: str, enabled: bool, level: int = 5, filter_val: int = 0) -> str:
    """Format noise control command for K4 protocol"""
    vfo_suffix = "$" if vfo.upper() == 'B' else ""
    
    if noise_type.upper() == 'NB':
        # Noise Blanker: NB[vfo]0LEM format (L=level, E=enabled, M=filter)
        enable_bit = "1" if enabled else "0"
        return f"NB{vfo_suffix}0{level}{enable_bit}{filter_val};"
    elif noise_type.upper() == 'NR':
        # Noise Reduction: NR[vfo]nnm format (nn=level, m=enabled)
        enable_bit = "1" if enabled else "0"
        level_str = str(level).zfill(2)
        return f"NR{vfo_suffix}{level_str}{enable_bit};"
    else:
        raise ValueError(f"Unknown noise type: {noise_type}")

def format_sub_rx_command() -> str:
    """Format Sub RX toggle command"""
    return "SB/;"

async def handle_vfo_command(ws: WebSocket, action: str, data: dict, k4_writer) -> bool:
    """Handle VFO-related commands and send to K4"""
    try:
        if action == 'set_frequency':
            vfo = data.get('vfo', 'A').upper()
            frequency = data.get('frequency')
            if not frequency or not isinstance(frequency, int):
                raise ValueError("Invalid frequency")
            
            command = format_frequency_command(vfo, frequency)
            
        elif action == 'set_mode':
            vfo = data.get('vfo', 'A').upper()
            mode = data.get('mode')
            if not mode:
                raise ValueError("Invalid mode")
            
            command = format_mode_command(vfo, mode)
            
        elif action == 'set_noise_control':
            vfo = data.get('vfo', 'A').upper()
            noise_type = data.get('noise_type')  # 'NB' or 'NR'
            enabled = data.get('enabled', False)
            level = data.get('level', 5)
            filter_val = data.get('filter', 0)
            
            command = format_noise_command(vfo, noise_type, enabled, level, filter_val)
            
        elif action == 'toggle_sub_rx':
            command = format_sub_rx_command()
            
        else:
            debug_print("CRITICAL", f"❌ Unknown VFO action: {action}")
            return False
        
        # Send command to K4
        if k4_writer and not k4_writer.is_closing():
            from connection import wrap_cat_command
            wrapped_command = wrap_cat_command(command)
            k4_writer.write(wrapped_command)
            await k4_writer.drain()
            debug_print("GENERAL", f"📡 VFO Command sent: {command}")
            return True
        else:
            debug_print("CRITICAL", "❌ Cannot send VFO command - K4 connection closed")
            return False
            
    except Exception as e:
        debug_print("CRITICAL", f"❌ Error processing VFO command: {e}")
        return False

async def handle_filter_command(ws: WebSocket, action: str, data: dict, k4_writer) -> bool:
    """Handle Filter-related commands and send to K4"""
    try:
        vfo = data.get('vfo', 'A').upper()
        command = data.get('command', '')
        
        # VFO B always uses $ suffix regardless of SubRX status
        # SubRX only affects audio routing, not command syntax
        suffix = '$' if vfo == 'B' else ''
        
        if command.startswith('FP') and command.endswith(';'):
            # Query current filter: FP; or FP$;
            k4_command = f"FP{suffix};"
            
        elif command.startswith('FP') and command.endswith('+'):
            # Cycle filter: FP+ or FP$+
            k4_command = f"FP{suffix}+"
            
        elif action == 'update_filter_values':
            # Handle filter parameter updates - BW/SHFT mode only
            filter_state = data.get('filter_state', {})
            
            # Direct mapping BW/SHFT to BW/IS
            ui_bw = filter_state.get('bw', 3.00)
            ui_shft = filter_state.get('shft', 1.50)
            
            bw_value = round((ui_bw * 1000) / 10)
            is_value = round((ui_shft * 1000) / 10)
            
            # Send IS and BW commands
            commands = [
                f"IS{suffix}{is_value:04d};",
                f"BW{suffix}{bw_value:04d};"
            ]
            
            for k4_command in commands:
                if k4_writer and not k4_writer.is_closing():
                    from connection import wrap_cat_command
                    wrapped_command = wrap_cat_command(k4_command)
                    k4_writer.write(wrapped_command)
                    await k4_writer.drain()
                    debug_print("GENERAL", f"📡 Filter Command sent: {k4_command}")
                else:
                    debug_print("CRITICAL", "❌ Cannot send filter command - K4 connection closed")
                    return False
            
            return True
            
        else:
            debug_print("CRITICAL", f"❌ Unknown filter command: {command}")
            return False
        
        # Send single command to K4 (for FP commands)
        if k4_writer and not k4_writer.is_closing():
            from connection import wrap_cat_command
            wrapped_command = wrap_cat_command(k4_command)
            k4_writer.write(wrapped_command)
            await k4_writer.drain()
            debug_print("GENERAL", f"📡 Filter Command sent: {k4_command}")
            return True
        else:
            debug_print("CRITICAL", "❌ Cannot send filter command - K4 connection closed")
            return False
            
    except Exception as e:
        debug_print("CRITICAL", f"❌ Error processing filter command: {e}")
        return False

async def handle_websocket_message(ws: WebSocket, message: str, k4_writer=None) -> bool:
    """
    WebSocket message handler - JSON commands for audio controls and VFO operations
    """
    # Check for empty or invalid messages before processing  
    if not message or not message.strip():
        debug_print("CRITICAL", f"⚠️ Received empty WebSocket message (length: {len(message)}, repr: {repr(message)}) - this indicates a frontend bug")
        return False
    
    # ONLY process JSON messages (audio controls), skip CAT commands
    if not message.startswith('{'):
        return False  # Let CAT handler process this
    
    try:
        data = json.loads(message)
        
        if data.get('type') == 'audio_control':
            action = data.get('action')
            value = data.get('value')
            
            try:
                if action == 'set_main_volume':
                    set_main_volume(float(value))
                elif action == 'set_sub_volume':
                    set_sub_volume(float(value))
                elif action == 'set_sub_enabled':
                    set_sub_receiver_enabled(bool(value))
                elif action == 'set_audio_routing':
                    set_audio_routing(str(value))
                
                settings = get_audio_settings()
                await safe_send_text(ws, json.dumps({
                    'type': 'audio_settings',
                    'settings': settings
                }))
                
                return True
                
            except Exception as e:
                debug_print("CRITICAL", f"❌ Error processing audio control: {e}")
                return False
        
        elif data.get('type') == 'vfo_control':
            action = data.get('action')
            
            if await handle_vfo_command(ws, action, data, k4_writer):
                # Send success response
                await safe_send_text(ws, json.dumps({
                    'type': 'vfo_response',
                    'action': action,
                    'status': 'success'
                }))
                return True
            else:
                # Send error response
                await safe_send_text(ws, json.dumps({
                    'type': 'vfo_response',
                    'action': action,
                    'status': 'error'
                }))
                return False
        
        elif data.get('type') == 'filter_control':
            action = data.get('action')
            
            if await handle_filter_command(ws, action, data, k4_writer):
                # Send success response
                await safe_send_text(ws, json.dumps({
                    'type': 'filter_response',
                    'action': action,
                    'status': 'success'
                }))
                return True
            else:
                # Send error response
                await safe_send_text(ws, json.dumps({
                    'type': 'filter_response',
                    'action': action,
                    'status': 'error'
                }))
                return False
                
    except (json.JSONDecodeError, KeyError) as e:
        debug_print("CRITICAL", f"❌ Error parsing WebSocket message: {e}")
    
    return False

async def send_boundary_update(ws, boundaries: dict):
    """
    Send immediate boundary update to WebSocket client when span/center changes.
    This ensures the frontend updates its frequency display immediately.
    """
    try:
        if boundaries and ws:
            boundary_packet = {
                'type': 'boundary_update',
                'center_frequency': boundaries.get('center_frequency', 0),
                'span': boundaries.get('span', 0),
                'timestamp': boundaries.get('timestamp', time.time())
            }
            
            # Validate the packet before sending to prevent JSON errors
            # CORRUPTION FIX: Also check for valid span and frequency values
            if (all(isinstance(v, (int, float, str)) for v in boundary_packet.values()) and
                boundary_packet['span'] > 0 and 
                boundary_packet['center_frequency'] > 0):
                json_data = json.dumps(boundary_packet)
                await safe_send_text(ws, json_data)
                return True
            else:
                debug_print("CRITICAL", f"❌ Invalid boundary data: {boundary_packet}")
    except Exception as e:
        debug_print("CRITICAL", f"❌ Failed to send boundary update: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def get_packet_statistics():
    """Packet statistics - unchanged"""
    return {
        'cat_packets_received': cat_packet_count,
        'audio_packets_received': audio_packet_count,
        'pan_packets_received': pan_packet_count,
        'mini_pan_packets_received': mini_pan_packet_count,
        'spectrum_data_sent': spectrum_data_sent_count,
        'last_updated': time.time()
    }

# Module initialization 
debug_print("GENERAL", "📦 Packet handler loaded with PAN DATA PRIORITY for broad spectrum monitoring")
debug_print("GENERAL", "🔧 Changes made:")
debug_print("GENERAL", "   - PAN packets (Type=2) prioritized for display (broad spectrum ~71 bins)")
debug_print("GENERAL", "   - MINI-PAN packets (Type=3) processing disabled (too detailed ~1048 bins)")
debug_print("GENERAL", "   - Should improve performance and provide proper broad spectrum coverage")
debug_print("GENERAL", "   - WebSocket safety functions maintained")