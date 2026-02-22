// UI Controls and Components for WhoVoted Map

// ============================================================================
// TIME-BASED FILTER CONTROL
// ============================================================================

/**
 * TimeFilterControl class manages election date filtering
 */
class TimeFilterControl {
    constructor(map, onFilterChange) {
        this.map = map;
        this.onFilterChange = onFilterChange;
        this.currentFilter = 'all'; // Default to "All Data This Cycle"
        this.availableElections = [];
        
        this.createControl();
    }
    
    createControl() {
        // Create filter control container
        const filterControl = document.createElement('div');
        filterControl.className = 'time-filter-control';
        filterControl.innerHTML = `
            <div class="time-filter-header">
                <label for="timeFilterSelect">Election Filter:</label>
            </div>
            <div class="time-filter-content">
                <select id="timeFilterSelect" class="time-filter-select">
                    <option value="all">All Data This Cycle</option>
                </select>
            </div>
        `;
        
        document.body.appendChild(filterControl);
        
        // Add event listener
        const select = document.getElementById('timeFilterSelect');
        select.addEventListener('change', (e) => this.handleFilterChange(e.target.value));
    }
    
    /**
     * Populates the dropdown with available election dates from metadata
     * @param {Array} elections - Array of election objects with date and name
     */
    populateElections(elections) {
        this.availableElections = elections;
        
        const select = document.getElementById('timeFilterSelect');
        
        // Clear existing options except "All Data This Cycle"
        select.innerHTML = '<option value="all">All Data This Cycle</option>';
        
        // Add individual election dates
        elections.forEach(election => {
            const option = document.createElement('option');
            option.value = election.date;
            option.textContent = `${election.name} (${election.date})`;
            select.appendChild(option);
        });
    }
    
    handleFilterChange(filterValue) {
        this.currentFilter = filterValue;
        
        // Call the callback to update map
        if (this.onFilterChange) {
            this.onFilterChange(filterValue);
        }
    }
    
    getCurrentFilter() {
        return this.currentFilter;
    }
}

// ============================================================================
// LAYER CONTROL PANEL
// ============================================================================

/**
 * LayerControlPanel class manages visibility of map layers
 */
