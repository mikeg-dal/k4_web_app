/**
 * K4 Web Controller - Radio Management System
 * 
 * Provides frontend interface for managing multiple radio configurations
 * Supports adding, editing, deleting, and switching between radios
 */

class RadioManager {
    constructor() {
        this.radios = {};
        this.activeRadioId = null;
        this.apiCallbacks = {
            onRadioChanged: null,
            onRadioListUpdated: null,
            onError: null
        };
    }

    // API Integration Methods
    async loadRadios() {
        try {
            const response = await fetch('/api/radios');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.radios = data.radios;
            this.activeRadioId = data.active_radio_id;
            
            console.log(`📻 Loaded ${data.total_count} radio configurations`);
            console.log(`🎯 Active radio: ${this.activeRadioId}`);
            
            this.notifyRadioListUpdated();
            return data;
            
        } catch (error) {
            console.error('❌ Failed to load radios:', error);
            this.notifyError('Failed to load radio configurations', error);
            throw error;
        }
    }

    async createRadio(radioData) {
        try {
            const response = await fetch('/api/radios', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(radioData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log(`✅ Created radio: ${data.radio_id}`);
            
            // Refresh the radio list
            await this.loadRadios();
            return data;
            
        } catch (error) {
            console.error('❌ Failed to create radio:', error);
            this.notifyError('Failed to create radio', error);
            throw error;
        }
    }

    async updateRadio(radioId, radioData) {
        try {
            const response = await fetch(`/api/radios/${radioId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(radioData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log(`✅ Updated radio: ${radioId}`);
            
            // Refresh the radio list
            await this.loadRadios();
            return data;
            
        } catch (error) {
            console.error('❌ Failed to update radio:', error);
            this.notifyError('Failed to update radio', error);
            throw error;
        }
    }

    async deleteRadio(radioId) {
        try {
            const response = await fetch(`/api/radios/${radioId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log(`✅ Deleted radio: ${radioId}`);
            
            // Refresh the radio list
            await this.loadRadios();
            return data;
            
        } catch (error) {
            console.error('❌ Failed to delete radio:', error);
            this.notifyError('Failed to delete radio', error);
            throw error;
        }
    }

    async activateRadio(radioId) {
        try {
            const response = await fetch(`/api/radios/${radioId}/activate`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log(`✅ Activated radio: ${radioId}`);
            
            // Update local state
            this.activeRadioId = radioId;
            this.notifyRadioChanged(radioId, this.radios[radioId]);
            
            // Refresh the radio list to get updated timestamps
            await this.loadRadios();
            return data;
            
        } catch (error) {
            console.error('❌ Failed to activate radio:', error);
            this.notifyError('Failed to activate radio', error);
            throw error;
        }
    }

    // Data Access Methods
    getRadio(radioId) {
        return this.radios[radioId] || null;
    }

    getActiveRadio() {
        return this.activeRadioId ? this.radios[this.activeRadioId] : null;
    }

    getActiveRadioId() {
        return this.activeRadioId;
    }

    getAllRadios() {
        return { ...this.radios };
    }

    getRadioCount() {
        return Object.keys(this.radios).length;
    }

    isRadioActive(radioId) {
        return radioId === this.activeRadioId;
    }

    // UI Helper Methods
    formatLastConnected(isoTimestamp) {
        if (!isoTimestamp) return 'Never';
        
        try {
            const date = new Date(isoTimestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);
            
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            
            return date.toLocaleDateString();
        } catch (error) {
            return 'Unknown';
        }
    }

    getRadioStatusColor(radio, radioId) {
        if (!radio.enabled) return '#666666'; // Gray for disabled
        if (this.isRadioActive(radioId)) return '#4CAF50'; // Green for active
        return '#2196F3'; // Blue for available
    }

    getRadioStatusText(radio, radioId) {
        if (!radio.enabled) return 'Disabled';
        if (this.isRadioActive(radioId)) return 'Active';
        return 'Available';
    }

    // Validation Methods
    validateRadioData(radioData) {
        const errors = [];
        
        if (!radioData.name || radioData.name.trim().length === 0) {
            errors.push('Radio name is required');
        }
        
        if (!radioData.host || radioData.host.trim().length === 0) {
            errors.push('Host/IP address is required');
        }
        
        if (!radioData.port || isNaN(parseInt(radioData.port))) {
            errors.push('Valid port number is required');
        } else {
            const port = parseInt(radioData.port);
            if (port < 1 || port > 65535) {
                errors.push('Port must be between 1 and 65535');
            }
        }
        
        if (!radioData.password || radioData.password.trim().length === 0) {
            errors.push('Password is required');
        }
        
        return errors;
    }

    // Event Notification Methods
    setCallbacks(callbacks) {
        this.apiCallbacks = { ...this.apiCallbacks, ...callbacks };
    }

    notifyRadioChanged(radioId, radioConfig) {
        if (this.apiCallbacks.onRadioChanged) {
            this.apiCallbacks.onRadioChanged(radioId, radioConfig);
        }
    }

    notifyRadioListUpdated() {
        if (this.apiCallbacks.onRadioListUpdated) {
            this.apiCallbacks.onRadioListUpdated(this.radios, this.activeRadioId);
        }
    }

    notifyError(message, error) {
        if (this.apiCallbacks.onError) {
            this.apiCallbacks.onError(message, error);
        }
    }

    // Demo/Test Methods
    createSampleRadios() {
        const sampleRadios = [
            {
                name: "K4 Shack",
                host: "192.168.1.10",
                port: 9205,
                password: "tester",
                description: "Main station K4 in the shack"
            },
            {
                name: "K4 Portable", 
                host: "192.168.1.20",
                port: 9205,
                password: "portable",
                description: "Portable K4 for field operations"
            },
            {
                name: "K4 Contest",
                host: "192.168.1.30", 
                port: 9205,
                password: "contest",
                description: "Contest station K4",
                enabled: false
            }
        ];

        console.log('🔧 Creating sample radio configurations...');
        
        sampleRadios.forEach(async (radio, index) => {
            try {
                await this.createRadio(radio);
                console.log(`✅ Created sample radio: ${radio.name}`);
            } catch (error) {
                console.error(`❌ Failed to create sample radio ${radio.name}:`, error);
            }
        });
    }
}

// Global instance and initialization
window.radioManager = new RadioManager();

// Initialize radio manager when DOM is loaded
window.addEventListener('DOMContentLoaded', async () => {
    try {
        await window.radioManager.loadRadios();
        console.log('📻 Radio Manager initialized successfully');
    } catch (error) {
        console.error('❌ Failed to initialize Radio Manager:', error);
    }
});

console.log('📦 Radio Manager module loaded');