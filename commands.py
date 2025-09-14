"""
K4 Commands Module - Audio Packet Formatting

This module handles packet wrapping and formatting for K4 radio communication.
Implements proper K4 protocol packet structure for audio transmission.

Key features:
1. Frame size optimized for K4 audio transmission (240 samples per channel)
2. Proper binary packet structure for K4 protocol
3. Correct sequence number handling
"""

import struct
import numpy as np

# Import centralized configuration
from config import audio_config, k4_config, AudioMode, CAT_MODE_MAP

# Import debug helper for controlled debugging
from debug_helper import debug_print

# Audio encoder not needed in commands.py

# Use config values instead of hardcoded ones
START_MARKER = k4_config.START_MARKER
END_MARKER = k4_config.END_MARKER

def wrap_cat_command(command: str) -> bytes:
    """Wraps a CAT command in the required K4 packet format."""
    payload = b'\x00\x00\x00' + command.encode("ascii")
    length = struct.pack(">I", len(payload))
    return START_MARKER + length + payload + END_MARKER


def wrap_audio_packet(audio_data: bytes, mode: int = None, frame_size: int = None, sample_rate: int = 0, sequence: int = 0) -> bytes:
    """
    Wraps audio data in the required K4 packet format for transmission.
    Optimized for K4 radio protocol transmission.
    
    Args:
        audio_data: Raw audio data bytes (encoded audio for mode 3)
        mode: Audio mode (defaults to config value)
        frame_size: Number of samples per channel (defaults to config value)
        sample_rate: Sample rate (0 = 12000 Hz default)
        sequence: 8-bit sequence number (wraps)
    
    Returns:
        Complete K4 audio packet ready for transmission
    """
    # Use config defaults if not specified
    if mode is None:
        mode = audio_config.DEFAULT_MODE
    if frame_size is None:
        frame_size = audio_config.K4_FRAME_SIZE
    
    # Audio payload header based on K4 protocol documentation:
    # Byte 0: TYPE = 1 (Audio)
    # Byte 1: VER = 1 (Version)  
    # Byte 2: SEQ = sequence number
    # Byte 3: MODE = audio encoding mode
    # Bytes 4-5: Frame size (little-endian short) - SAMPLES PER CHANNEL
    # Byte 6: Sample rate (0 = 12000 Hz)
    # Byte 7+: Audio data
    
    # Create payload with proper K4 protocol format
    payload = struct.pack('<BBBBBBB', 
                         1,                          # TYPE = 1 (Audio)
                         1,                          # VER = 1
                         sequence & 0xFF,            # SEQ (8-bit, wraps)
                         mode,                       # MODE (3 = EM3 Opus Float)
                         frame_size & 0xFF,          # Frame size low byte
                         (frame_size >> 8) & 0xFF,   # Frame size high byte
                         sample_rate                 # Sample rate (0 = 12000 Hz)
                         ) + audio_data
    
    length = struct.pack(">I", len(payload))
    packet = START_MARKER + length + payload + END_MARKER
    
    debug_print("AUDIO", f"📦 K4 audio packet: mode={mode}, frame_size={frame_size}, seq={sequence}, data_len={len(audio_data)}")
    return packet


def wrap_audio_packet_batch(encoded_frames: list, mode: int = None, frame_size: int = None, sequence_start: int = 0) -> list:
    """
    Wraps multiple encoded audio frames into K4 protocol packets.
    
    Creates a batch of properly formatted K4 audio packets for continuous transmission.
    
    Args:
        encoded_frames: List of encoded audio data bytes
        mode: Audio mode (defaults to config value)
        frame_size: Samples per channel (defaults to config value)
        sequence_start: Starting sequence number
        
    Returns:
        List of complete K4 audio packets ready for transmission
    """
    if mode is None:
        mode = audio_config.DEFAULT_MODE
    if frame_size is None:
        frame_size = audio_config.K4_FRAME_SIZE
        
    packets = []
    
    for i, frame_data in enumerate(encoded_frames):
        sequence = (sequence_start + i) & 0xFF  # 8-bit wraparound
        packet = wrap_audio_packet(
            audio_data=frame_data,
            mode=mode,
            frame_size=frame_size,
            sample_rate=0,  # 0 = 12000 Hz default
            sequence=sequence
        )
        packets.append(packet)
    
    debug_print("AUDIO", f"📦 Created {len(packets)} K4 audio packets")
    return packets


