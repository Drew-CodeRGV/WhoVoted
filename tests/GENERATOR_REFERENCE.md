# Test Data Generator Reference

Quick reference guide for using the test data generators in property-based tests.

## Basic Generators

### `datasetGenerator()`
Generates a complete dataset metadata object with all required fields.

```javascript
import { datasetGenerator } from './generators.js';
import fc from 'fast-check';

fc.assert(
  fc.property(datasetGenerator(), (dataset) => {
    // dataset has: county, year, electionType, electionDate, votingMethod, etc.
    return dataset.year >= 2020 && dataset.year <= 2024;
  })
);
```

**Generated fields:**
- `metadataFile`: string (e.g., "metadata_xyz.json")
- `mapDataFile`: string (e.g., "map_data_xyz.json")
- `county`: string (Hidalgo, Cameron, Travis, Bexar, Dallas)
- `year`: number (2020-2024)
- `electionType`: string (primary, general, runoff)
- `electionDate`: string (ISO date format)
- `votingMethod`: string (early-voting, election-day, mail-in)
- `lastUpdated`: string (ISO datetime)
- `totalAddresses`: number (0-100000)
- `originalFilename`: string (e.g., "xyz.csv")

### `voterGenerator()`
Generates a voter properties object with party affiliation.

```javascript
import { voterGenerator } from './generators.js';

fc.assert(
  fc.property(voterGenerator(), (voter) => {
    // voter has: address, name, precinct, party_affiliation_current, etc.
    return typeof voter.party_affiliation_current === 'string';
  })
);
```

**Generated fields:**
- `address`: string (5-100 chars)
- `name`: string (3-50 chars)
- `precinct`: string (1-10 chars)
- `party_affiliation_current`: string (Republican, Democratic, Independent, etc.)
- `voted_in_current_election`: boolean
- `is_registered`: boolean

### `geoJSONFeatureGenerator()`
Generates a complete GeoJSON Feature with Point geometry and voter properties.

```javascript
import { geoJSONFeatureGenerator } from './generators.js';

fc.assert(
  fc.property(geoJSONFeatureGenerator(), (feature) => {
    // feature.type === 'Feature'
    // feature.geometry.type === 'Point'
    // feature.geometry.coordinates = [lon, lat]
    // feature.properties = voter object
    return feature.geometry.coordinates.length === 2;
  })
);
```

## Specialized Generators

### `voterWithPartyGenerator(party)`
Generates a voter with specific party affiliation.

```javascript
import { voterWithPartyGenerator } from './generators.js';

// Generate only Republican voters
fc.assert(
  fc.property(voterWithPartyGenerator('republican'), (voter) => {
    const party = voter.party_affiliation_current.toLowerCase();
    return party.includes('republican') || party.includes('rep');
  })
);

// Generate only Democratic voters
fc.assert(
  fc.property(voterWithPartyGenerator('democratic'), (voter) => {
    const party = voter.party_affiliation_current.toLowerCase();
    return party.includes('democrat') || party.includes('dem');
  })
);

// Generate voters with other parties
fc.assert(
  fc.property(voterWithPartyGenerator('other'), (voter) => {
    const party = voter.party_affiliation_current.toLowerCase();
    return !party.includes('republican') && !party.includes('democrat');
  })
);
```

**Parameters:**
- `party`: 'republican', 'democratic', or 'other'

### `geoJSONFeatureWithPartyGenerator(party)`
Generates a GeoJSON Feature with specific party affiliation.

```javascript
import { geoJSONFeatureWithPartyGenerator } from './generators.js';

// Generate features with Republican voters only
fc.assert(
  fc.property(
    fc.array(geoJSONFeatureWithPartyGenerator('republican')),
    (features) => {
      return features.every(f => {
        const party = f.properties.party_affiliation_current.toLowerCase();
        return party.includes('republican') || party.includes('rep');
      });
    }
  )
);
```

**Parameters:**
- `party`: 'republican', 'democratic', or 'other'

### `datasetWithElectionTypeGenerator(electionType)`
Generates a dataset with specific election type.

```javascript
import { datasetWithElectionTypeGenerator } from './generators.js';

// Generate only primary election datasets
fc.assert(
  fc.property(
    datasetWithElectionTypeGenerator('primary'),
    (dataset) => {
      return dataset.electionType === 'primary';
    }
  )
);
```

**Parameters:**
- `electionType`: 'primary', 'general', or 'runoff'

## Collection Generators

### `datasetArrayGenerator(minDatasets, maxDatasets)`
Generates an array of datasets with varying properties.

```javascript
import { datasetArrayGenerator } from './generators.js';

// Generate 5-15 datasets
fc.assert(
  fc.property(
    datasetArrayGenerator(5, 15),
    (datasets) => {
      return datasets.length >= 5 && datasets.length <= 15;
    }
  )
);
```

**Parameters:**
- `minDatasets`: minimum number of datasets (default: 1)
- `maxDatasets`: maximum number of datasets (default: 20)

### `geoJSONFeatureCollectionGenerator(minFeatures, maxFeatures)`
Generates a complete GeoJSON FeatureCollection.

```javascript
import { geoJSONFeatureCollectionGenerator } from './generators.js';

// Generate FeatureCollection with 10-50 features
fc.assert(
  fc.property(
    geoJSONFeatureCollectionGenerator(10, 50),
    (collection) => {
      return (
        collection.type === 'FeatureCollection' &&
        collection.features.length >= 10 &&
        collection.features.length <= 50
      );
    }
  )
);
```