class LayerControlPanel {
    constructor(map, layers) {
        this.map = map;
        this.layers = layers; // Object with layer references
        this.layerStates = {
            voterMarkers: true,
            heatmap: false,
            precincts: false,
            pollingPlaces: false
        };
        
        this.createPanel();
        this.loadSavedStates();
    }
    
    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'layer-control-panel';
        panel.innerHTML = `
            <div class="layer-panel-header">
                <h3>Map Layers</h3>
                <button class="layer-panel-toggle" onclick="toggleLayerPanel()">
                    <i class="fas fa-layer-group"></i>
                </button>
            </div>
            <div class="layer-panel-content" id="layerPanelContent">
                <div class="layer-panel-item">
                    <label>
                        <input type="checkbox" id="layer-voter-markers" checked>
                        <span>Voter Markers</span>
                    </label>
                </div>
                <div class="layer-panel-item">
                    <label>
                        <input type="checkbox" id="layer-heatmap">
                        <span>Heatmap</span>
                    </label>
                </div>
                <div class="layer-panel-item">
                    <label>
                        <input type="checkbox" id="layer-precincts">
                        <span>Precinct Boundaries</span>
                    </label>
                </div>
                <div class="layer-panel-item">
                    <label>
                        <input type="checkbox" id="layer-polling-places">
                        <span>Polling Places</span>
                    </label>
                </div>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // Add event listeners
        this.attachEventListeners();
    }
    
    attachEventListeners() {
        document.getElementById('layer-voter-markers').addEventListener('change', (e) => {
            this.toggleLayer('voterMarkers', e.target.checked);
        });
        
        document.getElementById('layer-heatmap').addEventListener('change', (e) => {
            this.toggleLayer('heatmap', e.target.checked);
        });
        
        document.getElementById('layer-precincts').addEventListener('change', (e) => {
            this.toggleLayer('precincts', e.target.checked);
        });
        
        document.getElementById('layer-polling-places').addEventListener('change', (e) => {
            this.toggleLayer('pollingPlaces', e.target.checked);
        });
    }
    
    toggleLayer(layerName, visible) {
        this.layerStates[layerName] = visible;
        
        const layer = this.layers[layerName];
        if (!layer) return;
        
        if (visible) {
            if (!this.map.hasLayer(layer)) {
                this.map.addLayer(layer);
            }
        } else {
            if (this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
        }
        
        // Save state to localStorage
        this.saveStates();
    }
    
    saveStates() {
        localStorage.setItem('layerStates', JSON.stringify(this.layerStates));
    }
    
    loadSavedStates() {
        const saved = localStorage.getItem('layerStates');
        if (saved) {
            try {
                this.layerStates = JSON.parse(saved);
                
                // Update checkboxes
                document.getElementById('layer-voter-markers').checked = this.layerStates.voterMarkers;
                document.getElementById('layer-heatmap').checked = this.layerStates.heatmap;
                document.getElementById('layer-precincts').checked = this.layerStates.precincts;
                document.getElementById('layer-polling-places').checked = this.layerStates.pollingPlaces;
                
                // Apply states to map
                Object.keys(this.layerStates).forEach(layerName => {
                    this.toggleLayer(layerName, this.layerStates[layerName]);
                });
            } catch (e) {
                console.error('Error loading saved layer states:', e);
            }
        }
    }
}

function toggleLayerPanel() {
    const content = document.getElementById('layerPanelContent');
    const panel = document.querySelector('.layer-control-panel');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        panel.classList.add('expanded');
    } else {
        content.style.display = 'none';
        panel.classList.remove('expanded');
    }
}

// ============================================================================
// COLOR LEGEND
// ============================================================================

/**
 * ColorLegend class displays the marker color coding system
 */
class ColorLegend {
    constructor() {
        this.isCollapsed = true; // Start collapsed
        this.createLegend();
        this.makeDraggable();
    }
    
    createLegend() {
        const legend = document.createElement('div');
        legend.id = 'colorLegend';
        legend.className = 'color-legend collapsed'; // Start with collapsed class
        legend.innerHTML = `
            <div class="legend-header">
                <h3>Marker Legend</h3>
                <button class="legend-toggle" onclick="toggleLegend()">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>
            <div class="legend-content" id="legendContent" style="display: none;">
                <div class="legend-section">
                    <h4>Voted (Filled Circles)</h4>
                    <div class="legend-item">
                        <span class="legend-marker filled red"></span>
                        <span>Republican</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-marker filled blue"></span>
                        <span>Democratic</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-marker filled purple"></span>
                        <span>Switched to Democratic</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-marker filled maroon"></span>
                        <span>Switched to Republican</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-marker filled green"></span>
                        <span>Unknown Affiliation</span>
                    </div>
                </div>
                
                <div class="legend-section">
                    <h4>Registered, Not Voted (Hollow)</h4>
                    <div class="legend-item">
                        <span class="legend-marker hollow red"></span>
                        <span>Republican</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-marker hollow blue"></span>
                        <span>Democratic</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-marker hollow gray"></span>
                        <span>Unknown Party</span>
                    </div>
                </div>
                