def format_frequency(freq_str: str) -> str:
    """Formats a raw frequency string (e.g. 07058000) into readable format (e.g. 7.058.000)."""
    try:
        freq = int(freq_str)
        mhz = freq // 1_000_000
        khz = (freq % 1_000_000) // 1000
        hz = freq % 1000
        return f"{mhz}.{khz:03}.{hz:03}"
    except ValueError:
        return freq_str


def parse_frequency(formatted_freq: str) -> str:
    """Parses a formatted frequency string back to raw format for K4 commands."""
    try:
        # Remove dots and convert to integer
        raw_freq = formatted_freq.replace(".", "")
        freq = int(raw_freq)
        # Pad to 8 digits for K4 format
        return f"{freq:08d}"
    except ValueError:
        return formatted_freq


def create_k4_cat_command(command: str, value: str = "") -> str:
    """
    Creates a properly formatted K4 CAT command.
    
    Args:
        command: The base command (e.g., "FA", "FB", "MD")
        value: Optional value to set
        
    Returns:
        Formatted CAT command string
    """
    if value:
        return f"{command}{value};"
    else:
        return f"{command};"


def validate_audio_packet_structure(packet_data: bytes) -> dict:
    """
    Validates an audio packet structure against K4 protocol standards.
    
    Args:
        packet_data: Raw packet bytes
        
    Returns:
        Dictionary with validation results
    """
    try:
        if len(packet_data) < 12:  # Minimum packet size
            return {'valid': False, 'error': 'Packet too short'}
        
        # Check start marker
        if packet_data[:4] != START_MARKER:
            return {'valid': False, 'error': 'Invalid start marker'}
        
        # Extract length
        length = struct.unpack(">I", packet_data[4:8])[0]
        
        # Check end marker
        if packet_data[-4:] != END_MARKER:
            return {'valid': False, 'error': 'Invalid end marker'}
        
        # Extract payload
        payload = packet_data[8:-4]
        
        if len(payload) != length:
            return {'valid': False, 'error': f'Length mismatch: expected {length}, got {len(payload)}'}
        
        if len(payload) < 7:
            return {'valid': False, 'error': 'Audio payload too short'}
        
        # Parse audio header
        type_byte = payload[0]
        version = payload[1]
        sequence = payload[2]
        mode = payload[3]
        frame_size = struct.unpack("<H", payload[4:6])[0]
        sample_rate = payload[6] if len(payload) > 6 else 0
        audio_data = payload[7:]
        
        if type_byte != 1:
            return {'valid': False, 'error': f'Not an audio packet: type={type_byte}'}
        
        # Check K4 protocol standards
        warnings = []
        if frame_size not in [audio_config.K4_TX_FRAME_SIZE, audio_config.K4_RX_FRAME_SIZE]:
            warnings.append(f'Non-standard frame size: {frame_size} (expected {audio_config.K4_TX_FRAME_SIZE} for TX or {audio_config.K4_RX_FRAME_SIZE} for RX)')
        
        if mode not in [0, 1, 2, 3]:
            warnings.append(f'Unknown audio mode: {mode}')
        
        return {
            'valid': True,
            'type': type_byte,
            'version': version,
            'sequence': sequence,
            'mode': mode,
            'mode_name': AudioMode.get_name(mode),
            'frame_size': frame_size,
            'sample_rate': sample_rate,
            'data_length': len(audio_data),
            'warnings': warnings
        }
        
    except Exception as e:
        return {'valid': False, 'error': f'Parsing error: {e}'}


