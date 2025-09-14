/**
 * VFO Control Integration with K4 System - New Dual Row Version
 * Bridges the dual VFO control panel with existing K4 WebSocket communication
 */

class VFOIntegrationNew {
    constructor() {
        this.vfoControl = null;
        this.isInitialized = false;
    }

    initialize() {
        if (this.isInitialized) return;
        
        // Initialize VFO control panel
        this.vfoControl = initializeVFOControlNew();
        
        // Set up callbacks for K4 communication
        this.vfoControl.setCallbacks({
            onFrequencyChange: (vfo, frequency) => this.sendFrequencyCommand(vfo, frequency),
            onModeChange: (vfo, mode) => this.sendModeCommand(vfo, mode),
            onStepChange: (vfo, step) => this.sendStepCommand(vfo, step),
            onNoiseControl: (vfo, type, action, level, filterValue) => this.sendNoiseCommand(vfo, type, action, level, filterValue),
            onSubRXControl: () => this.sendSubRXCommand(),
            onVolumeChange: (vfo, volume) => this.sendVolumeCommand(vfo, volume)
        });

        // Listen for updates from existing CAT command system
        this.setupCATListeners();
        
        this.isInitialized = true;
        console.log('✅ VFO Integration initialized');
    }

    setupCATListeners() {
        // Override the existing updateCAT function to capture VFO updates
        if (typeof window.originalUpdateCAT === 'undefined') {
            window.originalUpdateCAT = window.updateCAT || function() {};
        }
        
        window.updateCAT = (text, updates = {}) => {
            // Call original updateCAT function
            window.originalUpdateCAT(text, updates);
            
            // Process CAT commands for VFO updates
            this.processCAT(text, updates);
        };
    }

    processCAT(text) {
        const commands = text.split(';');
        
        for (let cmd of commands) {
            if (cmd.startsWith("FA")) {
                // VFO A frequency
                const freq = parseInt(cmd.slice(2));
                if (!isNaN(freq)) {
                    this.vfoControl.updateFromK4('A', { frequency: freq });
                }
            } else if (cmd.startsWith("FB")) {
                // VFO B frequency  
                const freq = parseInt(cmd.slice(2));
                if (!isNaN(freq)) {
                    this.vfoControl.updateFromK4('B', { frequency: freq });
                }
            } else if (cmd.startsWith("MD$")) {
                // VFO B mode
                const modeCode = cmd.slice(3);
                const mode = this.mapModeCode(modeCode);
                if (mode) {
                    this.vfoControl.updateFromK4('B', { mode: mode });
                }
            } else if (cmd.startsWith("MD")) {
                // VFO A mode
                const modeCode = cmd.slice(2);
                const mode = this.mapModeCode(modeCode);
                if (mode) {
                    this.vfoControl.updateFromK4('A', { mode: mode });
                }
            } else if (cmd.startsWith("NB$")) {
                // VFO B Noise Blanker state - K4 format: NB$0LEM
                const stateAndLevel = cmd.slice(3);
                if (stateAndLevel.length >= 4) {
                    const level = parseInt(stateAndLevel.charAt(1)) || 1;
                    const enabled = (stateAndLevel.charAt(2) === '1');
                    const filter = parseInt(stateAndLevel.charAt(3)) || 0;
                    if (this.vfoControl.vfoState.B.nb) {
                        this.vfoControl.vfoState.B.nb.enabled = enabled;
                        this.vfoControl.vfoState.B.nb.level = level;
                        this.vfoControl.vfoState.B.nb.filter = filter;
                        this.vfoControl.updateNoiseControls('B');
                    }
                }
            } else if (cmd.startsWith("NB")) {
                // VFO A Noise Blanker state - K4 format: NB0LEM
                const stateAndLevel = cmd.slice(2);
                if (stateAndLevel.length >= 4) {
                    const level = parseInt(stateAndLevel.charAt(1)) || 1;
                    const enabled = (stateAndLevel.charAt(2) === '1');
                    const filter = parseInt(stateAndLevel.charAt(3)) || 0;
                    if (this.vfoControl.vfoState.A.nb) {
                        this.vfoControl.vfoState.A.nb.enabled = enabled;
                        this.vfoControl.vfoState.A.nb.level = level;
                        this.vfoControl.vfoState.A.nb.filter = filter;
                        this.vfoControl.updateNoiseControls('A');
                    }
                }
            } else if (cmd.startsWith("NR$")) {
                // VFO B Noise Reduction state - K4 format: NR$nnm
                const stateAndLevel = cmd.slice(3);
                if (stateAndLevel.length >= 3) {
                    const enabled = (stateAndLevel.slice(-1) === '1');
                    const level = parseInt(stateAndLevel.slice(0, -1)) || 0;
                    if (this.vfoControl.vfoState.B.nr) {
                        this.vfoControl.vfoState.B.nr.enabled = enabled;
                        this.vfoControl.vfoState.B.nr.level = level;
                        this.vfoControl.updateNoiseControls('B');
                    }
                }
            } else if (cmd.startsWith("NR")) {
                // VFO A Noise Reduction state - K4 format: NRnnm
                const stateAndLevel = cmd.slice(2);
                if (stateAndLevel.length >= 3) {
                    const enabled = (stateAndLevel.slice(-1) === '1');
                    const level = parseInt(stateAndLevel.slice(0, -1)) || 0;
                    if (this.vfoControl.vfoState.A.nr) {
                        this.vfoControl.vfoState.A.nr.enabled = enabled;
                        this.vfoControl.vfoState.A.nr.level = level;
                        this.vfoControl.updateNoiseControls('A');
                    }
                }
            } else if (cmd.startsWith("SB")) {
                // Sub Receiver state - SB0=OFF, SB1=ON
                const enabled = (cmd.slice(2) === '1');
                this.vfoControl.updateSubRX(enabled);
            }
        }
    }

