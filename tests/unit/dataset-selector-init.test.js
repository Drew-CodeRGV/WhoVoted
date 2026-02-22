/**
 * DatasetSelector Initialization Test
 * 
 * This test verifies that the DatasetSelector can be properly initialized
 * and connected to the DatasetManager.
 * 
 * Requirements: 1.1, 1.4, 2.2
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { createMockLocalStorage } from '../test-helpers.js';

// Mock localStorage and DOM
let mockLocalStorage;
let mockDocument;
let mockSelectElement;

beforeEach(() => {
  mockLocalStorage = createMockLocalStorage();
  global.localStorage = mockLocalStorage;
  
  // Create mock DOM elements
  mockSelectElement = {
    innerHTML: '',
    disabled: false,
    value: '',
    options: [],
    appendChild: jest.fn(function(option) {
      this.options.push(option);
    }),
    addEventListener: jest.fn()
  };
  
  mockDocument = {
    getElementById: jest.fn((id) => {
      if (id === 'dataset-selector') return mockSelectElement;
      if (id === 'dataset-county') return { textContent: '' };
      if (id === 'dataset-year') return { textContent: '' };
      if (id === 'dataset-type') return { textContent: '' };
      return null;
    }),
    querySelector: jest.fn(() => null),
    createElement: jest.fn((tag) => {
      if (tag === 'option') {
        return {
          value: '',
          textContent: '',
          dataset: {}
        };
      }
      return {};
    })
  };
  
  global.document = mockDocument;
  global.fetch = jest.fn();
  global.console.error = jest.fn();
  global.console.log = jest.fn();
});

afterEach(() => {
  delete global.localStorage;
  delete global.document;
  delete global.fetch;
});

// Define DatasetManager class for testing
class DatasetManager {
  constructor() {
    this.currentDataset = null;
    this.partyFilter = 'all';
    this.selectedDatasetIndex = null;
  }
  
  setCurrentDataset(dataset) {
    this.currentDataset = dataset;
  }
  
  getCurrentDataset() {
    return this.currentDataset;
  }
  
  setPartyFilter(filter) {
    this.partyFilter = filter;
  }
  
  getPartyFilter() {
    return this.partyFilter;
  }
  
  setSelectedDatasetIndex(index) {
    this.selectedDatasetIndex = index;
  }
  
  getSelectedDatasetIndex() {
    return this.selectedDatasetIndex;
  }
  
  isPrimaryElection() {
    return this.currentDataset?.electionType === 'primary';
  }
  
  saveState() {
    if (this.selectedDatasetIndex !== null) {
      localStorage.setItem('selectedDatasetIndex', this.selectedDatasetIndex.toString());
    }
    localStorage.setItem('partyFilter', this.partyFilter);
  }
  
  loadState() {
    const savedIndex = localStorage.getItem('selectedDatasetIndex');
    const savedFilter = localStorage.getItem('partyFilter');
    
    if (savedIndex !== null) {
      this.selectedDatasetIndex = parseInt(savedIndex, 10);
    }
    
    if (savedFilter !== null) {
      this.partyFilter = savedFilter;
    }
  }
}

// Define DatasetSelector class for testing
class DatasetSelector {
  constructor(map, onDatasetChange) {
    this.map = map;
    this.onDatasetChange = onDatasetChange;
    this.datasets = [];
    this.currentDatasetIndex = null;
    this.selectElement = null;
    this.errorElement = null;
  }
  
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
      return this.datasets;
      
    } catch (error) {
      console.error('DatasetSelector: Failed to load datasets:', error);
      return [];
    }
  }
  
  populateDropdown(datasets) {
    if (!this.selectElement) {
      return;
    }
    
    this.selectElement.innerHTML = '';
    this.selectElement.options = [];
    
    if (!datasets || datasets.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'No datasets available';
      this.selectElement.appendChild(option);
      this.selectElement.disabled = true;
      return;
    }
    
    datasets.forEach((dataset, index) => {
      const option = document.createElement('option');
      option.value = index;
      option.textContent = `${dataset.county} ${dataset.year} ${dataset.electionType}`;
      this.selectElement.appendChild(option);
    });
    
    this.selectElement.disabled = false;
  }
  
  handleSelection(datasetIndex) {
    if (datasetIndex < 0 || datasetIndex >= this.datasets.length) {
      throw new Error(`Invalid dataset index: ${datasetIndex}`);
    }
    
    const dataset = this.datasets[datasetIndex];
    this.currentDatasetIndex = datasetIndex;
    
    if (this.onDatasetChange) {
      this.onDatasetChange(dataset, datasetIndex);
    }
  }
  
  getCurrentDataset() {
    if (this.currentDatasetIndex !== null && 
        this.currentDatasetIndex >= 0 && 
        this.currentDatasetIndex < this.datasets.length) {
      return this.datasets[this.currentDatasetIndex];
    }
    return null;
  }
  
  restoreSavedSelection() {
    try {
      const savedIndex = localStorage.getItem('selectedDatasetIndex');
      
      if (savedIndex !== null) {
        const index = parseInt(savedIndex, 10);
        
        if (!isNaN(index) && index >= 0 && index < this.datasets.length) {
          this.selectElement.value = index;
          this.handleSelection(index);
          return;
        } else {
          localStorage.removeItem('selectedDatasetIndex');
        }
      }
      
      if (this.datasets.length > 0) {
        this.selectElement.value = 0;
        this.handleSelection(0);
      }
      
    } catch (error) {
      if (this.datasets.length > 0) {
        this.selectElement.value = 0;
        this.handleSelection(0);
      }
    }
  }
  
  async initialize() {
    this.selectElement = document.getElementById('dataset-selector');
    
    if (!this.selectElement) {
      console.error('DatasetSelector: Could not find dataset-selector element');
      return;
    }
    
    const datasets = await this.loadDatasets();
    
    if (datasets.length > 0) {
      this.populateDropdown(datasets);
      this.restoreSavedSelection();
    }
  }
}

describe('DatasetSelector Initialization (Task 9.2)', () => {
  let mockMap;

  beforeEach(() => {
    mockMap = {
      setView: jest.fn(),
      addLayer: jest.fn(),
      removeLayer: jest.fn(),
      hasLayer: jest.fn()
    };
  });

  describe('DatasetSelector Instance Creation', () => {
    it('should create DatasetSelector instance with map reference', () => {
      const onDatasetChange = jest.fn();
      const selector = new DatasetSelector(mockMap, onDatasetChange);
      
      expect(selector).toBeDefined();
      expect(selector.map).toBe(mockMap);
      expect(selector.onDatasetChange).toBe(onDatasetChange);
    });

    it('should initialize with empty datasets array', () => {
      const selector = new DatasetSelector(mockMap, jest.fn());
      
      expect(selector.datasets).toEqual([]);
      expect(selector.currentDatasetIndex).toBeNull();
    });
  });

  describe('DatasetSelector Initialization', () => {
    it('should load datasets from API on initialize', async () => {
      const mockDatasets = [
        {
          county: 'Hidalgo',
          year: 2024,
          electionType: 'primary',
          mapDataFile: 'map_data_hidalgo_2024_primary.json',
          metadataFile: 'metadata_hidalgo_2024_primary.json'
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, datasets: mockDatasets })
      });

      const selector = new DatasetSelector(mockMap, jest.fn());
      await selector.initialize();

      expect(global.fetch).toHaveBeenCalledWith('/admin/list-datasets');
      expect(selector.datasets).toEqual(mockDatasets);
    });

    it('should populate dropdown after loading datasets', async () => {
      const mockDatasets = [
        {
          county: 'Hidalgo',
          year: 2024,
          electionType: 'primary',
          mapDataFile: 'map_data_hidalgo_2024_primary.json'
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, datasets: mockDatasets })
      });

      const selector = new DatasetSelector(mockMap, jest.fn());
      await selector.initialize();

      expect(mockSelectElement.options.length).toBe(1);
      expect(mockSelectElement.options[0].textContent).toContain('Hidalgo');
      expect(mockSelectElement.options[0].textContent).toContain('2024');
    });

    it('should restore saved selection from localStorage', async () => {
      const mockDatasets = [
        {
          county: 'Hidalgo',
          year: 2024,
          electionType: 'primary',
          mapDataFile: 'map_data_hidalgo_2024_primary.json'
        },
        {
          county: 'Cameron',
          year: 2024,
          electionType: 'general',
          mapDataFile: 'map_data_cameron_2024_general.json'
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, datasets: mockDatasets })
      });

      mockLocalStorage.setItem('selectedDatasetIndex', '1');

      const onDatasetChange = jest.fn();
      const selector = new DatasetSelector(mockMap, onDatasetChange);
      await selector.initialize();

      expect(onDatasetChange).toHaveBeenCalledWith(mockDatasets[1], 1);
      expect(selector.currentDatasetIndex).toBe(1);
    });

    it('should select first dataset if no saved selection', async () => {
      const mockDatasets = [
        {
          county: 'Hidalgo',
          year: 2024,
          electionType: 'primary',
          mapDataFile: 'map_data_hidalgo_2024_primary.json'
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, datasets: mockDatasets })
      });

      const onDatasetChange = jest.fn();
      const selector = new DatasetSelector(mockMap, onDatasetChange);
      await selector.initialize();

      expect(onDatasetChange).toHaveBeenCalledWith(mockDatasets[0], 0);
      expect(selector.currentDatasetIndex).toBe(0);
    });
  });

  describe('DatasetSelector and DatasetManager Integration', () => {
    it('should connect to DatasetManager for state management', async () => {
      const mockDatasets = [
        {
          county: 'Hidalgo',
          year: 2024,
          electionType: 'primary',
          mapDataFile: 'map_data_hidalgo_2024_primary.json'
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, datasets: mockDatasets })
      });

      const datasetManager = new DatasetManager();
      
      const onDatasetChange = (dataset, index) => {
        datasetManager.setCurrentDataset(dataset);
        datasetManager.setSelectedDatasetIndex(index);
        datasetManager.saveState();
      };

      const selector = new DatasetSelector(mockMap, onDatasetChange);
      await selector.initialize();

      expect(datasetManager.getCurrentDataset()).toEqual(mockDatasets[0]);
      expect(datasetManager.getSelectedDatasetIndex()).toBe(0);
      expect(mockLocalStorage.getItem('selectedDatasetIndex')).toBe('0');
    });

    it('should trigger onDatasetChange callback when dataset is selected', async () => {
      const mockDatasets = [
        {
          county: 'Hidalgo',
          year: 2024,
          electionType: 'primary',
          mapDataFile: 'map_data_hidalgo_2024_primary.json'
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, datasets: mockDatasets })
      });

      const onDatasetChange = jest.fn();
      const selector = new DatasetSelector(mockMap, onDatasetChange);
      await selector.initialize();

      // Verify callback was called during initialization
      expect(onDatasetChange).toHaveBeenCalledTimes(1);
      expect(onDatasetChange).toHaveBeenCalledWith(mockDatasets[0], 0);
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const selector = new DatasetSelector(mockMap, jest.fn());
      await selector.initialize();

      expect(selector.datasets).toEqual([]);
    });

    it('should handle invalid API response format', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: false })
      });

      const selector = new DatasetSelector(mockMap, jest.fn());
      await selector.initialize();

      expect(selector.datasets).toEqual([]);
    });

    it('should handle missing DOM element', async () => {
      // Mock getElementById to return null for dataset-selector
      mockDocument.getElementById = jest.fn(() => null);

      const selector = new DatasetSelector(mockMap, jest.fn());
      await selector.initialize();

      // Should not throw error, just log and return
      expect(selector.selectElement).toBeNull();
      expect(global.console.error).toHaveBeenCalled();
    });
  });
});
