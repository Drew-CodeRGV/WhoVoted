# Production Deployment Checklist

## Pre-Deployment

### Security
- [ ] Change admin password from default `admin2026!`
- [ ] Set `secure=True` for cookies (requires HTTPS)
- [ ] Update `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`
- [ ] Review and restrict CORS origins in `config.py`
- [ ] Enable HTTPS/TLS on your server
- [ ] Set strong `SECRET_KEY` in `.env`

### Configuration
- [ ] Update `NOMINATIM_USER_AGENT` with your project name and contact
- [ ] Set appropriate `SESSION_TIMEOUT_HOURS`
- [ ] Configure `MAX_UPLOAD_SIZE_MB` based on your needs
- [ ] Update `MAP_CENTER` in `public/config.js` for your region
- [ ] Set `MAP_ZOOM` and `MAP_BOUNDS` appropriately

### Backend
- [ ] Install production WSGI server (gunicorn or waitress)
- [ ] Set up proper logging (file rotation, retention)
- [ ] Configure error monitoring (Sentry, etc.)
- [ ] Set up database for sessions (if scaling beyond single instance)
- [ ] Configure backup strategy for cache and data files

### Frontend
- [ ] Update API endpoints if backend is on different domain
- [ ] Minify JavaScript and CSS files
- [ ] Optimize images and assets
- [ ] Set up CDN for static assets (optional)
- [ ] Test on multiple browsers and devices

## Deployment Steps

### Backend Deployment (Railway)

1. **Create Railway Project**
   ```bash
   railway login
   railway init
   ```

2. **Set Environment Variables**
   ```bash
   railway variables set ADMIN_USERNAME=your_username
   railway variables set ADMIN_PASSWORD=your_secure_password
   railway variables set NOMINATIM_USER_AGENT="YourProject/1.0 (your@email.com)"
   ```

3. **Deploy**
   ```bash
   railway up
   ```

4. **Configure Persistent Storage**
   - Mount volumes for `/data`, `/uploads`, `/logs`
   - Set up automatic backups

### Frontend Deployment (GitHub Pages)

1. **Prepare Files**
   ```bash
   cd public
   # Update config.js with production backend URL
   ```

2. **Deploy to GitHub Pages**
   ```bash
   git checkout -b gh-pages
   git add public/*
   git commit -m "Deploy to GitHub Pages"
   git push origin gh-pages
   ```

3. **Configure Custom Domain** (optional)
   - Add CNAME file
   - Update DNS records
   - Enable HTTPS in GitHub Pages settings

## Post-Deployment

### Testing
- [ ] Test admin login with new credentials
- [ ] Upload sample CSV and verify processing
- [ ] Check public map displays data correctly
- [ ] Test search functionality
- [ ] Test geolocation feature
- [ ] Verify error handling and logging
- [ ] Test on mobile devices
- [ ] Run load testing (if expecting high traffic)

### Monitoring
- [ ] Set up uptime monitoring (UptimeRobot, Pingdom)
- [ ] Configure log aggregation (Papertrail, Loggly)
- [ ] Set up error alerting
- [ ] Monitor disk space usage
- [ ] Track API usage and rate limits

### Documentation
- [ ] Update README with production URLs
- [ ] Document deployment process
- [ ] Create runbook for common issues
- [ ] Document backup and restore procedures
- [ ] Create user guide for admin panel

## Maintenance

### Regular Tasks
- [ ] Review logs weekly
- [ ] Clean up old uploads (automated in code)
- [ ] Backup geocoding cache monthly
- [ ] Update dependencies quarterly
- [ ] Review and rotate logs
- [ ] Monitor Nominatim usage and respect limits

### Updates
- [ ] Test updates in staging environment first
- [ ] Keep Python and dependencies up to date
- [ ] Update Leaflet.js and plugins
- [ ] Review security advisories
- [ ] Update documentation

## Scaling Considerations

### If You Need to Scale

**Backend:**
- Use Redis for session storage
- Add load balancer for multiple instances
- Use PostgreSQL for persistent data
- Implement job queue (Celery) for processing
- Add caching layer (Redis, Memcached)

**Frontend:**
- Use CDN for static assets
- Implement service worker for offline support
- Add progressive web app features
- Optimize bundle size

**Data:**
- Partition large datasets by region
- Implement data archiving strategy
- Use spatial database (PostGIS) for queries
- Add data versioning

## Rollback Plan

If deployment fails:

1. **Backend Rollback**
   ```bash
   railway rollback
   ```

2. **Frontend Rollback**
   ```bash
   git revert HEAD
   git push origin gh-pages
   ```

3. **Data Rollback**
   - Restore from backup
   - Verify data integrity
   - Test functionality

## Support Contacts

- **Nominatim Support**: https://nominatim.org/
- **OpenStreetMap**: https://www.openstreetmap.org/
- **Leaflet.js**: https://leafletjs.com/
- **Flask**: https://flask.palletsprojects.com/

## Success Criteria

✓ Server responds within 2 seconds
✓ Admin login works
✓ CSV upload and processing completes
✓ Map displays data correctly
✓ Search returns results
✓ No errors in logs
✓ HTTPS enabled
✓ Monitoring active
✓ Backups configured

---

**Note**: This checklist assumes you're deploying to Railway (backend) and GitHub Pages (frontend). Adjust as needed for your hosting provider.
