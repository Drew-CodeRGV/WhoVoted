#!/usr/bin/env python3
"""
Test the PrecinctNormalizer to see what variants it generates
"""
import re

class PrecinctNormalizer:
    """
    Interprets and normalizes precinct identifiers from various formats.
    """
    
    @staticmethod
    def normalize(precinct, county=None):
        """
        Normalize a precinct identifier to a standard format.
        Returns a set of possible normalized forms for matching.
        """
        if not precinct:
            return set()
        
        p = str(precinct).strip().upper()
        normalized = set()
        
        # Original value
        normalized.add(p)
        
        # Remove all whitespace
        no_space = p.replace(' ', '')
        normalized.add(no_space)
        
        # Extract numeric parts
        numbers = re.findall(r'\d+', p)
        if numbers:
            # Just the numbers concatenated
            normalized.add(''.join(numbers))
            
            # Each number individually
            for num in numbers:
                normalized.add(num)
                normalized.add(num.lstrip('0') or '0')  # Without leading zeros
                normalized.add(num.zfill(4))  # Padded to 4 digits
        
        # Remove common prefixes
        for prefix in ['PCT', 'PRECINCT', 'PRE', 'P', 'S', 'E', 'W', 'N']:
            if p.startswith(prefix):
                suffix = p[len(prefix):].strip()
                if suffix:
                    normalized.add(suffix)
                    # Recursively normalize the suffix
                    normalized.update(PrecinctNormalizer.normalize(suffix))
        
        # Handle decimal formats: "S 3.2" → "S32", "32", "3.2", "302"
        if '.' in p:
            # Remove decimal point
            no_decimal = p.replace('.', '')
            normalized.add(no_decimal)
            
            # Split on decimal and pad: "3.2" → "302"
            parts = p.split('.')
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                major = parts[0].strip()
                minor = parts[1].strip()
                normalized.add(f"{major}{minor.zfill(2)}")
                normalized.add(f"{major.zfill(2)}{minor.zfill(2)}")
        
        # Handle hyphen formats: "3-2" → "32", "302"
        if '-' in p:
            no_hyphen = p.replace('-', '')
            normalized.add(no_hyphen)
            
            parts = p.split('-')
            if len(parts) == 2:
                normalized.add(f"{parts[0]}{parts[1].zfill(2)}")
        
        # Handle slash formats: "3/2" → "32"
        if '/' in p:
            no_slash = p.replace('/', '')
            normalized.add(no_slash)
        
        return normalized


# Test cases
test_cases = [
    ('151', 'Hidalgo'),  # Voting record format
    ('0151', 'Hidalgo'),  # Reference data format
    ('226', 'Hidalgo'),
    ('0226', 'Hidalgo'),
]

print("=" * 80)
print("PRECINCT NORMALIZER TEST")
print("=" * 80)

for precinct, county in test_cases:
    variants = PrecinctNormalizer.normalize(precinct, county)
    print(f"\nPrecinct: '{precinct}' (County: {county})")
    print(f"Variants: {sorted(variants)}")

# Check if they would match
print("\n" + "=" * 80)
print("MATCHING TEST")
print("=" * 80)

voting_precinct = '151'
reference_precinct = '0151'

voting_variants = PrecinctNormalizer.normalize(voting_precinct)
reference_variants = PrecinctNormalizer.normalize(reference_precinct)

print(f"\nVoting record: '{voting_precinct}'")
print(f"Variants: {sorted(voting_variants)}")

print(f"\nReference data: '{reference_precinct}'")
print(f"Variants: {sorted(reference_variants)}")

common = voting_variants & reference_variants
print(f"\nCommon variants: {sorted(common)}")

if common:
    print("✓ WOULD MATCH")
else:
    print("✗ WOULD NOT MATCH")
