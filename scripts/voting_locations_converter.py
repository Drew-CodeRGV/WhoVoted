import csv
import json
from pathlib import Path

def convert_voting_locations_to_json(csv_file_path, json_file_path):
    # Read the CSV file
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        data = list(csv_reader)

    # Convert the data to JSON
    json_data = json.dumps(data, indent=2)

    # Write the JSON data to a file
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json_file.write(json_data)

    print(f"Conversion complete. JSON file saved as {json_file_path}")

if __name__ == "__main__":
    # Set the paths for input CSV and output JSON
    current_dir = Path(__file__).parent.parent
    csv_file_path = current_dir / "data" / "voting_locations_geocoded_20241026_110404.csv"
    json_file_path = current_dir / "data" / "voting_locations.json"

    # Convert voting locations CSV to JSON
    convert_voting_locations_to_json(csv_file_path, json_file_path)