                <div class="legend-section">
                    <h4>Not Registered</h4>
                    <div class="legend-item">
                        <span class="legend-marker hollow black"></span>
                        <span>No Registered Voters</span>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(legend);
    }
    
    makeDraggable() {
        const legend = document.getElementById('colorLegend');
        const header = legend.querySelector('.legend-header');
        
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let xOffset = 0;
        let yOffset = 0;
        
        header.addEventListener('mousedown', dragStart);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', dragEnd);
        
        function dragStart(e) {
            if (e.target.classList.contains('legend-toggle') || 
                e.target.closest('.legend-toggle')) {
                return;
            }
            
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
            
            if (e.target === header || header.contains(e.target)) {
                isDragging = true;
                legend.style.cursor = 'grabbing';
            }
        }
        
        function drag(e) {
            if (isDragging) {
                e.preventDefault();
                
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                
                xOffset = currentX;
                yOffset = currentY;
                
                setTranslate(currentX, currentY, legend);
            }
        }
        
        function dragEnd(e) {
            initialX = currentX;
            initialY = currentY;
            
            isDragging = false;
            legend.style.cursor = 'grab';
        }
        
        function setTranslate(xPos, yPos, el) {
            el.style.transform = `translate3d(${xPos}px, ${yPos}px, 0)`;
        }
    }
}

function toggleLegend() {
    const content = document.getElementById('legendContent');
    const toggle = document.querySelector('.legend-toggle i');
    const legend = document.getElementById('colorLegend');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.className = 'fas fa-chevron-down';
        legend.classList.remove('collapsed');
    } else {
        content.style.display = 'none';
        toggle.className = 'fas fa-chevron-up';
        legend.classList.add('collapsed');
    }
}

// ============================================================================
// DATASET SELECTOR - UI component for selecting datasets
// ============================================================================

/**
 * DatasetSelector class manages dataset selection UI and interactions
 * Integrates with backend API to fetch available datasets and handles user selection
 */
class DatasetSelector {
    /**
     * Create a DatasetSelector instance
     * @param {Object} map - Leaflet map instance
     * @param {Function} onDatasetChange - Callback function called when dataset selection changes
     */
    constructor(map, onDatasetChange) {
        this.map = map;
        this.onDatasetChange = onDatasetChange;
        this.datasets = [];
        this.currentDatasetIndex = null;
        this.selectElement = null;
        this.errorElement = null;
    }
    
    /**
     * Load available datasets from backend API
     * Handles API errors gracefully with user-friendly error messages
     * @returns {Promise<Array>} Array of dataset objects
     */
    async loadDatasets() {
        try {
            const response = await fetch('/admin/list-datasets');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (!data.success || !Array.isArray(data.datasets)) {
                throw new Error('Invalid response format from server');
            }
            
            this.datasets = data.datasets;
            console.log(`DatasetSelector: Loaded ${this.datasets.length} datasets`);
            
            return this.datasets;
            
        } catch (error) {
            console.error('DatasetSelector: Failed to load datasets:', error);
            this.showError('Unable to load datasets. Please refresh the page.');
            return [];
        }
    }
    
    /**
     * Populate dropdown with dataset options
     * Groups datasets by year, election type, and voting method
     * @param {Array} datasets - Array of dataset objects
     */
    populateDropdown(datasets) {
        if (!this.selectElement) {
            console.error('DatasetSelector: Select element not found');
            return;
        }
        
        // Clear existing options
        this.selectElement.innerHTML = '';
        
        if (!datasets || datasets.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No datasets available';
            this.selectElement.appendChild(option);
            this.selectElement.disabled = true;
            return;
        }
        
        // Group datasets by year (descending), then by election type, then by voting method
        const grouped = this.groupDatasets(datasets);
        
        // Populate dropdown with grouped options
        datasets.forEach((dataset, index) => {
            const option = document.createElement('option');
            option.value = index;
            
            // Format label with metadata
            const votingMethodLabel = dataset.votingMethod === 'election-day' ? 'Election Day' : 'Early Voting';
            const electionTypeLabel = dataset.electionType.charAt(0).toUpperCase() + dataset.electionType.slice(1);
            
            option.textContent = `${dataset.county} ${dataset.year} ${electionTypeLabel} - ${votingMethodLabel}`;
            
            // Add metadata as data attributes for easy access
            option.dataset.county = dataset.county;
            option.dataset.year = dataset.year;
            option.dataset.electionType = dataset.electionType;
            option.dataset.electionDate = dataset.electionDate;
            option.dataset.votingMethod = dataset.votingMethod;
            
            this.selectElement.appendChild(option);
        });
        
        this.selectElement.disabled = false;
        
        // Sync with inline selector in Data Options panel
        if (typeof syncInlineDatasetSelector === 'function') {
            syncInlineDatasetSelector();
        }
        
        // Add change event listener
        this.selectElement.addEventListener('change', (e) => {
            const index = parseInt(e.target.value, 10);
            if (!isNaN(index)) {
                this.handleSelection(index);
            }
        });
    }
    
