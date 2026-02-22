# Testing Infrastructure

This directory contains the test suite for the WhoVoted dataset selection and party filtering feature.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for specific examples and edge cases
├── property/                # Property-based tests for universal correctness
├── generators.js            # Test data generators for fast-check
└── README.md               # This file
```

## Test Types

### Unit Tests (`unit/`)

Unit tests verify specific examples, edge cases, and error conditions:
- Specific input/output examples
- Edge cases (empty arrays, null values, etc.)
- Error handling scenarios
- Integration points between components

### Property-Based Tests (`property/`)

Property-based tests verify universal properties across all inputs using fast-check:
- Run minimum 100 iterations with randomized inputs
- Test correctness properties that should hold for all valid inputs
- Each test references the design document property number
- Use generators from `generators.js` for test data

## Running Tests

```bash
# Run all tests
npm test

# Run only unit tests
npm test:unit

# Run only property tests
npm test:property

# Run tests in watch mode
npm test:watch
```

## Test Configuration

Tests use:
- **Jest** as the test runner
- **fast-check** for property-based testing
- **jsdom** for DOM environment simulation

Configuration is in `package.json` under the `jest` key.

## Writing Tests

### Unit Test Example

```javascript
import { describe, it, expect } from '@jest/globals';
import { PartyFilterEngine } from '../public/data.js';

describe('PartyFilterEngine', () => {
  it('should handle null party affiliation', () => {
    const engine = new PartyFilterEngine();
    const result = engine.getPartyAffiliation({ party_affiliation_current: null });
    expect(result).toBe('Unknown');
  });
});
```

### Property Test Example

```javascript
import { describe, it } from '@jest/globals';
import fc from 'fast-check';
import { geoJSONFeatureGenerator } from '../generators.js';
import { PartyFilterEngine } from '../../public/data.js';

// Feature: dataset-party-filter, Property 6: Republican Filter Correctness
describe('Republican Filter Correctness', () => {
  it('should only display voters with Republican affiliation', () => {
    fc.assert(
      fc.property(
        fc.array(geoJSONFeatureGenerator()),
        (features) => {
          const engine = new PartyFilterEngine();
          const filtered = engine.filterByParty(features, 'republican');
          
          return filtered.every(feature => {
            const party = feature.properties.party_affiliation_current.toLowerCase();
            return party.includes('republican') || party.includes('rep');
          });
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

## Test Data Generators

The `generators.js` file provides fast-check generators for:

- `datasetGenerator()` - Random dataset metadata
- `voterGenerator()` - Random voter properties
- `voterWithPartyGenerator(party)` - Voter with specific party
- `geoJSONFeatureGenerator()` - Random GeoJSON feature
- `geoJSONFeatureWithPartyGenerator(party)` - Feature with specific party
- `geoJSONFeatureCollectionGenerator()` - GeoJSON FeatureCollection
- `datasetArrayGenerator()` - Array of datasets
- `datasetWithElectionTypeGenerator(type)` - Dataset with specific election type
- `mixedPartyVotersGenerator()` - Mixed party voter array
- `localStorageStateGenerator()` - localStorage state object

## Coverage Goals

- **Line coverage**: Minimum 85%
- **Branch coverage**: Minimum 80%
- **Property test coverage**: All 19 correctness properties implemented
- **Unit test coverage**: All edge cases and error conditions covered

## Test Tags

Each property test includes a comment tag referencing the design document:

```javascript
// Feature: dataset-party-filter, Property N: Property Name
```

This ensures traceability between requirements, design properties, and test implementation.
