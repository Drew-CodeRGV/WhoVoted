/**
 * Three-Dropdown Dataset Selector
 * Simplified approach: County → Year → Voting Method
 */

class DatasetSelectorV2 {
    constructor(map, onDatasetChange) {
        this.map = map;
        this.onDatasetChange = onDatasetChange;
        this.allDatasets = [];
        this.currentCounty = null;
        this.currentYear = null;
        this.currentMethod = null;
        
        // DOM elements
        this.countySelect = null;
        this.yearSelect = null;
        this.methodSelect = null;
    }
    
    /**
     * Initialize the selector
     */
    async initialize(detectedCounty) {
        // Get DOM elements
        this.countySelect = document.getElementById('countyDropdown');
        this.yearSelect = document.getElementById('year-selector');
        this.methodSelect = document.getElementById('voting-method-selector');
        
        if (!this.countySelect || !this.yearSelect || !this.methodSelect) {
            console.error('DatasetSelectorV2: Required elements not found');
            return;
        }
        
        // Load all datasets
        await this.loadAllDatasets();
        
        // Populate county dropdown
        this.populateCountyDropdown();
        
        // Set initial county
        this.currentCounty = detectedCounty || 'Hidalgo';
        
        // Set the dropdown value
        this.countySelect.value = this.currentCounty;
        
        // If the value didn't stick (county not in list), try to find it
        if (this.countySelect.value !== this.currentCounty) {
            // County might not exist, default to first available or 'all'
            if (this.countySelect.options.length > 1) {
                this.currentCounty = this.countySelect.options[1].value; // Skip "All Counties"
                this.countySelect.value = this.currentCounty;
            } else {
                this.currentCounty = 'all';
                this.countySelect.value = 'all';
            }
        }
        
        console.log(`DatasetSelectorV2: Selected county: ${this.currentCounty}`);
        
        // Populate year dropdown
        this.populateYearDropdown();
        
        // Set up event listeners
        this.countySelect.addEventListener('change', () => this.onCountyChange());
        this.yearSelect.addEventListener('change', () => this.onYearChange());
        this.methodSelect.addEventListener('change', () => this.onMethodChange());
        
        console.log('DatasetSelectorV2: Initialized');
    }
    
    /**
     * Populate county dropdown from all datasets
     */
    populateCountyDropdown() {
        // Extract unique counties from all datasets
        const countiesSet = new Set();
        this.allDatasets.forEach(ds => {
            const counties = ds.counties || [ds.county];
            counties.forEach(c => countiesSet.add(c));
        });
        
        const counties = Array.from(countiesSet).sort();
        
        // Clear and repopulate
        this.countySelect.innerHTML = '<option value="all">All Counties</option>';
        counties.forEach(county => {
            const option = document.createElement('option');
            option.value = county;
            option.textContent = county;
            this.countySelect.appendChild(option);
        });
        
        console.log(`DatasetSelectorV2: Populated ${counties.length} counties`);
    }
    
    /**
     * Load all datasets from API
     */
    async loadAllDatasets() {
        try {
            const response = await fetch('/api/elections');
            const data = await response.json();
            
            if (!data.success || !Array.isArray(data.elections)) {
                throw new Error('Invalid API response');
            }
            
            // Transform to simpler format
            this.allDatasets = data.elections.map(e => ({
                county: e.county,
                counties: e.counties || [e.county],
                year: e.electionYear,
                electionDate: e.electionDate,
                electionType: e.electionType,
                votingMethod: e.votingMethod,
                votingMethods: e.votingMethods || [],
                parties: e.parties || [],
                totalVoters: e.totalVoters,
                totalAddresses: e.totalVoters, // Alias for compatibility
                rawVoterCount: e.totalVoters,
                geocodedCount: e.geocodedCount,
                methodBreakdown: e.methodBreakdown || {},
                countyBreakdown: e.countyBreakdown || {},
                lastUpdated: e.lastUpdated,
                selectedCounties: (e.counties || [e.county]).slice(),
                dbDriven: true,
            }));
            
            console.log(`DatasetSelectorV2: Loaded ${this.allDatasets.length} datasets`);
        } catch (error) {
            console.error('DatasetSelectorV2: Failed to load datasets:', error);
            this.allDatasets = [];
        }
    }
    
    /**
     * Get datasets filtered by current county
     */
    getCountyDatasets() {
        if (!this.currentCounty || this.currentCounty === 'all') {
            return this.allDatasets;
        }
        
        return this.allDatasets.filter(ds => {
            const counties = ds.counties || [ds.county];
            return counties.includes(this.currentCounty);
        });
    }
    
