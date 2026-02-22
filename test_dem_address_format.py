"""Test what format DEM addresses are being cleaned to."""
import sys
import pandas as pd
sys.path.insert(0, 'backend')

from processor import ProcessingJob

# Create a test job to access the clean_addresses method
job = ProcessingJob(
    csv_path='uploads/DEM EV 02252022_202202260722013902.csv',
    county='Hidalgo',
    year='2022',
    election_type='primary',
    primary_party='democratic'
)

# Read first 5 rows
df = pd.read_csv('uploads/DEM EV 02252022_202202260722013902.csv', nrows=5)
print("Original addresses:")
for addr in df['ADDRESS']:
    print(f"  {addr}")

print("\nCleaned addresses:")
cleaned_df = job.clean_addresses(df)
for addr in cleaned_df['cleaned_address']:
    print(f"  {addr}")
