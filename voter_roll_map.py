# Dependencies
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import csv
from tkinter import filedialog, Tk
import webbrowser
import os

# 1. Load the Voter Roll CSV
def load_voter_roll():
    Tk().withdraw()  # Hides the root window
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not file_path:
        raise ValueError("No file selected.")
    return pd.read_csv(file_path)

# 2. Check for Duplicates and Concatenate Addresses
def clean_voter_roll(df):
    df['Address'] = df['Address'].str.strip()  # Remove leading/trailing whitespaces
    df_grouped = df.groupby('Address', as_index=False).agg(lambda x: ', '.join(set(x)))
    return df_grouped

# 3. Geolocate and Plot the Addresses
def plot_addresses(df):
    geolocator = Nominatim(user_agent="voter_roll_mapping")

    map_center = [37.7749, -122.4194]  # Default to San Francisco, update later
    voter_map = folium.Map(location=map_center, zoom_start=12)

    for index, row in df.iterrows():
        address = row['Address']
        try:
            location = geolocator.geocode(address)
            if location:
                folium.Marker(
                    location=[location.latitude, location.longitude],
                    popup=address,
                    icon=folium.Icon(color="green", icon="ok-sign")
                ).add_to(voter_map)
        except Exception as e:
            print(f"Error geolocating {address}: {e}")

    return voter_map

# 4. Geo-locate or Input Address
def geolocate_and_zoom(voter_map, user_address=None):
    geolocator = Nominatim(user_agent="voter_roll_user_location")

    if not user_address:
        user_location = geolocator.geocode("Your IP-based location")
        if user_location:
            user_coords = [user_location.latitude, user_location.longitude]
        else:
            raise ValueError("Unable to determine geolocation.")
    else:
        location = geolocator.geocode(user_address)
        if location:
            user_coords = [location.latitude, location.longitude]
        else:
            raise ValueError("Address not found.")

    # Zoom to .5 mile (approx. 0.8 km) radius
    voter_map.fit_bounds([[user_coords[0] - 0.005, user_coords[1] - 0.005], 
                          [user_coords[0] + 0.005, user_coords[1] + 0.005]])

    return voter_map

# 5. Save and Display the Map
def save_and_open_map(voter_map):
    voter_map.save("voter_roll_map.html")
    webbrowser.open(f"file://{os.path.realpath('voter_roll_map.html')}")

# Main workflow
if __name__ == "__main__":
    try:
        # Load voter roll
        voter_roll_df = load_voter_roll()

        # Clean and concatenate addresses
        cleaned_voter_roll_df = clean_voter_roll(voter_roll_df)

        # Plot voter addresses on map
        voter_map = plot_addresses(cleaned_voter_roll_df)

        # Geolocate or use input address
        user_input_address = input("Enter your address or press Enter to use geolocation: ")
        voter_map = geolocate_and_zoom(voter_map, user_address=user_input_address if user_input_address else None)

        # Save and open the map in a browser
        save_and_open_map(voter_map)

    except Exception as e:
        print(f"An error occurred: {e}")
