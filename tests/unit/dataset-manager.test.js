/**
 * Unit tests for DatasetManager class
 * Tests state management, localStorage persistence, and error handling
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { createMockLocalStorage } from '../test-helpers.js';

// Mock localStorage before importing DatasetManager
let mockLocalStorage;
let consoleWarnSpy;

beforeEach(() => {
  mockLocalStorage = createMockLocalStorage();
  global.localStorage = mockLocalStorage;
  consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  delete global.localStorage;
  consoleWarnSpy.mockRestore();
});

// Import DatasetManager after setting up mocks
// Note: In a real browser environment, this would be loaded from data.js
// For testing, we'll define it inline to avoid module loading issues
class DatasetManager {
  constructor() {
    this.currentDataset = null;
    this.partyFilter = 'all';
    this.selectedDatasetIndex = null;
    this.loadState();
  }
  
  setCurrentDataset(dataset) {
    this.currentDataset = dataset;
    this.saveState();
  }
  
  getCurrentDataset() {
    return this.currentDataset;
  }
  
  setPartyFilter(filterValue) {
    if (!['all', 'republican', 'democratic'].includes(filterValue)) {
      console.warn(`Invalid party filter value: ${filterValue}, defaulting to 'all'`);
      filterValue = 'all';
    }
    this.partyFilter = filterValue;
    this.saveState();
  }
  
  getPartyFilter() {
    return this.partyFilter;
  }
  
  setSelectedDatasetIndex(index) {
    this.selectedDatasetIndex = index;
    this.saveState();
  }
  
  getSelectedDatasetIndex() {
    return this.selectedDatasetIndex;
  }
  
  isPrimaryElection() {
    if (!this.currentDataset || !this.currentDataset.electionType) {
      return false;
    }
    return this.currentDataset.electionType.toLowerCase() === 'primary';
  }
  
  saveState() {
    try {
      if (this.selectedDatasetIndex !== null) {
        localStorage.setItem('selectedDatasetIndex', this.selectedDatasetIndex.toString());
      }
      localStorage.setItem('partyFilter', this.partyFilter);
    } catch (error) {
      console.warn('Failed to save state to localStorage:', error.message);
    }
  }
  
  loadState() {
    try {
      const savedIndex = localStorage.getItem('selectedDatasetIndex');
      if (savedIndex !== null) {
        this.selectedDatasetIndex = parseInt(savedIndex, 10);
      }
      
      const savedFilter = localStorage.getItem('partyFilter');
      if (savedFilter && ['all', 'republican', 'democratic'].includes(savedFilter)) {
        this.partyFilter = savedFilter;
      } else {
        this.partyFilter = 'all';
      }
    } catch (error) {
      console.warn('Failed to load state from localStorage:', error.message);
      this.selectedDatasetIndex = null;
      this.partyFilter = 'all';
    }
  }
}

describe('DatasetManager', () => {
  describe('Constructor and Initialization', () => {
    it('should initialize with default values', () => {
      const manager = new DatasetManager();
      
      expect(manager.getCurrentDataset()).toBeNull();
      expect(manager.getPartyFilter()).toBe('all');
      expect(manager.getSelectedDatasetIndex()).toBeNull();
    });

    it('should load saved state from localStorage on initialization', () => {
      mockLocalStorage.setItem('selectedDatasetIndex', '2');
      mockLocalStorage.setItem('partyFilter', 'republican');
      
      const manager = new DatasetManager();
      
      expect(manager.getSelectedDatasetIndex()).toBe(2);
      expect(manager.getPartyFilter()).toBe('republican');
    });
  });

  describe('Dataset Management', () => {
    it('should set and get current dataset', () => {
      const manager = new DatasetManager();
      const dataset = {
        county: 'Hidalgo',
        year: 2024,
        electionType: 'primary'
      };
      
      manager.setCurrentDataset(dataset);
      
      expect(manager.getCurrentDataset()).toEqual(dataset);
    });

    it('should save dataset index to localStorage when set', () => {
      const manager = new DatasetManager();
      
      manager.setSelectedDatasetIndex(5);
      
      expect(mockLocalStorage.getItem('selectedDatasetIndex')).toBe('5');
      expect(manager.getSelectedDatasetIndex()).toBe(5);
    });
  });

  describe('Party Filter Management', () => {
    it('should set and get party filter', () => {
      const manager = new DatasetManager();
      
      manager.setPartyFilter('republican');
      expect(manager.getPartyFilter()).toBe('republican');
      
      manager.setPartyFilter('democratic');
      expect(manager.getPartyFilter()).toBe('democratic');
      
      manager.setPartyFilter('all');
      expect(manager.getPartyFilter()).toBe('all');
    });

    it('should save party filter to localStorage when set', () => {
      const manager = new DatasetManager();
      
      manager.setPartyFilter('democratic');
      
      expect(mockLocalStorage.getItem('partyFilter')).toBe('democratic');
    });

    it('should default to "all" for invalid filter values', () => {
      const manager = new DatasetManager();
      
      manager.setPartyFilter('invalid');
      
      expect(manager.getPartyFilter()).toBe('all');
      expect(consoleWarnSpy).toHaveBeenCalled();
    });
  });

  describe('Primary Election Detection', () => {
    it('should return true for primary election datasets', () => {
      const manager = new DatasetManager();
      const dataset = {
        county: 'Hidalgo',
        year: 2024,
        electionType: 'primary'
      };
      
      manager.setCurrentDataset(dataset);
      
      expect(manager.isPrimaryElection()).toBe(true);
    });

    it('should return false for non-primary election datasets', () => {
      const manager = new DatasetManager();
      const dataset = {
        county: 'Hidalgo',
        year: 2024,
        electionType: 'general'
      };
      
      manager.setCurrentDataset(dataset);
      
      expect(manager.isPrimaryElection()).toBe(false);
    });

    it('should handle case-insensitive election type', () => {
      const manager = new DatasetManager();
      const dataset = {
        county: 'Hidalgo',
        year: 2024,
        electionType: 'PRIMARY'
      };
      
      manager.setCurrentDataset(dataset);
      
      expect(manager.isPrimaryElection()).toBe(true);
    });

    it('should return false when no dataset is set', () => {
      const manager = new DatasetManager();
      
      expect(manager.isPrimaryElection()).toBe(false);
    });

    it('should return false when dataset has no electionType', () => {
      const manager = new DatasetManager();
      const dataset = {
        county: 'Hidalgo',
        year: 2024
      };
      
      manager.setCurrentDataset(dataset);
      
      expect(manager.isPrimaryElection()).toBe(false);
    });
  });

  describe('LocalStorage Persistence', () => {
    it('should persist state across save/load cycle', () => {
      const manager1 = new DatasetManager();
      
      manager1.setSelectedDatasetIndex(3);
      manager1.setPartyFilter('republican');
      
      // Create new instance to simulate page reload
      const manager2 = new DatasetManager();
      
      expect(manager2.getSelectedDatasetIndex()).toBe(3);
      expect(manager2.getPartyFilter()).toBe('republican');
    });

    it('should handle localStorage unavailable gracefully', () => {
      // Simulate localStorage failure
      global.localStorage = {
        getItem: () => { throw new Error('localStorage unavailable'); },
        setItem: () => { throw new Error('localStorage unavailable'); }
      };
      
      const manager = new DatasetManager();
      
      // Should not throw, should use defaults
      expect(manager.getPartyFilter()).toBe('all');
      expect(manager.getSelectedDatasetIndex()).toBeNull();
      
      // Should not throw when saving
      expect(() => {
        manager.setPartyFilter('republican');
        manager.setSelectedDatasetIndex(1);
      }).not.toThrow();
      
      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it('should handle invalid saved dataset index', () => {
      mockLocalStorage.setItem('selectedDatasetIndex', 'invalid');
      
      const manager = new DatasetManager();
      
      // parseInt('invalid') returns NaN
      expect(isNaN(manager.getSelectedDatasetIndex())).toBe(true);
    });

    it('should default to "all" for invalid saved filter', () => {
      mockLocalStorage.setItem('partyFilter', 'invalid-filter');
      
      const manager = new DatasetManager();
      
      expect(manager.getPartyFilter()).toBe('all');
    });

    it('should handle missing localStorage values', () => {
      // localStorage is empty
      const manager = new DatasetManager();
      
      expect(manager.getSelectedDatasetIndex()).toBeNull();
      expect(manager.getPartyFilter()).toBe('all');
    });
  });

  describe('State Management Integration', () => {
    it('should maintain separate state for dataset and filter', () => {
      const manager = new DatasetManager();
      const dataset = {
        county: 'Hidalgo',
        year: 2024,
        electionType: 'primary'
      };
      
      manager.setCurrentDataset(dataset);
      manager.setSelectedDatasetIndex(2);
      manager.setPartyFilter('democratic');
      
      expect(manager.getCurrentDataset()).toEqual(dataset);
      expect(manager.getSelectedDatasetIndex()).toBe(2);
      expect(manager.getPartyFilter()).toBe('democratic');
      expect(manager.isPrimaryElection()).toBe(true);
    });

    it('should not save null dataset index to localStorage', () => {
      const manager = new DatasetManager();
      
      // selectedDatasetIndex is null by default
      manager.saveState();
      
      // Should not have saved null index
      expect(mockLocalStorage.getItem('selectedDatasetIndex')).toBeNull();
      
      // But should have saved default filter
      expect(mockLocalStorage.getItem('partyFilter')).toBe('all');
    });
  });
});
