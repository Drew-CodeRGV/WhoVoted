/**
 * Test Helper Utilities
 * 
 * Common utilities and helper functions for testing.
 */

/**
 * Creates a mock localStorage implementation for testing
 * 
 * @returns {Object} Mock localStorage object
 */
export function createMockLocalStorage() {
  let store = {};

  return {
    getItem(key) {
      return store[key] || null;
    },
    setItem(key, value) {
      store[key] = String(value);
    },
    removeItem(key) {
      delete store[key];
    },
    clear() {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key(index) {
      const keys = Object.keys(store);
      return keys[index] || null;
    }
  };
}

/**
 * Creates a mock fetch implementation for testing
 * 
 * @param {Object} responses - Map of URLs to response data
 * @returns {Function} Mock fetch function
 */
export function createMockFetch(responses = {}) {
  return async (url) => {
    const response = responses[url];
    
    if (!response) {
      return {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Not found' })
      };
    }

    if (response.error) {
      return {
        ok: false,
        status: response.status || 500,
        statusText: response.statusText || 'Internal Server Error',
        json: async () => response.data || { error: 'Server error' }
      };
    }

    return {
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => response
    };
  };
}

/**
 * Checks if a string contains party affiliation keywords
 * 
 * @param {string} party - Party affiliation string
 * @param {string} type - Party type ('republican' or 'democratic')
 * @returns {boolean} True if party matches type
 */
export function isPartyType(party, type) {
  if (!party || typeof party !== 'string') {
    return false;
  }

  const lowerParty = party.toLowerCase();

  if (type === 'republican') {
    return lowerParty.includes('republican') || lowerParty.includes('rep');
  }

  if (type === 'democratic') {
    return lowerParty.includes('democrat') || lowerParty.includes('dem');
  }

  return false;
}

/**
 * Extracts party color based on affiliation
 * 
 * @param {string} party - Party affiliation string
 * @returns {string} Color code ('red', 'blue', or 'green')
 */
export function getExpectedPartyColor(party) {
  if (!party || typeof party !== 'string') {
    return 'green';
  }

  const lowerParty = party.toLowerCase();

  if (lowerParty.includes('republican') || lowerParty.includes('rep')) {
    return 'red';
  }

  if (lowerParty.includes('democrat') || lowerParty.includes('dem')) {
    return 'blue';
  }

  return 'green';
}

/**
 * Extracts party color hex code
 * 
 * @param {string} colorCode - Color code ('red', 'blue', or 'green')
 * @returns {string} Hex color code
 */
export function getExpectedColorHex(colorCode) {
  const colors = {
    'red': '#DC143C',
    'blue': '#1E90FF',
    'green': '#32CD32'
  };

  return colors[colorCode] || colors['green'];
}

/**
 * Groups datasets by a specific property
 * 
 * @param {Array} datasets - Array of dataset objects
 * @param {string} property - Property to group by
 * @returns {Object} Grouped datasets
 */
export function groupDatasets(datasets, property) {
  return datasets.reduce((groups, dataset) => {
    const key = dataset[property];
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(dataset);
    return groups;
  }, {});
}

/**
 * Checks if all datasets in a group have the same property value
 * 
 * @param {Array} datasets - Array of dataset objects
 * @param {string} property - Property to check
 * @param {*} expectedValue - Expected value
 * @returns {boolean} True if all datasets have the expected value
 */
export function allDatasetsHaveProperty(datasets, property, expectedValue) {
  return datasets.every(dataset => dataset[property] === expectedValue);
}

/**
 * Creates a mock DOM element for testing
 * 
 * @param {string} tag - HTML tag name
 * @param {Object} attributes - Element attributes
 * @returns {Object} Mock DOM element
 */
export function createMockElement(tag, attributes = {}) {
  const element = {
    tagName: tag.toUpperCase(),
    attributes: { ...attributes },
    children: [],
    style: {},
    classList: {
      add: function(...classes) {
        this.classes = [...(this.classes || []), ...classes];
      },
      remove: function(...classes) {
        this.classes = (this.classes || []).filter(c => !classes.includes(c));
      },
      contains: function(className) {
        return (this.classes || []).includes(className);
      },
      classes: []
    },
    addEventListener: function(event, handler) {
      this.eventListeners = this.eventListeners || {};
      this.eventListeners[event] = this.eventListeners[event] || [];
      this.eventListeners[event].push(handler);
    },
    removeEventListener: function(event, handler) {
      if (this.eventListeners && this.eventListeners[event]) {
        this.eventListeners[event] = this.eventListeners[event].filter(h => h !== handler);
      }
    },
    dispatchEvent: function(event) {
      if (this.eventListeners && this.eventListeners[event.type]) {
        this.eventListeners[event.type].forEach(handler => handler(event));
      }
    },
    appendChild: function(child) {
      this.children.push(child);
    },
    removeChild: function(child) {
      this.children = this.children.filter(c => c !== child);
    },
    getAttribute: function(name) {
      return this.attributes[name];
    },
    setAttribute: function(name, value) {
      this.attributes[name] = value;
    }
  };

  return element;
}

/**
 * Waits for a condition to be true
 * 
 * @param {Function} condition - Function that returns boolean
 * @param {number} timeout - Timeout in milliseconds
 * @param {number} interval - Check interval in milliseconds
 * @returns {Promise<boolean>} True if condition met, false if timeout
 */
export async function waitFor(condition, timeout = 1000, interval = 50) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (condition()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  return false;
}

/**
 * Validates dataset metadata completeness
 * 
 * @param {Object} dataset - Dataset object
 * @returns {boolean} True if all required fields are present
 */
export function hasCompleteMetadata(dataset) {
  const requiredFields = [
    'county',
    'year',
    'electionType',
    'electionDate',
    'votingMethod'
  ];

  return requiredFields.every(field => 
    dataset.hasOwnProperty(field) && dataset[field] !== null && dataset[field] !== undefined
  );
}

/**
 * Checks if a dataset is a primary election
 * 
 * @param {Object} dataset - Dataset object
 * @returns {boolean} True if primary election
 */
export function isPrimaryElection(dataset) {
  return dataset && dataset.electionType === 'primary';
}
