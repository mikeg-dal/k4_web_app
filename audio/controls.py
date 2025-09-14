"""
K4 Audio Controls Module

This module handles audio control functions for volume, routing, and dual receiver settings.
All functions are moved exactly as-is from the working audio.py to maintain compatibility.
"""

# Import the decoder module to access the decode_opus_float function for attribute access
from . import decoder

# Import centralized configuration
from config import audio_config

def set_main_volume(volume):
    """Set VFO A / Main receiver volume (0.0 to 2.0)"""
    decoder.decode_opus_float.main_volume = max(0.0, min(2.0, volume))

def set_sub_volume(volume):
    """Set VFO B / Sub receiver volume (0.0 to 2.0)"""
    decoder.decode_opus_float.sub_volume = max(0.0, min(2.0, volume))

def set_sub_receiver_enabled(enabled):
    """Enable/disable sub receiver (VFO B audio)"""
    decoder.decode_opus_float.sub_enabled = bool(enabled)

def set_audio_routing(routing):
    """Set audio routing mode
    
    Args:
        routing (str): Audio routing pattern:
            'a.b'   - Main left, Sub right (default stereo)
            'ab.ab' - Mix both to both channels (mono)
            'a.-a'  - Main left, Main inverted right (binaural)
            'a.ab'  - Main left, Mix right
            'ab.b'  - Mix left, Sub right
            'ab.a'  - Mix left, Main right  
            'b.ab'  - Sub left, Mix right
            'b.b'   - Sub both channels
            'b.a'   - Sub left, Main right (swapped)
            'a.a'   - Main both channels
    """
    valid_patterns = ['a.b', 'ab.ab', 'a.-a', 'a.ab', 'ab.b', 'ab.a', 'b.ab', 'b.b', 'b.a', 'a.a']
    if routing in valid_patterns:
        decoder.decode_opus_float.audio_routing = routing
        print(f"🔀 Audio routing set to: {routing}")
    else:
        print(f"⚠️ Invalid audio routing: {routing}, using default '{audio_config.DEFAULT_AUDIO_ROUTING}'")
        decoder.decode_opus_float.audio_routing = audio_config.DEFAULT_AUDIO_ROUTING

def get_audio_settings():
    """Get current audio settings"""
    return {
        'main_volume': getattr(decoder.decode_opus_float, 'main_volume', audio_config.DEFAULT_MAIN_VOLUME),
        'sub_volume': getattr(decoder.decode_opus_float, 'sub_volume', audio_config.DEFAULT_SUB_VOLUME), 
        'sub_enabled': getattr(decoder.decode_opus_float, 'sub_enabled', audio_config.DEFAULT_SUB_ENABLED),
        'audio_routing': getattr(decoder.decode_opus_float, 'audio_routing', audio_config.DEFAULT_AUDIO_ROUTING)
    }

# Initialize default settings exactly as in original audio.py
# This ensures the decode_opus_float function has the required attributes
def _initialize_default_settings():
    """Initialize default audio control settings"""
    if not hasattr(decoder.decode_opus_float, 'main_volume'):
        decoder.decode_opus_float.main_volume = audio_config.DEFAULT_MAIN_VOLUME
    if not hasattr(decoder.decode_opus_float, 'sub_volume'):
        decoder.decode_opus_float.sub_volume = audio_config.DEFAULT_SUB_VOLUME
    if not hasattr(decoder.decode_opus_float, 'sub_enabled'):
        decoder.decode_opus_float.sub_enabled = audio_config.DEFAULT_SUB_ENABLED
    if not hasattr(decoder.decode_opus_float, 'audio_routing'):
        decoder.decode_opus_float.audio_routing = audio_config.DEFAULT_AUDIO_ROUTING

# Initialize on module load
_initialize_default_settings()

print("🎚️ Audio controls initialized")
