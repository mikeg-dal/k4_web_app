"""
K4 TCP Connection Handler - Radio Communication

Optimized for K4 radio protocol communication with proper frame sizing.
Uses 240 samples per channel for TX and 480 for RX to match K4 requirements.

Key feature: Separate TX/RX frame sizes optimized for K4 radio timing.
"""

import asyncio
import logging
import time
from fastapi import WebSocket, WebSocketDisconnect
from auth import get_sha384_hash
from commands import wrap_cat_command, wrap_audio_packet
from k4_commands import get_command_handler
from audio.encoder import encode_audio_for_k4_continuous
from packet_handler import handle_packet, handle_websocket_message

# Import centralized configuration
from config import k4_config, audio_config, web_config

# Import radio configuration for multi-radio support
from radios.radio_config import get_current_k4_connection_params, get_radio_manager

# Import debug helper for controlled debugging
from debug_helper import debug_print, is_debug_enabled
START_MARKER = k4_config.START_MARKER
END_MARKER = k4_config.END_MARKER

# Global sequence counter for TX audio packets
tx_audio_sequence = 0

# PTT state is managed by the frontend - we just respond to audio packets
ptt_active = False
last_ptt_time = 0


async def emergency_rx_command(writer):
    """Send RX command in emergency situations (connection loss, errors, etc.)"""
    if writer and not writer.is_closing():
        try:
            writer.write(wrap_cat_command("RX;"))
            await writer.drain()
            debug_print("CRITICAL", "🚨 Emergency RX command sent")
            global ptt_active
            ptt_active = False
        except Exception as e:
            debug_print("CRITICAL", f"❌ Failed to send emergency RX: {e}")