    mapModeCode(modeCode) {
        // STEP 5: Use configuration system for mode mapping with safe fallback
        if (typeof K4ModeUtils !== 'undefined') {
            return K4ModeUtils.getModeDisplayName(modeCode) !== `Mode ${modeCode}` ? 
                   K4ModeUtils.getModeDisplayName(modeCode) : null;
        } else {
            // Safe fallback if configuration not loaded yet
            const fallbackModeMap = {
                '1': 'LSB', '2': 'USB', '3': 'CW', '4': 'FM',
                '5': 'AM', '6': 'DATA', '7': 'CW-R', '9': 'DATA-R'
            };
            return fallbackModeMap[modeCode] || null;
        }
    }

    sendFrequencyCommand(vfo, frequency) {
        if (!vfo || frequency === undefined || frequency === null) {
            console.error('❌ Invalid VFO frequency command parameters:', { vfo, frequency });
            return;
        }
        
        this.sendSemanticCommand('set_frequency', {
            vfo: vfo.toUpperCase(),
            frequency: frequency
        });
    }

    sendModeCommand(vfo, mode) {
        if (!vfo || !mode) {
            console.error('❌ Invalid VFO mode command parameters:', { vfo, mode });
            return;
        }
        
        this.sendSemanticCommand('set_mode', {
            vfo: vfo.toUpperCase(),
            mode: mode.toUpperCase()
        });
    }

    sendStepCommand(vfo, step) {
        // K4 step commands - implement if needed
        // Current implementation doesn't send step commands to K4
    }

    sendNoiseCommand(vfo, type, action, level, filterValue) {
        // Determine enabled state and level from action
        let enabled = false;
        let finalLevel = level || 5;
        let finalFilter = filterValue || 0;
        
        if (action === 'ON') {
            enabled = true;
        } else if (action === 'OFF') {
            enabled = false;
        } else if (action === 'SET_LEVEL') {
            // Get current state for enabled status
            const currentState = this.getVFOState()?.[vfo]?.[type.toLowerCase()];
            enabled = currentState?.enabled || false;
        } else if (action === 'SET_FILTER') {
            // Get current state for enabled status and level
            const currentState = this.getVFOState()?.[vfo]?.[type.toLowerCase()];
            enabled = currentState?.enabled || false;
            finalLevel = currentState?.level || 5;
        }
        
        this.sendSemanticCommand('set_noise_control', {
            vfo: vfo.toUpperCase(),
            noise_type: type.toUpperCase(),
            enabled: enabled,
            level: finalLevel,
            filter: finalFilter
        });
    }

    sendSubRXCommand() {
        this.sendSemanticCommand('toggle_sub_rx', {});
        
        // Also integrate with audio system Sub Receiver
        if (typeof window.updateVFOSubRX === 'function') {
            window.updateVFOSubRX();
        }
    }

    sendVolumeCommand(vfo, volume) {
        // Send volume commands to main app volume controls
        // Integrate with existing volume control system
        if (typeof window.updateVFOVolume === 'function') {
            window.updateVFOVolume(vfo, volume);
        }
    }

    sendSemanticCommand(action, data) {
        // Send semantic JSON command to Python backend
        let message;
        
        // Handle filter control commands specially
        if (action === 'filter_control' || action === 'update_filter_values') {
            message = {
                type: 'filter_control',
                action: action,
                ...data
            };
        } else {
            // Standard VFO control commands
            message = {
                type: 'vfo_control',
                action: action,
                ...data
            };
        }
        
        if (typeof send === 'function') {
            send(JSON.stringify(message));
        } else {
            console.warn('⚠️ Send function not available for semantic command');
        }
    }

    sendCommand(command) {
        // Validate command is not empty
        if (!command || command.trim() === '') {
            console.error('❌ VFO Integration attempted to send empty command:', JSON.stringify(command));
            return;
        }
        
        // Use existing send function from app.js
        if (typeof send === 'function') {
            send(command);
        } else {
            console.warn('⚠️ Send function not available');
        }
    }

    // Public method to update VFO data from external sources
    updateVFO(vfo, data) {
        if (this.vfoControl) {
            this.vfoControl.updateFromK4(vfo, data);
        }
    }

    // Public method to get current VFO state
    getVFOState() {
        return this.vfoControl ? this.vfoControl.vfoState : null;
    }
}

// Global VFO integration instance
let vfoIntegrationNew = null;

// Initialize VFO integration
function initializeVFOIntegrationNew() {
    if (!vfoIntegrationNew) {
        vfoIntegrationNew = new VFOIntegrationNew();
        vfoIntegrationNew.initialize();
    }
    return vfoIntegrationNew;
}

// Make it available globally
window.vfoIntegrationNew = vfoIntegrationNew;

// Make sendSemanticCommand available as a global function for filter controls
window.sendSemanticCommand = function(action, data) {
    // Try to get the initialized instance first
    const integration = window.vfoIntegrationNew || vfoIntegrationNew;
    
    if (integration && integration.sendSemanticCommand) {
        return integration.sendSemanticCommand(action, data);
    } else {
        // Fallback: try to send directly if send function is available
        if (typeof send === 'function') {
            let message;
            if (action === 'filter_control' || action === 'update_filter_values') {
                message = {
                    type: 'filter_control',
                    action: action,
                    ...data
                };
            } else {
                message = {
                    type: 'vfo_control',
                    action: action,
                    ...data
                };
            }
            send(JSON.stringify(message));
            return true;
        } else {
            console.warn('⚠️ VFO Integration and send function not available for semantic command:', action);
            return false;
        }
    }
};