    /**
     * Populate year dropdown based on current county
     */
    populateYearDropdown() {
        const datasets = this.getCountyDatasets();
        
        // Extract unique years, sorted descending
        const years = [...new Set(datasets.map(ds => ds.year))].sort((a, b) => b.localeCompare(a));
        
        this.yearSelect.innerHTML = '';
        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            this.yearSelect.appendChild(option);
        });
        
        // Select most recent year
        if (years.length > 0) {
            this.currentYear = years[0];
            this.yearSelect.value = this.currentYear;
            this.populateMethodDropdown();
        }
    }
    
    /**
     * Populate voting method dropdown based on current county + year
     */
    populateMethodDropdown() {
        const datasets = this.getCountyDatasets().filter(ds => ds.year === this.currentYear);
        
        this.methodSelect.innerHTML = '';
        
        // Check if combined dataset exists
        const hasCombined = datasets.some(ds => ds.votingMethod === 'combined');
        
        if (hasCombined) {
            const option = document.createElement('option');
            option.value = 'combined';
            option.textContent = 'Complete Election';
            this.methodSelect.appendChild(option);
        }
        
        // Add individual methods
        const methods = [
            { value: 'early-voting', label: 'Early Voting' },
            { value: 'election-day', label: 'Election Day' },
            { value: 'mail-in', label: 'Mail-In' }
        ];
        
        methods.forEach(method => {
            if (datasets.some(ds => ds.votingMethod === method.value)) {
                const option = document.createElement('option');
                option.value = method.value;
                option.textContent = method.label;
                this.methodSelect.appendChild(option);
            }
        });
        
        // Default to combined if available, otherwise first option
        this.currentMethod = hasCombined ? 'combined' : (this.methodSelect.options[0]?.value || null);
        if (this.currentMethod) {
            this.methodSelect.value = this.currentMethod;
            this.loadCurrentDataset();
        }
    }
    
    /**
     * Load the currently selected dataset
     */
    loadCurrentDataset() {
        const datasets = this.getCountyDatasets();
        const dataset = datasets.find(ds => 
            ds.year === this.currentYear && 
            ds.votingMethod === this.currentMethod
        );
        
        if (dataset && this.onDatasetChange) {
            // Create a modified dataset with only the selected county
            const modifiedDataset = {
                ...dataset,
                // Override selectedCounties to only include the current county
                selectedCounties: this.currentCounty === 'all' 
                    ? (dataset.counties || [dataset.county])
                    : [this.currentCounty],
                // Update county field to reflect the selected county
                county: this.currentCounty === 'all' 
                    ? dataset.county 
                    : this.currentCounty
            };
            
            console.log('DatasetSelectorV2: Loading dataset:', {
                county: this.currentCounty,
                year: this.currentYear,
                method: this.currentMethod,
                voters: dataset.totalVoters,
                selectedCounties: modifiedDataset.selectedCounties
            });
            
            // Update method breakdown display
            this.updateMethodBreakdown(dataset);
            
            // Zoom to the selected county if not "all"
            if (this.currentCounty !== 'all' && typeof zoomToCounty === 'function') {
                zoomToCounty(this.currentCounty);
            }
            
            this.onDatasetChange(modifiedDataset);
        }
    }
    
    /**
     * Update method breakdown display for combined datasets
     */
    updateMethodBreakdown(dataset) {
        let breakdownElement = document.getElementById('dataset-method-breakdown');
        
        if (dataset.votingMethod === 'combined' && dataset.methodBreakdown) {
            if (!breakdownElement) {
                breakdownElement = document.createElement('div');
                breakdownElement.id = 'dataset-method-breakdown';
                this.methodSelect.parentNode.appendChild(breakdownElement);
            }
            
            breakdownElement.style.cssText = 'display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; font-size: 11px;';
            
            const breakdown = dataset.methodBreakdown;
            const parts = [];
            
            if (breakdown['early-voting']) {
                parts.push(`Early: ${breakdown['early-voting'].totalVoters.toLocaleString()}`);
            }
            if (breakdown['mail-in']) {
                parts.push(`Mail-In: ${breakdown['mail-in'].totalVoters.toLocaleString()}`);
            }
            if (breakdown['election-day']) {
                parts.push(`Election Day: ${breakdown['election-day'].totalVoters.toLocaleString()}`);
            }
            
            breakdownElement.innerHTML = parts.map(part => 
                `<span style="padding: 3px 6px; background: #e8f4f8; border-radius: 4px; color: #0066cc; font-weight: 500;">${part}</span>`
            ).join('');
            breakdownElement.style.display = 'flex';
        } else if (breakdownElement) {
            breakdownElement.style.display = 'none';
        }
    }
    
    /**
     * Handle county change
     */
    onCountyChange() {
        this.currentCounty = this.countySelect.value;
        console.log('DatasetSelectorV2: County changed to', this.currentCounty);
        
        // CRITICAL: Update global county filter variable FIRST
        // This is used by loadDataset() and _fetchAndDisplayStats()
        if (typeof window.selectedCountyFilter !== 'undefined') {
            window.selectedCountyFilter = this.currentCounty;
        } else {
            window.selectedCountyFilter = this.currentCounty;
        }
        
        this.populateYearDropdown();
    }
    
    /**
     * Handle year change
     */
    onYearChange() {
        this.currentYear = this.yearSelect.value;
        console.log('DatasetSelectorV2: Year changed to', this.currentYear);
        this.populateMethodDropdown();
    }
    
    /**
     * Handle method change
     */
    onMethodChange() {
        this.currentMethod = this.methodSelect.value;
        console.log('DatasetSelectorV2: Method changed to', this.currentMethod);
        this.loadCurrentDataset();
    }
}

// Export for use in main app
window.DatasetSelectorV2 = DatasetSelectorV2;
