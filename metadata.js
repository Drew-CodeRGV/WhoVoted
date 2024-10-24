function loadMetadata() {
  const TOTAL_VOTERS = 446749;

  fetch('data/metadata.json')
    .then(response => response.json())
    .then(data => {
      // Format and update total addresses
      const totalAddressesElement = document.getElementById('total-addresses');
      if (totalAddressesElement) {
        totalAddressesElement.textContent = new Intl.NumberFormat().format(data.total_addresses);
      }

      // Calculate and update percentage
      const percentageElement = document.getElementById('percentage');
      if (percentageElement) {
        const percentage = (data.total_addresses / TOTAL_VOTERS * 100).toFixed(2);
        percentageElement.textContent = percentage;
      }

      // Format and update timestamp
      const lastUpdatedElement = document.getElementById('last-updated');
      if (lastUpdatedElement && data.last_updated) {
        const date = new Date(data.last_updated);
        const formattedTime = new Intl.DateTimeFormat('en-US', {
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        }).format(date);

        const formattedDate = new Intl.DateTimeFormat('en-US', {
          month: 'numeric',
          day: 'numeric',
          year: 'numeric'
        }).format(date);

        lastUpdatedElement.textContent = `${formattedTime} on ${formattedDate}`;
      }
    })
    .catch(error => {
      console.error('Error loading metadata:', error);
      ['total-addresses', 'percentage', 'last-updated'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
          element.textContent = 'Error';
        }
      });
    });
}

// Call loadMetadata when the document is loaded
document.addEventListener('DOMContentLoaded', loadMetadata);
