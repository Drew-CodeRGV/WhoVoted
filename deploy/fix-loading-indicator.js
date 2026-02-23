// Emergency fix for stuck loading indicator
// Add this to the end of data.js to ensure loading indicator is always hidden

// Force hide loading indicator after 10 seconds if still showing
setTimeout(() => {
    const loadingIndicator = document.getElementById('map-loading-indicator');
    if (loadingIndicator && loadingIndicator.style.display !== 'none') {
        console.warn('Loading indicator was stuck, forcing hide');
        loadingIndicator.style.display = 'none';
    }
}, 10000);

// Also hide on any error
window.addEventListener('error', () => {
    const loadingIndicator = document.getElementById('map-loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
});
