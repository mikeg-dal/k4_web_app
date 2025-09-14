"""
K4 Debug Helper Module

Centralized debug logging control to reduce console spam while preserving
the ability to enable detailed debugging when needed.
"""

import os

# Debug categories that can be individually enabled
DEBUG_CATEGORIES = {
    "GENERAL": False,      # General info messages
    "NETWORK": False,      # Network/WebSocket messages
    "AUDIO": False,        # Audio processing messages
    "PANADAPTER": False,   # Panadapter/spectrum messages
    "CAT": False,          # CAT command messages
    "CRITICAL": False,     # Critical errors (turned off for production)
}

# Check environment variables for debug flags
for category in DEBUG_CATEGORIES:
    env_var = f"K4_DEBUG_{category}"
    if os.environ.get(env_var, "").lower() in ["true", "1", "yes"]:
        DEBUG_CATEGORIES[category] = True

# Master debug flag from environment
if os.environ.get("K4_DEBUG_ALL", "").lower() in ["true", "1", "yes"]:
    for category in DEBUG_CATEGORIES:
        DEBUG_CATEGORIES[category] = True

def debug_print(category: str, message: str):
    """
    Print debug message if category is enabled.
    
    Args:
        category: Debug category (e.g., "AUDIO", "NETWORK", "PANADAPTER")
        message: Debug message to print
    """
    if DEBUG_CATEGORIES.get(category, False):
        print(f"[{category}] {message}")

def is_debug_enabled(category: str) -> bool:
    """Check if a debug category is enabled."""
    return DEBUG_CATEGORIES.get(category, False)

def enable_debug(category: str = None):
    """Enable debug for a specific category or all categories."""
    if category:
        if category in DEBUG_CATEGORIES:
            DEBUG_CATEGORIES[category] = True
            print(f"✅ Debug enabled for category: {category}")
        else:
            print(f"❌ Unknown debug category: {category}")
    else:
        # Enable all categories
        for cat in DEBUG_CATEGORIES:
            DEBUG_CATEGORIES[cat] = True
        print("✅ All debug categories enabled")

def disable_debug(category: str = None):
    """Disable debug for a specific category or all categories."""
    if category:
        if category in DEBUG_CATEGORIES:
            DEBUG_CATEGORIES[category] = False
            print(f"❌ Debug disabled for category: {category}")
        else:
            print(f"⚠️ Unknown category: {category}")
    else:
        # Disable all categories
        for cat in DEBUG_CATEGORIES:
            DEBUG_CATEGORIES[cat] = False
        print("❌ All debug categories disabled")

def get_debug_status():
    """Get current debug status for all categories."""
    return DEBUG_CATEGORIES.copy()

# Print initial debug status
print("🔧 K4 Debug Helper loaded")
print(f"   Debug categories: {', '.join([k for k, v in DEBUG_CATEGORIES.items() if v])}")
print("   Set K4_DEBUG_<CATEGORY>=true or K4_DEBUG_ALL=true to enable debug output")