**Parameters:**
- `minFeatures`: minimum number of features (default: 0)
- `maxFeatures`: maximum number of features (default: 100)

### `mixedPartyVotersGenerator(minVoters, maxVoters)`
Generates an array of GeoJSON features with mixed party affiliations.

```javascript
import { mixedPartyVotersGenerator } from './generators.js';

// Generate 20-100 voters with mixed parties
fc.assert(
  fc.property(
    mixedPartyVotersGenerator(20, 100),
    (voters) => {
      // Will contain mix of Republican, Democratic, and other party voters
      return voters.length >= 20 && voters.length <= 100;
    }
  )
);
```

**Parameters:**
- `minVoters`: minimum number of voters (default: 10)
- `maxVoters`: maximum number of voters (default: 100)

## State Generators

### `localStorageStateGenerator()`
Generates a localStorage state object for persistence testing.

```javascript
import { localStorageStateGenerator } from './generators.js';

fc.assert(
  fc.property(
    localStorageStateGenerator(),
    (state) => {
      return (
        typeof state.selectedDatasetIndex === 'number' &&
        ['all', 'republican', 'democratic'].includes(state.partyFilter)
      );
    }
  )
);
```

**Generated fields:**
- `selectedDatasetIndex`: number (0-50)
- `partyFilter`: string ('all', 'republican', 'democratic')

## Geometry Generators

### `geoJSONPointGenerator()`
Generates a GeoJSON Point geometry with valid coordinates.

```javascript
import { geoJSONPointGenerator } from './generators.js';

fc.assert(
  fc.property(
    geoJSONPointGenerator(),
    (point) => {
      const [lon, lat] = point.coordinates;
      return (
        point.type === 'Point' &&
        lon >= -180 && lon <= 180 &&
        lat >= -90 && lat <= 90
      );
    }
  )
);
```

## Usage Tips

### Combining Generators

You can combine generators using fast-check's combinators:

```javascript
import fc from 'fast-check';
import { datasetGenerator, voterGenerator } from './generators.js';

// Generate a dataset with an array of voters
fc.assert(
  fc.property(
    fc.record({
      dataset: datasetGenerator(),
      voters: fc.array(voterGenerator(), { minLength: 10, maxLength: 100 })
    }),
    ({ dataset, voters }) => {
      // Test with both dataset and voters
      return voters.length >= 10;
    }
  )
);
```

### Filtering Generated Data

Use `fc.filter()` to constrain generated data:

```javascript
import fc from 'fast-check';
import { datasetGenerator } from './generators.js';

// Generate only datasets from 2024
fc.assert(
  fc.property(
    datasetGenerator().filter(d => d.year === 2024),
    (dataset) => {
      return dataset.year === 2024;
    }
  )
);
```

### Mapping Generated Data

Use `.map()` to transform generated data:

```javascript
import fc from 'fast-check';
import { voterGenerator } from './generators.js';

// Generate voters and extract only party affiliation
fc.assert(
  fc.property(
    voterGenerator().map(v => v.party_affiliation_current),
    (party) => {
      return typeof party === 'string';
    }
  )
);
```

## Common Patterns

### Testing Filter Functions

```javascript
import fc from 'fast-check';
import { mixedPartyVotersGenerator } from './generators.js';

// Test that filtering returns only matching voters
fc.assert(
  fc.property(
    mixedPartyVotersGenerator(10, 50),
    (voters) => {
      const filtered = voters.filter(v => {
        const party = v.properties.party_affiliation_current.toLowerCase();
        return party.includes('republican');
      });
      
      return filtered.every(v => {
        const party = v.properties.party_affiliation_current.toLowerCase();
        return party.includes('republican') || party.includes('rep');
      });
    }
  ),
  { numRuns: 100 }
);
```

### Testing Grouping Functions

```javascript
import fc from 'fast-check';
import { datasetArrayGenerator } from './generators.js';

// Test that grouping by year works correctly
fc.assert(
  fc.property(
    datasetArrayGenerator(5, 20),
    (datasets) => {
      const grouped = datasets.reduce((groups, dataset) => {
        const year = dataset.year;
        groups[year] = groups[year] || [];
        groups[year].push(dataset);
        return groups;
      }, {});
      
      // All datasets in each group should have the same year
      return Object.entries(grouped).every(([year, group]) => {
        return group.every(d => d.year === parseInt(year));
      });
    }
  ),
  { numRuns: 100 }
);
```

### Testing Color Mapping

```javascript
import fc from 'fast-check';
import { voterGenerator } from './generators.js';
import { getExpectedPartyColor } from './test-helpers.js';

// Test that color mapping is consistent
fc.assert(
  fc.property(
    voterGenerator(),
    (voter) => {
      const color1 = getExpectedPartyColor(voter.party_affiliation_current);
      const color2 = getExpectedPartyColor(voter.party_affiliation_current);
      return color1 === color2; // Same input should give same output
    }
  ),
  { numRuns: 100 }
);
```

## Configuration

All property tests should run with at least 100 iterations:

```javascript
fc.assert(
  fc.property(/* ... */),
  { numRuns: 100 }
);
```

For more intensive testing, increase the number of runs:

```javascript
fc.assert(
  fc.property(/* ... */),
  { numRuns: 1000 }
);
```