async def k4_tcp_reader(ws: WebSocket):
    """Main K4 connection handler with proper frame size matching"""
    # Get current radio configuration
    radio_params = get_current_k4_connection_params()
    radio_manager = get_radio_manager()
    
    # Ensure we have at least a default radio
    radio_manager.create_default_radio_if_none()
    
    k4_host = radio_params["host"]
    k4_port = radio_params["port"] 
    password = radio_params["password"]
    
    reader = None
    writer = None
    
    try:
        debug_print("NETWORK", f"🔗 Connecting to K4 at {k4_host}:{k4_port}...")
        reader, writer = await asyncio.open_connection(k4_host, k4_port)
        debug_print("NETWORK", "✅ Connected to K4")

        # Step 1: Authentication
        auth_hash = get_sha384_hash(password)
        writer.write(auth_hash)
        await writer.drain()
        debug_print("NETWORK", "🔐 Sent authentication")

        # Step 2: Send initial commands from config
        for cmd in k4_config.INIT_COMMANDS:
            writer.write(wrap_cat_command(cmd))
            await writer.drain()
            await asyncio.sleep(0.1)
        
        debug_print("GENERAL", f"📻 K4 initialized with EM{audio_config.DEFAULT_MODE} ({audio_config.DEFAULT_MODE}) mode")

        # Step 3: Keep alive task
        async def keep_alive():
            while True:
                try:
                    await asyncio.sleep(k4_config.KEEPALIVE_INTERVAL)
                    if writer and not writer.is_closing():
                        writer.write(wrap_cat_command("PING;"))
                        await writer.drain()
                except Exception as e:
                    debug_print("CRITICAL", f"❌ Keep alive error: {e}")
                    break

        # Step 4: WebSocket reader with proper frame size handling
        async def ws_reader():
            consecutive_errors = 0
            message_counter = 0
            
            try:
                while True:
                    try:
                        # Use receive() to handle any data type without forcing text/binary
                        message = await ws.receive()
                        consecutive_errors = 0  # Reset error counter on successful receive
                        message_counter += 1
                        
                        # Handle based on actual message type
                        if message["type"] == "websocket.receive":
                            
                            if "text" in message:
                                if message["text"]:
                                    # Handle non-empty text messages (CAT commands, controls)
                                    text_data = message["text"]
                                    
                                    # Try to handle as audio control first
                                    if await handle_websocket_message(ws, text_data, writer):
                                        continue  # Audio control handled, continue loop
                                else:
                                    debug_print("CRITICAL", f"🚨 MSG#{message_counter} EMPTY TEXT MESSAGE! Full: {message}")
                                    continue
                                
                                # Handle as regular CAT command
                                if text_data == "DISCONNECT":
                                    debug_print("NETWORK", "🔌 Client requested disconnect")
                                    await emergency_rx_command(writer)
                                    # Properly close connections
                                    try:
                                        await ws.close()
                                    except:
                                        pass
                                    if writer:
                                        try:
                                            writer.close()
                                            await writer.wait_closed()
                                        except:
                                            pass
                                    return
                                    
                                elif text_data.endswith(";"):  # send raw CAT
                                    if writer and not writer.is_closing():
                                        # Block TX/RX commands - let audio packets control TX state
                                        if text_data == "TX;":
                                            global ptt_active, last_ptt_time
                                            ptt_active = True
                                            last_ptt_time = time.time()
                                            # Don't send the TX command - let audio packets trigger TX
                                        elif text_data == "RX;":
                                            ptt_active = False
                                            # Don't send the RX command - let lack of audio packets trigger RX
                                        else:
                                            # Use new command system for validation and tracking
                                            command_handler = get_command_handler()
                                            parsed_command = command_handler.parse_command(text_data)
                                            
                                            if parsed_command:
                                                # Command is valid, send it
                                                writer.write(wrap_cat_command(text_data))
                                                await writer.drain()
                                                command_handler.add_to_history(text_data, "sent")
                                            else:
                                                # Invalid command, log warning but send anyway for backward compatibility
                                                writer.write(wrap_cat_command(text_data))
                                                await writer.drain()
                                    else:
                                        debug_print("CRITICAL", "❌ Cannot send CAT command - K4 connection closed")
                                        
                            elif "bytes" in message and message["bytes"]:
                                # Handle binary audio data with proper frame size handling
                                audio_data = message["bytes"]
                                
                                # Get audio frames with correct frame size information
                                audio_result = encode_audio_for_k4_continuous(audio_data)
                                encoded_frames = audio_result.get('frames', [])
                                timing_info = audio_result.get('timing', {})
                                
                                # Use TX frame size from encoder result (240 samples for K4)
                                encoder_frame_size = audio_result.get('k4_frame_size', audio_config.K4_TX_FRAME_SIZE)
                                
                                if encoded_frames and writer and not writer.is_closing():
                                    global tx_audio_sequence
                                    
                                    # Send all frames immediately (no delays - AudioWorklet provides timing)
                                    for i, frame_data in enumerate(encoded_frames):
                                        tx_audio_sequence = (tx_audio_sequence + 1) % 256
                                        
                                        # Use TX frame size from encoder (240 samples - K4 verified)
                                        audio_packet = wrap_audio_packet(
                                            frame_data, 
                                            mode=audio_config.DEFAULT_MODE,  # EM3 = Opus Float
                                            frame_size=encoder_frame_size,  # TX frame size for K4
                                            sequence=tx_audio_sequence
                                        )
                                        
                                        # Send to K4 immediately
                                        writer.write(audio_packet)
                                        await writer.drain()
                                    
                                elif not encoded_frames:
                                    debug_print("CRITICAL", "⚠️ AudioWorklet audio processing returned empty result")
                        
                        elif message["type"] == "websocket.disconnect":
                            debug_print("NETWORK", "🚨 WebSocket disconnected (browser closed)")
                            break
                            
                    except WebSocketDisconnect:
                        debug_print("NETWORK", "🚨 WebSocket disconnected (browser closed)")
                        break
                        
                    except Exception as e:
                        consecutive_errors += 1
                        debug_print("CRITICAL", f"❌ WebSocket error #{consecutive_errors}: {e}")
                        
                        # If too many consecutive errors, assume connection is dead
                        if consecutive_errors >= web_config.WS_MAX_ERRORS:
                            debug_print("CRITICAL", f"🚨 Too many consecutive errors ({consecutive_errors}), assuming connection is dead")
                            break
                            
            except Exception as e:
                debug_print("CRITICAL", f"❌ WebSocket reader error: {e}")
            finally:
                # CRITICAL: Always send RX command when WebSocket reader exits
                debug_print("CRITICAL", "🚨 WebSocket reader exiting - ensuring radio returns to RX")
                await emergency_rx_command(writer)

        # Step 5: TCP read loop from K4
        async def tcp_reader():
            buffer = b""
            try:
                while reader and not reader.at_eof():
                    try:
                        data = await asyncio.wait_for(reader.read(4096), timeout=k4_config.CONNECTION_TIMEOUT)
                        if not data:
                            debug_print("CRITICAL", "❌ Connection closed by K4")
                            break
                        buffer += data
                        while START_MARKER in buffer and END_MARKER in buffer:
                            start = buffer.index(START_MARKER)
                            end = buffer.index(END_MARKER) + 4
                            packet = buffer[start:end]
                            buffer = buffer[end:]
                            
                            # Only process packets if websocket is still connected
                            try:
                                if ws.client_state.CONNECTED:
                                    await handle_packet(packet, ws)
                            except Exception as e:
                                debug_print("CRITICAL", f"❌ Error processing packet: {e}")
                                # Don't break here - keep processing K4 data
                                
                    except asyncio.TimeoutError:
                        debug_print("NETWORK", f"⚠️ No data from K4 for {k4_config.CONNECTION_TIMEOUT} seconds - checking connection")
                        continue
                        
            except Exception as e:
                debug_print("CRITICAL", f"❌ TCP reader error: {e}")

        # Run all tasks concurrently with proper exception handling
        try:
            tasks = [
                asyncio.create_task(ws_reader()),
                asyncio.create_task(tcp_reader()), 
                asyncio.create_task(keep_alive())
            ]
            
            # Wait for any task to complete or fail
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            debug_print("CRITICAL", f"❌ Error in concurrent tasks: {e}")
        finally:
            # CRITICAL: Emergency RX on any exit path
            await emergency_rx_command(writer)

    except Exception as e:
        debug_print("CRITICAL", f"❌ TCP connection failed or closed: {e}")
    finally:
        # Cleanup with MANDATORY RX command
        debug_print("GENERAL", "🧹 Cleaning up connections...")
        if writer:
            try:
                # CRITICAL: Always send RX command to ensure radio safety
                if not writer.is_closing():
                    writer.write(wrap_cat_command("RX;"))
                    await writer.drain()
                    debug_print("CRITICAL", "📻 Sent final RX; command for safety")
                    ptt_active = False
            except Exception as cleanup_error:
                debug_print("CRITICAL", f"⚠️ Error during RX cleanup: {cleanup_error}")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as close_error:
                debug_print("CRITICAL", f"⚠️ Error closing writer: {close_error}")
        debug_print("GENERAL", "✅ Cleanup complete - radio should be in RX mode")