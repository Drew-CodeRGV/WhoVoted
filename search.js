let autocomplete;

function initAutocomplete() {
    const input = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');

    autocomplete = new google.maps.places.Autocomplete(input, {
        types: ['address'],
        componentRestrictions: {country: 'us'},
        bounds: new google.maps.LatLngBounds(
            new google.maps.LatLng(26.0, -98.5),
            new google.maps.LatLng(26.4, -98.0)
        ),
        strictBounds: true
    });

    autocomplete.addListener('place_changed', performSearch);
    searchButton.addEventListener('click', performSearch);
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

function performSearch() {
    const place = autocomplete.getPlace();
    if (!place || !place.geometry) {
        const service = new google.maps.places.AutocompleteService();
        service.getPlacePredictions({ input: document.getElementById('search-input').value }, function(predictions, status) {
            if (status === google.maps.places.PlacesServiceStatus.OK && predictions && predictions.length > 0) {
                const placesService = new google.maps.places.PlacesService(document.createElement('div'));
                placesService.getDetails({ placeId: predictions[0].place_id }, function(result, status) {
                    if (status === google.maps.places.PlacesServiceStatus.OK) {
                        handleSelectedPlace(result);
                    }
                });
            } else {
                console.log("No results found");
            }
        });
    } else {
        handleSelectedPlace(place);
    }
}

function handleSelectedPlace(place) {
    const latlng = [place.geometry.location.lat(), place.geometry.location.lng()];
    addCustomMarker(latlng);
    map.setView(latlng, 16);
    showNearbyLocations(latlng);
}

initAutocomplete();
