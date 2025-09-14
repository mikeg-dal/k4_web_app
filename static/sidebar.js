/**
 * Responsive Sidebar JavaScript
 * Handles sidebar toggle, settings panel, and synchronization with main controls
 */

// Sidebar state
let sidebarOpen = false;
let radioManagerExpanded = false;
let settingsExpanded = false;
let sessionInfoExpanded = false;

// Radio management state
let currentEditingRadioId = null;

// Initialize sidebar functionality
function initializeSidebar() {
    // Sync initial values from main controls to sidebar
    syncSidebarControls();
    
    // Set up event listeners for sidebar controls
    setupSidebarEventListeners();
    
    // Set up periodic sync for session info (every 2 seconds)
    setInterval(() => {
        if (sessionInfoExpanded) {
            syncSessionInfo();
        }
    }, 2000);
    
    // Set up periodic sync for radio manager connection status (every 1 second)
    setInterval(() => {
        if (radioManagerExpanded) {
            updateConnectionStatus();
        }
    }, 1000);
    
    console.log('✅ Sidebar initialized');
}

// Open sidebar
function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar && overlay) {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        sidebarOpen = true;
        
        // Sync controls when opening
        syncSidebarControls();
    }
}

// Close sidebar
function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar && overlay) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        sidebarOpen = false;
        
        // Close settings and session info panels when closing sidebar
        if (settingsExpanded) {
            toggleSettings();
        }
        if (sessionInfoExpanded) {
            toggleSessionInfo();
        }
    }
}

// Toggle radio manager panel
function toggleRadioManager() {
    const radioPanel = document.getElementById('radioManagerPanel');
    const arrow = document.getElementById('radioManagerArrow');
    
    if (radioPanel && arrow) {
        radioManagerExpanded = !radioManagerExpanded;
        
        if (radioManagerExpanded) {
            radioPanel.classList.add('expanded');
            arrow.classList.add('rotated');
            arrow.textContent = '▼';
            
            // Close other panels if open
            if (settingsExpanded) {
                toggleSettings();
            }
            if (sessionInfoExpanded) {
                toggleSessionInfo();
            }
            
            // Initialize radio manager when first opened
            initializeRadioManager();
        } else {
            radioPanel.classList.remove('expanded');
            arrow.classList.remove('rotated');
            arrow.textContent = '▶';
        }
    }
}

// Toggle settings panel
function toggleSettings() {
    const settingsPanel = document.getElementById('settingsPanel');
    const arrow = document.getElementById('settingsArrow');
    
    if (settingsPanel && arrow) {
        settingsExpanded = !settingsExpanded;
        
        if (settingsExpanded) {
            settingsPanel.classList.add('expanded');
            arrow.classList.add('rotated');
            arrow.textContent = '▼';
            
            // Close other panels if open
            if (radioManagerExpanded) {
                toggleRadioManager();
            }
            if (sessionInfoExpanded) {
                toggleSessionInfo();
            }
            
            // Sync controls when expanding settings
            syncSidebarControls();
        } else {
            settingsPanel.classList.remove('expanded');
            arrow.classList.remove('rotated');
            arrow.textContent = '▶';
        }
    }
}

// Toggle session info panel
function toggleSessionInfo() {
    const sessionInfoPanel = document.getElementById('sessionInfoPanel');
    const arrow = document.getElementById('sessionInfoArrow');
    
    if (sessionInfoPanel && arrow) {
        sessionInfoExpanded = !sessionInfoExpanded;
        
        if (sessionInfoExpanded) {
            sessionInfoPanel.classList.add('expanded');
            arrow.classList.add('rotated');
            arrow.textContent = '▼';
            
            // Close other panels if open
            if (radioManagerExpanded) {
                toggleRadioManager();
            }
            if (settingsExpanded) {
                toggleSettings();
            }
            
            // Sync session info when expanding
            syncSessionInfo();
        } else {
            sessionInfoPanel.classList.remove('expanded');
            arrow.classList.remove('rotated');
            arrow.textContent = '▶';
        }
    }
}