    /**
     * Group datasets by year, election type, and voting method
     * @param {Array} datasets - Array of dataset objects
     * @returns {Object} Grouped datasets object
     */
    groupDatasets(datasets) {
        const grouped = {};
        
        datasets.forEach(dataset => {
            const year = dataset.year;
            const electionType = dataset.electionType;
            const votingMethod = dataset.votingMethod;
            
            if (!grouped[year]) {
                grouped[year] = {};
            }
            
            if (!grouped[year][electionType]) {
                grouped[year][electionType] = {};
            }
            
            if (!grouped[year][electionType][votingMethod]) {
                grouped[year][electionType][votingMethod] = [];
            }
            
            grouped[year][electionType][votingMethod].push(dataset);
        });
        
        return grouped;
    }
    
    /**
     * Handle user selection of a dataset
     * Updates current selection and triggers callback
     * @param {number} datasetIndex - Index of selected dataset in datasets array
     */
    handleSelection(datasetIndex) {
        try {
            if (datasetIndex < 0 || datasetIndex >= this.datasets.length) {
                throw new Error(`Invalid dataset index: ${datasetIndex}`);
            }
            
            const dataset = this.datasets[datasetIndex];
            this.currentDatasetIndex = datasetIndex;
            
            console.log(`DatasetSelector: Selected dataset at index ${datasetIndex}:`, dataset);
            
            // Update dataset info display
            this.updateDatasetInfo(dataset);
            
            // Sync with inline selector in Data Options panel
            if (typeof syncInlineDatasetSelector === 'function') {
                syncInlineDatasetSelector();
            }
            
            // Clear any previous errors
            this.clearError();
            
            // Trigger callback with selected dataset
            if (this.onDatasetChange) {
                this.onDatasetChange(dataset, datasetIndex);
            }
            
        } catch (error) {
            console.error('DatasetSelector: Error handling selection:', error);
            this.showError(`Failed to select dataset: ${error.message}`);
        }
    }
    
    /**
     * Get the currently selected dataset
     * @returns {Object|null} Current dataset object or null if none selected
     */
    getCurrentDataset() {
        if (this.currentDatasetIndex !== null && this.currentDatasetIndex >= 0 && this.currentDatasetIndex < this.datasets.length) {
            return this.datasets[this.currentDatasetIndex];
        }
        return null;
    }
    
    /**
     * Restore saved dataset selection from localStorage
     * Falls back to first dataset if saved selection is unavailable
     */
    restoreSavedSelection() {
        try {
            const savedIndex = localStorage.getItem('selectedDatasetIndex');
            
            if (savedIndex !== null) {
                const index = parseInt(savedIndex, 10);
                
                // Validate saved index
                if (!isNaN(index) && index >= 0 && index < this.datasets.length) {
                    console.log(`DatasetSelector: Restoring saved selection at index ${index}`);
                    this.selectElement.value = index;
                    this.handleSelection(index);
                    return;
                } else {
                    console.info('DatasetSelector: Saved dataset no longer available, using first dataset');
                    localStorage.removeItem('selectedDatasetIndex');
                }
            }
            
            // Fallback to first dataset
            if (this.datasets.length > 0) {
                console.log('DatasetSelector: No saved selection, using first dataset');
                this.selectElement.value = 0;
                this.handleSelection(0);
            }
            
        } catch (error) {
            console.warn('DatasetSelector: Error restoring saved selection:', error);
            
            // Fallback to first dataset on error
            if (this.datasets.length > 0) {
                this.selectElement.value = 0;
                this.handleSelection(0);
            }
        }
    }
    
