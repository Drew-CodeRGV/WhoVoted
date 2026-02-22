/**
 * Test Data Generators for Property-Based Testing
 * 
 * This module provides fast-check generators for creating test data
 * for the dataset selection and party filtering feature.
 */

import fc from 'fast-check';

/**
 * Generates a random dataset metadata object
 * 
 * @returns {fc.Arbitrary<Object>} Dataset metadata generator
 */
export function datasetGenerator() {
  return fc.record({
    metadataFile: fc.string({ minLength: 1 }).map(s => `metadata_${s}.json`),
    mapDataFile: fc.string({ minLength: 1 }).map(s => `map_data_${s}.json`),
    county: fc.constantFrom('Hidalgo', 'Cameron', 'Travis', 'Bexar', 'Dallas'),
    year: fc.integer({ min: 2020, max: 2024 }),
    electionType: fc.constantFrom('primary', 'general', 'runoff'),
    electionDate: fc.date({ min: new Date('2020-01-01'), max: new Date('2024-12-31') })
      .map(d => d.toISOString().split('T')[0]),
    votingMethod: fc.constantFrom('early-voting', 'election-day', 'mail-in'),
    lastUpdated: fc.date({ min: new Date('2020-01-01'), max: new Date() })
      .map(d => d.toISOString()),
    totalAddresses: fc.integer({ min: 0, max: 100000 }),
    originalFilename: fc.string({ minLength: 1 }).map(s => `${s}.csv`)
  });
}

/**
 * Generates a random voter properties object
 * 
 * @returns {fc.Arbitrary<Object>} Voter properties generator
 */
export function voterGenerator() {
  return fc.record({
    address: fc.string({ minLength: 5, maxLength: 100 }),
    name: fc.string({ minLength: 3, maxLength: 50 }),
    precinct: fc.string({ minLength: 1, maxLength: 10 }),
    party_affiliation_current: fc.constantFrom(
      'Republican',
      'Democratic',
      'Independent',
      'Libertarian',
      'Green',
      'No Party',
      '',
      'REP',
      'DEM',
      'republican',
      'democrat'
    ),
    voted_in_current_election: fc.boolean(),
    is_registered: fc.boolean()
  });
}

/**
 * Generates a voter with specific party affiliation
 * 
 * @param {string} party - Party affiliation ('republican', 'democratic', or 'other')
 * @returns {fc.Arbitrary<Object>} Voter properties generator with specific party
 */
export function voterWithPartyGenerator(party) {
  const partyValues = {
    republican: fc.constantFrom('Republican', 'REP', 'republican', 'Rep'),
    democratic: fc.constantFrom('Democratic', 'DEM', 'democrat', 'Dem'),
    other: fc.constantFrom('Independent', 'Libertarian', 'Green', 'No Party', '')
  };

  return fc.record({
    address: fc.string({ minLength: 5, maxLength: 100 }),
    name: fc.string({ minLength: 3, maxLength: 50 }),
    precinct: fc.string({ minLength: 1, maxLength: 10 }),
    party_affiliation_current: partyValues[party] || partyValues.other,
    voted_in_current_election: fc.boolean(),
    is_registered: fc.boolean()
  });
}

/**
 * Generates a GeoJSON Point geometry
 * 
 * @returns {fc.Arbitrary<Object>} GeoJSON Point geometry generator
 */
export function geoJSONPointGenerator() {
  return fc.record({
    type: fc.constant('Point'),
    coordinates: fc.tuple(
      fc.double({ min: -180, max: 180, noNaN: true }), // longitude
      fc.double({ min: -90, max: 90, noNaN: true })    // latitude
    )
  });
}

/**
 * Generates a GeoJSON Feature with voter properties
 * 
 * @returns {fc.Arbitrary<Object>} GeoJSON Feature generator
 */
export function geoJSONFeatureGenerator() {
  return fc.record({
    type: fc.constant('Feature'),
    geometry: geoJSONPointGenerator(),
    properties: voterGenerator()
  });
}