def parse_cat_command(cat_text: str) -> dict:
    """
    Parse CAT command text and extract useful information for the web interface.
    DEPRECATED: Use k4_commands.get_command_handler() for new code.
    
    Args:
        cat_text: Raw CAT command text (e.g., "FA07058000;")
        
    Returns:
        Dictionary with parsed command information
    """
    # Redirect to new command system for backward compatibility
    try:
        from k4_commands import get_command_handler
        handler = get_command_handler()
        parsed = handler.parse_command(cat_text)
        if parsed:
            return handler.create_ui_update(parsed)
        return {}
    except ImportError:
        # Fallback to old implementation if k4_commands not available
        debug_print("CRITICAL", "k4_commands module not available, using legacy parser")
        return _legacy_parse_cat_command(cat_text)


def _legacy_parse_cat_command(cat_text: str) -> dict:
    """Legacy CAT command parser - kept for fallback"""
    try:
        cmd_clean = cat_text.strip().rstrip(';')
        if not cmd_clean:
            return {}
        
        updates = {}
        
        # Frequency commands
        if cmd_clean.startswith('FA') and len(cmd_clean) > 2:
            freq_str = cmd_clean[2:]
            if freq_str.isdigit():
                updates['vfo_a_freq'] = format_frequency(freq_str)
                updates['vfo_a_freq_hz'] = int(freq_str)
        
        elif cmd_clean.startswith('FB') and len(cmd_clean) > 2:
            freq_str = cmd_clean[2:]
            if freq_str.isdigit():
                updates['vfo_b_freq'] = format_frequency(freq_str)
                updates['vfo_b_freq_hz'] = int(freq_str)
        
        elif cmd_clean.startswith('FI') and len(cmd_clean) > 2:
            freq_str = cmd_clean[2:]
            if freq_str.isdigit():
                updates['if_center_freq'] = format_frequency(freq_str)
                updates['if_center_freq_hz'] = int(freq_str)
        
        # Mode commands - separate VFO A and VFO B
        elif cmd_clean.startswith('MD$') and len(cmd_clean) > 3:
            # VFO B mode (sub receiver)
            mode_code = cmd_clean[3:]
            updates['mode_b'] = CAT_MODE_MAP.get(mode_code, f'Mode {mode_code}')
        elif cmd_clean.startswith('MD') and len(cmd_clean) > 2:
            # VFO A mode (main receiver)
            mode_code = cmd_clean[2:]
            updates['mode_a'] = CAT_MODE_MAP.get(mode_code, f'Mode {mode_code}')
        
        # Audio commands - separate main and sub AF gain
        elif cmd_clean.startswith('AG$') and len(cmd_clean) > 3:
            # Sub AF gain
            gain = cmd_clean[3:]
            if gain.isdigit():
                updates['af_gain_sub'] = int(gain)
        elif cmd_clean.startswith('AG') and len(cmd_clean) > 2:
            # Main AF gain
            gain = cmd_clean[2:]
            if gain.isdigit():
                updates['af_gain_main'] = int(gain)
        
        # Sub receiver commands
        elif cmd_clean.startswith('SB') and len(cmd_clean) > 2:
            # Sub receiver state (SB0 = off, SB1 = on)
            state = cmd_clean[2:]
            if state in ['0', '1']:
                updates['sub_receiver_enabled'] = (state == '1')
        
        elif cmd_clean.startswith('EM') and len(cmd_clean) > 2:
            mode = cmd_clean[2:]
            updates['audio_encoding'] = AudioMode.get_name(int(mode))
        
        # Panadapter commands
        elif cmd_clean.startswith('#SPN') and len(cmd_clean) > 4:
            span = cmd_clean[4:]
            if span.isdigit():
                updates['pan_span'] = int(span)
        
        elif cmd_clean.startswith('#REF') and len(cmd_clean) > 4:
            ref = cmd_clean[4:]
            if ref.lstrip('-').isdigit():
                updates['pan_ref_level'] = int(ref)
        
        # State/control commands
        elif cmd_clean == 'RDY':
            updates['radio_ready'] = True
        
        elif cmd_clean.startswith('AI') and len(cmd_clean) > 2:
            ai_mode = cmd_clean[2:]
            updates['auto_info'] = ai_mode == '1'
        
        return updates
        
    except Exception as e:
        debug_print("CRITICAL", f"❌ Error parsing CAT command '{cat_text}': {e}")
        return {}


debug_print("GENERAL", "📡 K4 Commands module loaded with centralized configuration")