// Sync sidebar controls with main controls
function syncSidebarControls() {
    // Sync Sub Receiver toggle
    const mainSubToggle = document.getElementById('subRxToggle');
    const sidebarSubToggle = document.getElementById('sidebarSubRxToggle');
    if (mainSubToggle && sidebarSubToggle) {
        sidebarSubToggle.className = mainSubToggle.className;
        sidebarSubToggle.textContent = mainSubToggle.textContent;
    }
    
    // Sync Audio Routing select
    const mainRouting = document.getElementById('audioRoutingSelect');
    const sidebarRouting = document.getElementById('sidebarAudioRoutingSelect');
    if (mainRouting && sidebarRouting) {
        sidebarRouting.value = mainRouting.value;
    }
    
    // Sync status displays
    const mainAudioStatus = document.getElementById('audioStatusDisplay');
    const sidebarAudioStatus = document.getElementById('sidebarAudioStatusDisplay');
    if (mainAudioStatus && sidebarAudioStatus) {
        sidebarAudioStatus.textContent = mainAudioStatus.textContent;
    }
    
    const mainRoutingStatus = document.getElementById('routingStatusDisplay');
    const sidebarRoutingStatus = document.getElementById('sidebarRoutingStatusDisplay');
    if (mainRoutingStatus && sidebarRoutingStatus) {
        sidebarRoutingStatus.textContent = mainRoutingStatus.textContent;
    }
    
    // Sync volume controls
    const mainVolume = document.getElementById('volumeSlider');
    const sidebarVolume = document.getElementById('sidebarVolumeSlider');
    const sidebarVolumeValue = document.getElementById('sidebarVolumeValue');
    if (mainVolume && sidebarVolume && sidebarVolumeValue) {
        sidebarVolume.value = mainVolume.value;
        sidebarVolumeValue.textContent = mainVolume.value + '%';
    }
    
    // Sync buffer size
    const mainBuffer = document.getElementById('bufferSlider');
    const sidebarBuffer = document.getElementById('sidebarBufferSlider');
    const sidebarBufferValue = document.getElementById('sidebarBufferValue');
    if (mainBuffer && sidebarBuffer && sidebarBufferValue) {
        sidebarBuffer.value = mainBuffer.value;
        sidebarBufferValue.textContent = mainBuffer.value;
    }
    
    // Sync mic gain
    const mainMicGain = document.getElementById('micGainSlider');
    const sidebarMicGain = document.getElementById('sidebarMicGainSlider');
    const sidebarMicGainValue = document.getElementById('sidebarMicGainValue');
    if (mainMicGain && sidebarMicGain && sidebarMicGainValue) {
        sidebarMicGain.value = mainMicGain.value;
        sidebarMicGainValue.textContent = mainMicGain.value + '%';
    }
    
    // Sync processing status
    const mainProcessingStatus = document.getElementById('processingStatus');
    const sidebarProcessingStatus = document.getElementById('sidebarProcessingStatus');
    if (mainProcessingStatus && sidebarProcessingStatus) {
        sidebarProcessingStatus.textContent = mainProcessingStatus.textContent;
    }
}

// Sync session info with main status elements
function syncSessionInfo() {
    // Sync Audio Queue
    const mainAudioStatus = document.getElementById('audioStatus');
    const sidebarAudioStatus = document.getElementById('sidebarAudioStatus');
    if (mainAudioStatus && sidebarAudioStatus) {
        // Extract just the number from "Audio Queue: 3"
        const match = mainAudioStatus.textContent.match(/Audio Queue:\s*(\d+)/);
        sidebarAudioStatus.textContent = match ? match[1] : '0';
    }
    
    // Sync Audio Context
    const mainAudioContext = document.getElementById('audioContext');
    const sidebarAudioContext = document.getElementById('sidebarAudioContext');
    if (mainAudioContext && sidebarAudioContext) {
        // Extract from "Audio Context: running @ 48000Hz"
        const contextText = mainAudioContext.textContent.replace('Audio Context: ', '');
        sidebarAudioContext.textContent = contextText;
    }
    
    // Sync Latency
    const mainAudioLatency = document.getElementById('audioLatency');
    const sidebarAudioLatency = document.getElementById('sidebarAudioLatency');
    if (mainAudioLatency && sidebarAudioLatency) {
        // Extract just the latency value from "Latency: 12ms"
        const match = mainAudioLatency.textContent.match(/Latency:\s*(\d+ms)/);
        sidebarAudioLatency.textContent = match ? match[1] : '0ms';
    }
    
    // Sync Dual RX Status
    const mainDualRxStatus = document.getElementById('dualRxStatus');
    const sidebarDualRxStatus = document.getElementById('sidebarDualRxStatus');
    if (mainDualRxStatus && sidebarDualRxStatus) {
        // Extract from "Dual RX: Main Only"
        const dualRxText = mainDualRxStatus.textContent.replace('Dual RX: ', '');
        sidebarDualRxStatus.textContent = dualRxText;
    }
    
    // Sync Current Mode
    const mainCurrentMode = document.getElementById('currentMode');
    const sidebarCurrentMode = document.getElementById('sidebarCurrentMode');
    if (mainCurrentMode && sidebarCurrentMode) {
        sidebarCurrentMode.textContent = mainCurrentMode.textContent;
    }
}

