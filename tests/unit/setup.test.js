/**
 * Setup verification test
 * 
 * This test verifies that the testing infrastructure is properly configured.
 */

import { describe, it, expect } from '@jest/globals';
import fc from 'fast-check';
import { 
  datasetGenerator, 
  voterGenerator, 
  geoJSONFeatureGenerator 
} from '../generators.js';

describe('Testing Infrastructure Setup', () => {
  describe('Jest Configuration', () => {
    it('should run basic assertions', () => {
      expect(true).toBe(true);
      expect(1 + 1).toBe(2);
    });

    it('should support async tests', async () => {
      const result = await Promise.resolve(42);
      expect(result).toBe(42);
    });
  });

  describe('fast-check Integration', () => {
    it('should run property-based tests', () => {
      fc.assert(
        fc.property(fc.integer(), (n) => {
          return n + 0 === n;
        }),
        { numRuns: 100 }
      );
    });

    it('should generate random integers', () => {
      fc.assert(
        fc.property(fc.integer({ min: 0, max: 100 }), (n) => {
          return n >= 0 && n <= 100;
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('Test Data Generators', () => {
    it('should generate valid dataset objects', () => {
      fc.assert(
        fc.property(datasetGenerator(), (dataset) => {
          return (
            typeof dataset.county === 'string' &&
            typeof dataset.year === 'number' &&
            typeof dataset.electionType === 'string' &&
            typeof dataset.metadataFile === 'string' &&
            typeof dataset.mapDataFile === 'string'
          );
        }),
        { numRuns: 100 }
      );
    });

    it('should generate valid voter objects', () => {
      fc.assert(
        fc.property(voterGenerator(), (voter) => {
          return (
            typeof voter.address === 'string' &&
            typeof voter.name === 'string' &&
            typeof voter.precinct === 'string' &&
            typeof voter.party_affiliation_current === 'string' &&
            typeof voter.voted_in_current_election === 'boolean' &&
            typeof voter.is_registered === 'boolean'
          );
        }),
        { numRuns: 100 }
      );
    });

    it('should generate valid GeoJSON features', () => {
      fc.assert(
        fc.property(geoJSONFeatureGenerator(), (feature) => {
          return (
            feature.type === 'Feature' &&
            feature.geometry.type === 'Point' &&
            Array.isArray(feature.geometry.coordinates) &&
            feature.geometry.coordinates.length === 2 &&
            typeof feature.properties === 'object'
          );
        }),
        { numRuns: 100 }
      );
    });

    it('should generate coordinates within valid ranges', () => {
      fc.assert(
        fc.property(geoJSONFeatureGenerator(), (feature) => {
          const [lon, lat] = feature.geometry.coordinates;
          return (
            lon >= -180 && lon <= 180 &&
            lat >= -90 && lat <= 90
          );
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('Generator Constraints', () => {
    it('should generate datasets with valid years', () => {
      fc.assert(
        fc.property(datasetGenerator(), (dataset) => {
          return dataset.year >= 2020 && dataset.year <= 2024;
        }),
        { numRuns: 100 }
      );
    });

    it('should generate datasets with valid election types', () => {
      fc.assert(
        fc.property(datasetGenerator(), (dataset) => {
          return ['primary', 'general', 'runoff'].includes(dataset.electionType);
        }),
        { numRuns: 100 }
      );
    });

    it('should generate datasets with valid voting methods', () => {
      fc.assert(
        fc.property(datasetGenerator(), (dataset) => {
          return ['early-voting', 'election-day', 'mail-in'].includes(dataset.votingMethod);
        }),
        { numRuns: 100 }
      );
    });

    it('should generate voters with valid party affiliations', () => {
      fc.assert(
        fc.property(voterGenerator(), (voter) => {
          const validParties = [
            'Republican', 'Democratic', 'Independent', 
            'Libertarian', 'Green', 'No Party', '',
            'REP', 'DEM', 'republican', 'democrat'
          ];
          return validParties.includes(voter.party_affiliation_current);
        }),
        { numRuns: 100 }
      );
    });
  });
});