    /**
     * Update dataset info display with metadata
     * @param {Object} dataset - Dataset object with metadata
     */
    updateDatasetInfo(dataset) {
        const countyElement = document.getElementById('dataset-county');
        const yearElement = document.getElementById('dataset-year');
        const typeElement = document.getElementById('dataset-type');
        
        if (countyElement) {
            countyElement.textContent = dataset.county || '';
        }
        
        if (yearElement) {
            yearElement.textContent = dataset.year || '';
        }
        
        if (typeElement) {
            const electionTypeLabel = dataset.electionType ? 
                dataset.electionType.charAt(0).toUpperCase() + dataset.electionType.slice(1) : '';
            const votingMethodLabel = dataset.votingMethod === 'election-day' ? 'Election Day' : 'Early Voting';
            typeElement.textContent = `${electionTypeLabel} - ${votingMethodLabel}`;
        }
    }
    
    /**
     * Show error message to user
     * @param {string} message - Error message to display
     */
    showError(message) {
        if (!this.errorElement) {
            // Create error element if it doesn't exist
            this.errorElement = document.createElement('div');
            this.errorElement.className = 'dataset-selector-error';
            
            const container = document.querySelector('.dataset-selector-control');
            if (container) {
                container.appendChild(this.errorElement);
            }
        }
        
        this.errorElement.textContent = message;
        this.errorElement.style.display = 'block';
    }
    
    /**
     * Clear error message display
     */
    clearError() {
        if (this.errorElement) {
            this.errorElement.style.display = 'none';
            this.errorElement.textContent = '';
        }
    }
    
    /**
     * Initialize the DatasetSelector
     * Sets up DOM references and loads datasets
     * @returns {Promise<void>}
     */
    async initialize() {
        // Get DOM references
        this.selectElement = document.getElementById('dataset-selector');
        
        if (!this.selectElement) {
            console.error('DatasetSelector: Could not find dataset-selector element');
            return;
        }
        
        // Load datasets from API
        const datasets = await this.loadDatasets();
        
        if (datasets.length > 0) {
            // Populate dropdown
            this.populateDropdown(datasets);
            
            // Restore saved selection or select first dataset
            this.restoreSavedSelection();
        }
    }
}

// ============================================================================
// PARTY FILTER - UI component for filtering voters by party affiliation
// ============================================================================

/**
 * PartyFilter class manages party affiliation filtering for primary elections
 * Provides three filter options: Show All, Show Republican Only, Show Democratic Only
 * Hidden by default and only shown for primary election datasets
 */
class PartyFilter {
    /**
     * Create a PartyFilter instance
     * @param {Object} map - Leaflet map instance
     * @param {Function} onFilterChange - Callback function called when filter selection changes
     */
    constructor(map, onFilterChange) {
        this.map = map;
        this.onFilterChange = onFilterChange;
        this.currentFilter = 'all'; // Default filter value
        this.controlElement = null;
        this.buttons = {};
    }
    
    /**
     * Show or hide the party filter control based on election type
     * @param {boolean} isPrimaryElection - True if current dataset is a primary election
     */
    setVisible(isPrimaryElection) {
        if (!this.controlElement) {
            this.controlElement = document.querySelector('.party-filter-control');
        }
        
        if (!this.controlElement) {
            console.warn('PartyFilter: Control element not found');
            return;
        }
        
        if (isPrimaryElection) {
            this.controlElement.style.display = 'block';
            console.log('PartyFilter: Showing filter for primary election');
            
            // Show inline party filter in Data Options panel
            if (typeof setInlinePartyFilterVisibility === 'function') {
                setInlinePartyFilterVisibility(true);
            }
        } else {
            this.controlElement.style.display = 'none';
            console.log('PartyFilter: Hiding filter for non-primary election');
            
            // Hide inline party filter in Data Options panel
            if (typeof setInlinePartyFilterVisibility === 'function') {
                setInlinePartyFilterVisibility(false);
            }
        }
    }
    