// Setup event listeners for sidebar controls
function setupSidebarEventListeners() {
    // Override existing functions to sync with sidebar
    if (typeof window.originalToggleSubReceiver === 'undefined') {
        window.originalToggleSubReceiver = window.toggleSubReceiver || function() {};
    }
    
    window.toggleSubReceiver = function() {
        window.originalToggleSubReceiver();
        syncSidebarControls();
    };
    
    if (typeof window.originalUpdateAudioRouting === 'undefined') {
        window.originalUpdateAudioRouting = window.updateAudioRouting || function() {};
    }
    
    window.updateAudioRouting = function(routing) {
        window.originalUpdateAudioRouting(routing);
        syncSidebarControls();
    };
    
    if (typeof window.originalUpdateVolume === 'undefined') {
        window.originalUpdateVolume = window.updateVolume || function() {};
    }
    
    window.updateVolume = function(value) {
        window.originalUpdateVolume(value);
        
        // Update sidebar volume display
        const sidebarVolumeValue = document.getElementById('sidebarVolumeValue');
        if (sidebarVolumeValue) {
            sidebarVolumeValue.textContent = value + '%';
        }
    };
    
    if (typeof window.originalUpdateBufferSize === 'undefined') {
        window.originalUpdateBufferSize = window.updateBufferSize || function() {};
    }
    
    window.updateBufferSize = function(value) {
        window.originalUpdateBufferSize(value);
        
        // Update sidebar buffer display
        const sidebarBufferValue = document.getElementById('sidebarBufferValue');
        if (sidebarBufferValue) {
            sidebarBufferValue.textContent = value;
        }
    };
    
    if (typeof window.originalUpdateMicGain === 'undefined') {
        window.originalUpdateMicGain = window.updateMicGain || function() {};
    }
    
    window.updateMicGain = function(value) {
        window.originalUpdateMicGain(value);
        
        // Update sidebar mic gain display
        const sidebarMicGainValue = document.getElementById('sidebarMicGainValue');
        if (sidebarMicGainValue) {
            sidebarMicGainValue.textContent = value + '%';
        }
    };
    
    if (typeof window.originalToggleAudioProcessing === 'undefined') {
        window.originalToggleAudioProcessing = window.toggleAudioProcessing || function() {};
    }
    
    window.toggleAudioProcessing = function() {
        window.originalToggleAudioProcessing();
        syncSidebarControls();
    };
}

// Close sidebar when clicking outside (additional safety)
document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    
    if (sidebar && sidebarToggle && sidebarOpen) {
        // Check if click is outside sidebar and not on toggle button
        if (!sidebar.contains(event.target) && !sidebarToggle.contains(event.target)) {
            // Don't close if clicking on the overlay (that's handled by overlay click)
            if (!event.target.classList.contains('sidebar-overlay')) {
                closeSidebar();
            }
        }
    }
});

// Handle escape key to close sidebar
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && sidebarOpen) {
        closeSidebar();
    }
});

// Radio Management Functions

async function initializeRadioManager() {
    // Set up radio manager callbacks
    if (window.radioManager) {
        window.radioManager.setCallbacks({
            onRadioListUpdated: updateRadioDisplay,
            onRadioChanged: handleRadioChanged,
            onError: handleRadioError
        });
        
        // Load initial radio data
        await refreshRadioList();
    }
}

async function refreshRadioList() {
    try {
        if (window.radioManager) {
            await window.radioManager.loadRadios();
            updateLastUpdateTime();
        }
    } catch (error) {
        console.error('❌ Failed to refresh radio list:', error);
        handleRadioError('Failed to refresh radio list', error);
    }
}

function updateRadioDisplay(radios, activeRadioId) {
    updateActiveRadioDisplay(activeRadioId, radios[activeRadioId]);
    updateRadioListDisplay(radios, activeRadioId);
    updateConnectionStatus();
}