/**
 * Generates a GeoJSON Feature with specific party affiliation
 * 
 * @param {string} party - Party affiliation ('republican', 'democratic', or 'other')
 * @returns {fc.Arbitrary<Object>} GeoJSON Feature generator with specific party
 */
export function geoJSONFeatureWithPartyGenerator(party) {
  return fc.record({
    type: fc.constant('Feature'),
    geometry: geoJSONPointGenerator(),
    properties: voterWithPartyGenerator(party)
  });
}

/**
 * Generates a GeoJSON FeatureCollection
 * 
 * @param {number} minFeatures - Minimum number of features
 * @param {number} maxFeatures - Maximum number of features
 * @returns {fc.Arbitrary<Object>} GeoJSON FeatureCollection generator
 */
export function geoJSONFeatureCollectionGenerator(minFeatures = 0, maxFeatures = 100) {
  return fc.record({
    type: fc.constant('FeatureCollection'),
    features: fc.array(geoJSONFeatureGenerator(), { minLength: minFeatures, maxLength: maxFeatures })
  });
}

/**
 * Generates an array of datasets with varying properties
 * 
 * @param {number} minDatasets - Minimum number of datasets
 * @param {number} maxDatasets - Maximum number of datasets
 * @returns {fc.Arbitrary<Array>} Array of dataset generators
 */
export function datasetArrayGenerator(minDatasets = 1, maxDatasets = 20) {
  return fc.array(datasetGenerator(), { minLength: minDatasets, maxLength: maxDatasets });
}

/**
 * Generates a dataset with specific election type
 * 
 * @param {string} electionType - Election type ('primary', 'general', or 'runoff')
 * @returns {fc.Arbitrary<Object>} Dataset generator with specific election type
 */
export function datasetWithElectionTypeGenerator(electionType) {
  return fc.record({
    metadataFile: fc.string({ minLength: 1 }).map(s => `metadata_${s}.json`),
    mapDataFile: fc.string({ minLength: 1 }).map(s => `map_data_${s}.json`),
    county: fc.constantFrom('Hidalgo', 'Cameron', 'Travis', 'Bexar', 'Dallas'),
    year: fc.integer({ min: 2020, max: 2024 }),
    electionType: fc.constant(electionType),
    electionDate: fc.date({ min: new Date('2020-01-01'), max: new Date('2024-12-31') })
      .map(d => d.toISOString().split('T')[0]),
    votingMethod: fc.constantFrom('early-voting', 'election-day', 'mail-in'),
    lastUpdated: fc.date({ min: new Date('2020-01-01'), max: new Date() })
      .map(d => d.toISOString()),
    totalAddresses: fc.integer({ min: 0, max: 100000 }),
    originalFilename: fc.string({ minLength: 1 }).map(s => `${s}.csv`)
  });
}

/**
 * Generates a mixed array of voters with different party affiliations
 * 
 * @param {number} minVoters - Minimum number of voters
 * @param {number} maxVoters - Maximum number of voters
 * @returns {fc.Arbitrary<Array>} Array of GeoJSON features with mixed parties
 */
export function mixedPartyVotersGenerator(minVoters = 10, maxVoters = 100) {
  return fc.array(
    fc.oneof(
      geoJSONFeatureWithPartyGenerator('republican'),
      geoJSONFeatureWithPartyGenerator('democratic'),
      geoJSONFeatureWithPartyGenerator('other')
    ),
    { minLength: minVoters, maxLength: maxVoters }
  );
}

/**
 * Generates a localStorage state object
 * 
 * @returns {fc.Arbitrary<Object>} localStorage state generator
 */
export function localStorageStateGenerator() {
  return fc.record({
    selectedDatasetIndex: fc.integer({ min: 0, max: 50 }),
    partyFilter: fc.constantFrom('all', 'republican', 'democratic')
  });
}
