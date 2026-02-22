# Deprecated - Version 1.0

This directory contains the original version of WhoVoted (v1.0) which has been deprecated.

## Why Deprecated?

The original version has been replaced with a modernized architecture featuring:

- **Backend-driven architecture** with Flask server
- **Admin dashboard** for file uploads and processing
- **Multi-dataset support** with dataset selector
- **Improved geocoding** with AWS Location Service integration
- **Caching system** with 77,000+ pre-geocoded addresses
- **Two-color progress bar** showing cached vs newly geocoded addresses
- **Parallel processing** for faster geocoding
- **Better error handling** and logging

## Migration

The new version is located in the `public/` directory and uses a Flask backend in the `backend/` directory.

### Key Changes:

1. **Frontend**: Moved from root to `public/` directory
2. **Backend**: New Flask server in `backend/` directory
3. **Data**: Centralized in `data/` directory with caching
4. **Admin**: New admin dashboard at `/admin`

## Old Version Files

- `index.html` - Original single-page application
- `data.js` - Client-side data loading
- `config.js` - Client-side configuration
- `styles.css` - Original styles

## Do Not Use

This version is kept for reference only. Please use the new version in the `public/` directory.

---

**Deprecated Date**: February 22, 2026  
**Replacement**: WhoVoted v2.0 (public/ + backend/)