function updateActiveRadioDisplay(activeRadioId, activeRadio) {
    const nameElement = document.querySelector('#activeRadioDisplay .radio-name');
    const detailsElement = document.querySelector('#activeRadioDisplay .radio-details');
    
    if (nameElement && detailsElement) {
        if (activeRadio) {
            nameElement.textContent = activeRadio.name;
            
            // Get real-time connection status
            const isConnected = window.ws && window.ws.readyState === WebSocket.OPEN;
            const connectionStatus = isConnected ? 'Connected' : 'Ready';
            const lastConnected = window.radioManager.formatLastConnected(activeRadio.last_connected);
            
            detailsElement.innerHTML = `
                ${activeRadio.host}:${activeRadio.port}<br>
                Status: <span style="color: ${isConnected ? '#4CAF50' : '#2196F3'}">${connectionStatus}</span><br>
                Last connected: ${lastConnected}
            `;
        } else {
            nameElement.textContent = 'No Active Radio';
            detailsElement.textContent = 'Please select a radio to connect';
        }
    }
}

function updateRadioListDisplay(radios, activeRadioId) {
    const radioList = document.getElementById('radioList');
    
    if (!radioList) return;
    
    if (Object.keys(radios).length === 0) {
        radioList.innerHTML = '<div class="radio-loading">No radios configured. Click "Add Radio" to get started.</div>';
        return;
    }
    
    const radioItems = Object.entries(radios).map(([radioId, radio]) => {
        const isActive = radioId === activeRadioId;
        const statusColor = window.radioManager.getRadioStatusColor(radio, radioId);
        const statusClass = isActive ? 'active' : (radio.enabled ? 'available' : 'disabled');
        
        return `
            <div class="radio-item ${isActive ? 'active' : ''}" onclick="handleRadioClick('${radioId}')">
                <div class="radio-item-info">
                    <div class="radio-item-name">${radio.name}</div>
                    <div class="radio-item-details">${radio.host}:${radio.port}</div>
                </div>
                <div class="radio-item-status">
                    <div class="radio-status-dot ${statusClass}"></div>
                    <div class="radio-item-actions">
                        ${!isActive ? `<button class="radio-action-button" onclick="event.stopPropagation(); activateRadio('${radioId}')">Select</button>` : ''}
                        <button class="radio-action-button" onclick="event.stopPropagation(); editRadio('${radioId}')">Edit</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    radioList.innerHTML = radioItems;
}

function updateConnectionStatus() {
    const statusElement = document.getElementById('radioConnectionStatus');
    const activeRadio = window.radioManager?.getActiveRadio();
    
    if (statusElement) {
        if (activeRadio) {
            // Check if WebSocket is actually connected
            const isConnected = window.ws && window.ws.readyState === WebSocket.OPEN;
            if (isConnected) {
                statusElement.textContent = `Connected to ${activeRadio.name}`;
                statusElement.style.color = '#4CAF50'; // Green
            } else {
                statusElement.textContent = `Ready: ${activeRadio.name}`;
                statusElement.style.color = '#2196F3'; // Blue
            }
        } else {
            statusElement.textContent = 'No active radio';
            statusElement.style.color = '#666666'; // Gray
        }
    }
}

function updateLastUpdateTime() {
    const updateElement = document.getElementById('radioLastUpdate');
    if (updateElement) {
        const now = new Date();
        updateElement.textContent = now.toLocaleTimeString();
    }
}

async function handleRadioClick(radioId) {
    if (!window.radioManager.isRadioActive(radioId)) {
        await activateRadio(radioId);
    }
}

async function activateRadio(radioId) {
    try {
        await window.radioManager.activateRadio(radioId);
        console.log(`✅ Switched to radio: ${radioId}`);
        
        // Show success message
        showRadioMessage(`Switched to ${window.radioManager.getRadio(radioId)?.name}`, 'success');
        
        // Trigger connection with new radio (this would need to be implemented in the main app)
        if (typeof triggerRadioReconnection === 'function') {
            triggerRadioReconnection();
        }
        
    } catch (error) {
        console.error('❌ Failed to activate radio:', error);
        showRadioMessage('Failed to switch radio', 'error');
    }
}

function handleRadioChanged(radioId, radioConfig) {
    console.log(`📻 Active radio changed to: ${radioConfig.name}`);
    updateConnectionStatus();
}

function handleRadioError(message, error) {
    console.error('❌ Radio Manager Error:', message, error);
    showRadioMessage(message, 'error');
}

function showRadioMessage(message, type) {
    // Simple message display - could be enhanced with a toast notification system
    const statusElement = document.getElementById('radioConnectionStatus');
    if (statusElement) {
        const originalText = statusElement.textContent;
        const originalColor = statusElement.style.color;
        
        statusElement.textContent = message;
        statusElement.style.color = type === 'success' ? '#4CAF50' : '#f44336';
        
        setTimeout(() => {
            statusElement.textContent = originalText;
            statusElement.style.color = originalColor;
        }, 3000);
    }
}

// Radio Dialog Functions

function showAddRadioDialog() {
    currentEditingRadioId = null;
    
    document.getElementById('radioDialogTitle').textContent = 'Add New Radio';
    document.getElementById('radioForm').reset();
    document.getElementById('radioDeleteButton').style.display = 'none';
    
    showRadioDialog();
}

function editRadio(radioId) {
    const radio = window.radioManager.getRadio(radioId);
    if (!radio) return;
    
    currentEditingRadioId = radioId;
    
    document.getElementById('radioDialogTitle').textContent = `Edit ${radio.name}`;
    document.getElementById('radioName').value = radio.name;
    document.getElementById('radioHost').value = radio.host;
    document.getElementById('radioPort').value = radio.port;
    document.getElementById('radioPassword').value = radio.password;
    document.getElementById('radioDescription').value = radio.description || '';
    document.getElementById('radioEnabled').checked = radio.enabled;
    document.getElementById('radioDeleteButton').style.display = 'block';
    
    showRadioDialog();
}

function showRadioDialog() {
    const overlay = document.getElementById('radioDialogOverlay');
    const dialog = document.getElementById('radioDialog');
    
    if (overlay && dialog) {
        overlay.classList.add('show');
        dialog.classList.add('show');
    }
}

function closeRadioDialog() {
    const overlay = document.getElementById('radioDialogOverlay');
    const dialog = document.getElementById('radioDialog');
    
    if (overlay && dialog) {
        overlay.classList.remove('show');
        dialog.classList.remove('show');
    }
    
    currentEditingRadioId = null;
}

async function submitRadioForm(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const radioData = {
        name: formData.get('name'),
        host: formData.get('host'),
        port: formData.get('port'),
        password: formData.get('password'),
        description: formData.get('description'),
        enabled: formData.has('enabled')
    };
    
    // Validate the data
    const errors = window.radioManager.validateRadioData(radioData);
    if (errors.length > 0) {
        alert('Please fix the following errors:\n\n' + errors.join('\n'));
        return false;
    }
    
    try {
        if (currentEditingRadioId) {
            // Update existing radio
            await window.radioManager.updateRadio(currentEditingRadioId, radioData);
            showRadioMessage(`Updated ${radioData.name}`, 'success');
        } else {
            // Create new radio
            await window.radioManager.createRadio(radioData);
            showRadioMessage(`Created ${radioData.name}`, 'success');
        }
        
        closeRadioDialog();
        
    } catch (error) {
        console.error('❌ Failed to save radio:', error);
        alert(`Failed to save radio: ${error.message}`);
    }
    
    return false;
}

async function deleteCurrentRadio() {
    if (!currentEditingRadioId) return;
    
    const radio = window.radioManager.getRadio(currentEditingRadioId);
    if (!radio) return;
    
    const confirmed = confirm(`Are you sure you want to delete "${radio.name}"?\n\nThis action cannot be undone.`);
    if (!confirmed) return;
    
    try {
        await window.radioManager.deleteRadio(currentEditingRadioId);
        showRadioMessage(`Deleted ${radio.name}`, 'success');
        closeRadioDialog();
        
    } catch (error) {
        console.error('❌ Failed to delete radio:', error);
        alert(`Failed to delete radio: ${error.message}`);
    }
}

// Make functions globally available
window.openSidebar = openSidebar;
window.closeSidebar = closeSidebar;
window.toggleRadioManager = toggleRadioManager;
window.toggleSettings = toggleSettings;
window.toggleSessionInfo = toggleSessionInfo;
window.initializeSidebar = initializeSidebar;

// Radio management functions
window.refreshRadioList = refreshRadioList;
window.showAddRadioDialog = showAddRadioDialog;
window.editRadio = editRadio;
window.closeRadioDialog = closeRadioDialog;
window.submitRadioForm = submitRadioForm;
window.deleteCurrentRadio = deleteCurrentRadio;
window.activateRadio = activateRadio;