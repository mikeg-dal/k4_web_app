"""
K4 Web Controller - Multi-Radio Configuration System

This module provides radio configuration management without duplicating 
the shared settings from config.py. Each radio only stores its unique
connection parameters (name, host, port, password).
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

@dataclass
class RadioConfig:
    """Individual radio configuration - only unique per-radio settings"""
    name: str                    # User-friendly name: "K4 Shack", "K4 Portable"
    host: str                   # IP address: "192.168.1.10"
    port: int                   # Port: 9205
    password: str               # Radio password: "tester"
    enabled: bool = True        # Whether radio is available for connection
    last_connected: Optional[str] = None    # ISO timestamp of last connection
    description: str = ""       # Optional description
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RadioConfig':
        """Create RadioConfig from dictionary"""
        return cls(**data)
    
    def update_last_connected(self):
        """Update last connected timestamp to now"""
        self.last_connected = datetime.now().isoformat()


class RadioManager:
    """Manages multiple radio configurations"""
    
    def __init__(self, config_dir: str = "radios/configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.active_radio_file = Path("radios/active_radio.json")
        self._radios: Dict[str, RadioConfig] = {}
        self._active_radio_id: Optional[str] = None
        
        # Load existing configurations
        self.load_all_radios()
        self.load_active_radio()
    
    def get_radio_config_file(self, radio_id: str) -> Path:
        """Get the config file path for a radio"""
        return self.config_dir / f"{radio_id}.json"
    
    def create_radio_id(self, name: str) -> str:
        """Create a filesystem-safe radio ID from name"""
        # Convert to lowercase, replace spaces/special chars with hyphens
        radio_id = name.lower().replace(" ", "-")
        radio_id = "".join(c for c in radio_id if c.isalnum() or c in "-_")
        
        # Ensure uniqueness
        counter = 1
        original_id = radio_id
        while radio_id in self._radios:
            radio_id = f"{original_id}-{counter}"
            counter += 1
            
        return radio_id
    
    def add_radio(self, name: str, host: str, port: int, password: str, 
                  description: str = "", enabled: bool = True) -> str:
        """Add a new radio configuration"""
        radio_id = self.create_radio_id(name)
        
        radio_config = RadioConfig(
            name=name,
            host=host,
            port=port,
            password=password,
            description=description,
            enabled=enabled
        )
        
        self._radios[radio_id] = radio_config
        self.save_radio(radio_id)
        
        # If this is the first radio, make it active
        if not self._active_radio_id:
            self.set_active_radio(radio_id)
            
        return radio_id
    
    def update_radio(self, radio_id: str, **kwargs) -> bool:
        """Update an existing radio configuration"""
        if radio_id not in self._radios:
            return False
            
        radio = self._radios[radio_id]
        
        # Update allowed fields
        allowed_fields = {'name', 'host', 'port', 'password', 'description', 'enabled'}
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(radio, field, value)
        
        self.save_radio(radio_id)
        return True
    
    def remove_radio(self, radio_id: str) -> bool:
        """Remove a radio configuration"""
        if radio_id not in self._radios:
            return False
            
        # Don't allow removing the only radio
        if len(self._radios) <= 1:
            return False
            
        # If removing active radio, switch to another one
        if radio_id == self._active_radio_id:
            remaining_radios = [rid for rid in self._radios.keys() if rid != radio_id]
            if remaining_radios:
                self.set_active_radio(remaining_radios[0])
        
        # Remove radio and its config file
        del self._radios[radio_id]
        config_file = self.get_radio_config_file(radio_id)
        if config_file.exists():
            config_file.unlink()
            
        return True
    
    def get_radio(self, radio_id: str) -> Optional[RadioConfig]:
        """Get a specific radio configuration"""
        return self._radios.get(radio_id)
    
    def get_all_radios(self) -> Dict[str, RadioConfig]:
        """Get all radio configurations"""
        return self._radios.copy()
    
    def set_active_radio(self, radio_id: str) -> bool:
        """Set the active radio"""
        if radio_id not in self._radios:
            return False
            
        self._active_radio_id = radio_id
        self.save_active_radio()
        
        # Update last connected timestamp
        self._radios[radio_id].update_last_connected()
        self.save_radio(radio_id)
        
        return True
    
    def get_active_radio(self) -> Optional[RadioConfig]:
        """Get the currently active radio configuration"""
        if self._active_radio_id:
            return self._radios.get(self._active_radio_id)
        return None
    
    def get_active_radio_id(self) -> Optional[str]:
        """Get the currently active radio ID"""
        return self._active_radio_id
    
    def save_radio(self, radio_id: str):
        """Save a single radio configuration to file"""
        if radio_id not in self._radios:
            return
            
        config_file = self.get_radio_config_file(radio_id)
        with open(config_file, 'w') as f:
            json.dump(self._radios[radio_id].to_dict(), f, indent=2)
    
    def load_radio(self, radio_id: str) -> bool:
        """Load a single radio configuration from file"""
        config_file = self.get_radio_config_file(radio_id)
        if not config_file.exists():
            return False
            
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
                self._radios[radio_id] = RadioConfig.from_dict(data)
                return True
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"⚠️ Failed to load radio config {radio_id}: {e}")
            return False
    
    def load_all_radios(self):
        """Load all radio configurations from config directory"""
        if not self.config_dir.exists():
            return
            
        for config_file in self.config_dir.glob("*.json"):
            radio_id = config_file.stem
            self.load_radio(radio_id)
    
    def save_active_radio(self):
        """Save the active radio selection"""
        data = {"active_radio_id": self._active_radio_id}
        with open(self.active_radio_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_active_radio(self):
        """Load the active radio selection"""
        if not self.active_radio_file.exists():
            return
            
        try:
            with open(self.active_radio_file, 'r') as f:
                data = json.load(f)
                active_id = data.get("active_radio_id")
                if active_id and active_id in self._radios:
                    self._active_radio_id = active_id
        except (json.JSONDecodeError, KeyError):
            pass
    
    def create_default_radio_if_none(self):
        """Create a default radio configuration if none exist"""
        if not self._radios:
            self.add_radio(
                name="Default K4",
                host="192.168.1.10",
                port=9205,
                password="tester",
                description="Default K4 radio configuration"
            )
            print("📻 Created default radio configuration")


# Global radio manager instance
radio_manager = RadioManager()

def get_radio_manager() -> RadioManager:
    """Get the global radio manager instance"""
    return radio_manager

def get_current_radio_config() -> Optional[RadioConfig]:
    """Get the currently active radio configuration"""
    return radio_manager.get_active_radio()

def get_current_k4_connection_params() -> dict:
    """Get K4 connection parameters for the active radio"""
    active_radio = get_current_radio_config()
    if active_radio:
        return {
            "host": active_radio.host,
            "port": active_radio.port,
            "password": active_radio.password
        }
    
    # Fallback to original config.py values
    from config import k4_config
    return {
        "host": k4_config.DEFAULT_HOST,
        "port": k4_config.DEFAULT_PORT,
        "password": k4_config.DEFAULT_PASSWORD
    }