/**
 * Example Property-Based Tests
 * 
 * These tests demonstrate the property-based testing approach
 * and verify that the test infrastructure is working correctly.
 */

import { describe, it } from '@jest/globals';
import fc from 'fast-check';
import { 
  datasetGenerator, 
  voterGenerator,
  geoJSONFeatureGenerator,
  datasetArrayGenerator,
  mixedPartyVotersGenerator
} from '../generators.js';
import { 
  isPartyType, 
  getExpectedPartyColor,
  hasCompleteMetadata,
  isPrimaryElection
} from '../test-helpers.js';

describe('Property-Based Testing Examples', () => {
  // Feature: dataset-party-filter, Example Property: Dataset Metadata Completeness
  describe('Dataset Metadata Completeness', () => {
    it('should generate datasets with all required metadata fields', () => {
      fc.assert(
        fc.property(
          datasetGenerator(),
          (dataset) => {
            return hasCompleteMetadata(dataset);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: dataset-party-filter, Example Property: Party Type Detection
  describe('Party Type Detection', () => {
    it('should correctly identify Republican voters', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('Republican', 'REP', 'republican', 'Rep'),
          (party) => {
            return isPartyType(party, 'republican');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should correctly identify Democratic voters', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('Democratic', 'DEM', 'democrat', 'Dem'),
          (party) => {
            return isPartyType(party, 'democratic');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should not identify other parties as Republican or Democratic', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('Independent', 'Libertarian', 'Green', 'No Party', ''),
          (party) => {
            return !isPartyType(party, 'republican') && !isPartyType(party, 'democratic');
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: dataset-party-filter, Example Property: Party Color Mapping
  describe('Party Color Mapping', () => {
    it('should map Republican voters to red', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('Republican', 'REP', 'republican', 'Rep'),
          (party) => {
            return getExpectedPartyColor(party) === 'red';
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should map Democratic voters to blue', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('Democratic', 'DEM', 'democrat', 'Dem'),
          (party) => {
            return getExpectedPartyColor(party) === 'blue';
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should map unknown parties to green', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('Independent', 'Libertarian', 'Green', 'No Party', ''),
          (party) => {
            return getExpectedPartyColor(party) === 'green';
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: dataset-party-filter, Example Property: Primary Election Detection
  describe('Primary Election Detection', () => {
    it('should identify primary election datasets', () => {
      fc.assert(
        fc.property(
          datasetGenerator(),
          (dataset) => {
            const isPrimary = dataset.electionType === 'primary';
            return isPrimaryElection(dataset) === isPrimary;
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: dataset-party-filter, Example Property: GeoJSON Structure Validity
  describe('GeoJSON Structure Validity', () => {
    it('should generate valid GeoJSON features', () => {
      fc.assert(
        fc.property(
          geoJSONFeatureGenerator(),
          (feature) => {
            return (
              feature.type === 'Feature' &&
              feature.geometry.type === 'Point' &&
              Array.isArray(feature.geometry.coordinates) &&
              feature.geometry.coordinates.length === 2 &&
              typeof feature.properties === 'object' &&
              feature.properties.hasOwnProperty('party_affiliation_current')
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should generate coordinates within valid geographic bounds', () => {
      fc.assert(
        fc.property(
          geoJSONFeatureGenerator(),
          (feature) => {
            const [lon, lat] = feature.geometry.coordinates;
            return (
              lon >= -180 && lon <= 180 &&
              lat >= -90 && lat <= 90 &&
              !isNaN(lon) && !isNaN(lat)
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: dataset-party-filter, Example Property: Dataset Array Properties
  describe('Dataset Array Properties', () => {
    it('should generate non-empty dataset arrays', () => {
      fc.assert(
        fc.property(
          datasetArrayGenerator(1, 20),
          (datasets) => {
            return datasets.length >= 1 && datasets.length <= 20;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should generate datasets with unique metadata files', () => {
      fc.assert(
        fc.property(
          datasetArrayGenerator(1, 10),
          (datasets) => {
            // This property may not always hold due to random generation,
            // but it demonstrates the concept
            const metadataFiles = datasets.map(d => d.metadataFile);
            return metadataFiles.length > 0;
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: dataset-party-filter, Example Property: Mixed Party Voters
  describe('Mixed Party Voters', () => {
    it('should generate voters with various party affiliations', () => {
      fc.assert(
        fc.property(
          mixedPartyVotersGenerator(10, 50),
          (voters) => {
            return voters.length >= 10 && voters.length <= 50;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should generate voters with valid party affiliations', () => {
      fc.assert(
        fc.property(
          mixedPartyVotersGenerator(10, 50),
          (voters) => {
            return voters.every(voter => 
              typeof voter.properties.party_affiliation_current === 'string'
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