    /**
     * Handle filter selection change
     * Updates active button state, saves to localStorage, and triggers callback
     * @param {string} filterValue - Filter value: "all", "republican", or "democratic"
     */
    handleFilterChange(filterValue) {
        try {
            // Validate filter value
            const validFilters = ['all', 'republican', 'democratic'];
            if (!validFilters.includes(filterValue)) {
                throw new Error(`Invalid filter value: ${filterValue}`);
            }
            
            this.currentFilter = filterValue;
            console.log(`PartyFilter: Filter changed to ${filterValue}`);
            
            // Update button active states
            this.updateButtonStates(filterValue);
            
            // Sync with inline party filter in Data Options panel
            if (typeof syncInlinePartyFilter === 'function') {
                syncInlinePartyFilter(filterValue);
            }
            
            // Save to localStorage
            this.saveFilter();
            
            // Trigger callback
            if (this.onFilterChange) {
                this.onFilterChange(filterValue);
            }
            
        } catch (error) {
            console.error('PartyFilter: Error handling filter change:', error);
        }
    }
    
    /**
     * Update active state of filter buttons
     * @param {string} activeFilter - The currently active filter value
     */
    updateButtonStates(activeFilter) {
        // Get all filter buttons
        const buttons = document.querySelectorAll('.party-filter-btn');
        
        buttons.forEach(button => {
            const filterValue = button.dataset.filter;
            
            if (filterValue === activeFilter) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
    }
    
    /**
     * Get the current filter value
     * @returns {string} Current filter value: "all", "republican", or "democratic"
     */
    getCurrentFilter() {
        return this.currentFilter;
    }
    
    /**
     * Restore saved filter selection from localStorage
     * Defaults to "all" if no saved selection exists
     */
    restoreSavedFilter() {
        try {
            const savedFilter = localStorage.getItem('partyFilter');
            
            if (savedFilter !== null) {
                const validFilters = ['all', 'republican', 'democratic'];
                
                if (validFilters.includes(savedFilter)) {
                    console.log(`PartyFilter: Restoring saved filter: ${savedFilter}`);
                    this.currentFilter = savedFilter;
                    this.updateButtonStates(savedFilter);
                    return savedFilter;
                } else {
                    console.warn(`PartyFilter: Invalid saved filter value: ${savedFilter}, using default`);
                    localStorage.removeItem('partyFilter');
                }
            }
            
            // Default to "all"
            console.log('PartyFilter: No saved filter, using default "all"');
            this.currentFilter = 'all';
            this.updateButtonStates('all');
            return 'all';
            
        } catch (error) {
            console.warn('PartyFilter: Error restoring saved filter:', error);
            
            // Fallback to default
            this.currentFilter = 'all';
            this.updateButtonStates('all');
            return 'all';
        }
    }
    
    /**
     * Save current filter selection to localStorage
     */
    saveFilter() {
        try {
            localStorage.setItem('partyFilter', this.currentFilter);
            console.log(`PartyFilter: Saved filter to localStorage: ${this.currentFilter}`);
        } catch (error) {
            console.warn('PartyFilter: Failed to save filter to localStorage:', error);
            // Continue without persistence - non-critical feature
        }
    }
    
    /**
     * Initialize the PartyFilter
     * Sets up event listeners for filter buttons
     */
    initialize() {
        // Get DOM reference
        this.controlElement = document.querySelector('.party-filter-control');
        
        if (!this.controlElement) {
            console.error('PartyFilter: Could not find party-filter-control element');
            return;
        }
        
        // Get all filter buttons
        const buttons = document.querySelectorAll('.party-filter-btn');
        
        // Add click event listeners
        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                const filterValue = button.dataset.filter;
                if (filterValue) {
                    this.handleFilterChange(filterValue);
                }
            });
        });
        
        // Restore saved filter
        this.restoreSavedFilter();
        
        console.log('PartyFilter: Initialized');
    }
}
