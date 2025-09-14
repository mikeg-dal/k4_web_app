"""
K4 Web Control Audio Package

This package provides audio processing functionality for the K4 Web Control application.
It includes RX audio decoding, TX audio encoding, volume/routing controls, and utilities.

Re-exports all functions for backward compatibility with existing imports.
"""

# Import all functions from submodules for backward compatibility
from .decoder import decode_opus_float
from .encoder import encode_audio_for_k4
from .controls import (
    set_main_volume, 
    set_sub_volume, 
    set_sub_receiver_enabled, 
    set_audio_routing, 
    get_audio_settings
)

# Version information
__version__ = "1.0.0"
__author__ = "K4 Web Control Project"

# Package metadata
__all__ = [
    # RX Audio Processing
    'decode_opus_float',
    
    # TX Audio Processing  
    'encode_audio_for_k4',
    
    # Audio Controls
    'set_main_volume',
    'set_sub_volume', 
    'set_sub_receiver_enabled',
    'set_audio_routing',
    'get_audio_settings'
]

print("🎚️ K4 Audio package loaded - maintaining backward compatibility")
