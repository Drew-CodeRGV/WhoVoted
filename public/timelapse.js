/**
 * TimeLapsePlayer - Animated day-by-day early vote turnout visualization
 * Shows turnout building over time like a weather radar map.
 */
class TimeLapsePlayer {
    constructor(map, options = {}) {
        this.map = map;
        this.daySnapshots = [];     // [{date, features}] sorted chronologically
        this.currentDayIndex = -1;
        this.isPlaying = false;
        this.playbackSpeed = 1000;  // ms per step
        this.intervalId = null;
        this.heatmapLayer = null;
        this.controlsEl = null;
        this.onDayChange = options.onDayChange || null;
    }

    /**
     * Load day snapshots from pre-fetched data
     * @param {Array} snapshots - Array of {date, features} sorted chronologically
     */
    setSnapshots(snapshots) {
        this.daySnapshots = snapshots || [];
        this.currentDayIndex = this.daySnapshots.length > 0 ? 0 : -1;
        this.updateControls();
    }

    play() {
        if (this.daySnapshots.length === 0) return;
        if (this.isPlaying) return;
        
        this.isPlaying = true;
        this.updateControls();
        
        // If at the end, restart from beginning
        if (this.currentDayIndex >= this.daySnapshots.length - 1) {
            this.currentDayIndex = -1;
        }
        
        this.intervalId = setInterval(() => {
            if (this.currentDayIndex >= this.daySnapshots.length - 1) {
                this.pause();
                return;
            }
            this.stepForward();
        }, this.playbackSpeed);
    }

    pause() {
        this.isPlaying = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.updateControls();
    }

    stepForward() {
        if (this.currentDayIndex < this.daySnapshots.length - 1) {
            this.currentDayIndex++;
            this.renderCumulativeUpTo(this.currentDayIndex);
        }
    }

    stepBackward() {
        if (this.currentDayIndex > 0) {
            this.currentDayIndex--;
            this.renderCumulativeUpTo(this.currentDayIndex);
        }
    }

    seekToDay(index) {
        const clamped = Math.max(0, Math.min(index, this.daySnapshots.length - 1));
        this.currentDayIndex = clamped;
        this.renderCumulativeUpTo(this.currentDayIndex);
    }

    setSpeed(ms) {
        this.playbackSpeed = Math.max(500, Math.min(3000, ms));
        // If playing, restart interval with new speed
        if (this.isPlaying) {
            clearInterval(this.intervalId);
            this.intervalId = setInterval(() => {
                if (this.currentDayIndex >= this.daySnapshots.length - 1) {
                    this.pause();
                    return;
                }
                this.stepForward();
            }, this.playbackSpeed);
        }
        this.updateControls();
    }

    renderCumulativeUpTo(dayIndex) {
        if (dayIndex < 0 || dayIndex >= this.daySnapshots.length) return;
        
        // Collect all features up to and including dayIndex
        const allFeatures = [];
        for (let i = 0; i <= dayIndex; i++) {
            allFeatures.push(...this.daySnapshots[i].features);
        }
        
        // Deduplicate by VUID
        const deduped = deduplicateByVUID(allFeatures);
        
        // Filter out unmatched
        const { renderable, total, unmatched } = filterEarlyVoteFeatures(deduped);
        
        // Build heatmap points
        const heatPoints = renderable.map(f => {
            const coords = f.geometry.coordinates;
            return [coords[1], coords[0], 1]; // [lat, lng, intensity]
        });
        
        // Update or create heatmap layer
        if (this.heatmapLayer) {
            this.heatmapLayer.setLatLngs(heatPoints);
        } else {
            // Determine color based on party from first feature
            const party = renderable.length > 0 
                ? (renderable[0].properties.party_affiliation_current || '').toLowerCase()
                : '';
            
            const gradient = party.includes('democrat') 
                ? { 0.0: 'rgba(30,144,255,0)', 0.3: 'rgba(30,144,255,0.4)', 0.6: 'rgba(30,144,255,0.7)', 1.0: 'rgba(30,144,255,1)' }
                : party.includes('republican')
                ? { 0.0: 'rgba(220,20,60,0)', 0.3: 'rgba(220,20,60,0.4)', 0.6: 'rgba(220,20,60,0.7)', 1.0: 'rgba(220,20,60,1)' }
                : undefined;
            
            const opts = {
                radius: 25, blur: 35, maxZoom: 16,
                max: 1.0, minOpacity: 0.3, maxOpacity: 0.8
            };
            if (gradient) opts.gradient = gradient;
            
            this.heatmapLayer = L.heatLayer(heatPoints, opts);
            this.heatmapLayer.addTo(this.map);
        }
        
        // Notify
        const snapshot = this.daySnapshots[dayIndex];
        if (this.onDayChange) {
            this.onDayChange({
                date: snapshot.date,
                dayIndex: dayIndex,
                totalDays: this.daySnapshots.length,
                cumulativeTotal: total,
                cumulativeRenderable: renderable.length,
                unmatchedCount: unmatched
            });
        }
        
        this.updateControls();
    }

    updateControls() {
        if (!this.controlsEl) return;
        
        const playBtn = this.controlsEl.querySelector('.tl-play-btn');
        const dayLabel = this.controlsEl.querySelector('.tl-day-label');
        const countLabel = this.controlsEl.querySelector('.tl-count-label');
        const progress = this.controlsEl.querySelector('.tl-progress');
        const speedLabel = this.controlsEl.querySelector('.tl-speed-label');
        
        if (playBtn) {
            playBtn.innerHTML = this.isPlaying 
                ? '<i class="fas fa-pause"></i>' 
                : '<i class="fas fa-play"></i>';
        }
        
        if (dayLabel && this.currentDayIndex >= 0 && this.daySnapshots.length > 0) {
            const snap = this.daySnapshots[this.currentDayIndex];
            dayLabel.textContent = `Day ${this.currentDayIndex + 1}/${this.daySnapshots.length}: ${snap.date}`;
        } else if (dayLabel) {
            dayLabel.textContent = 'No data loaded';
        }
        
        if (progress) {
            const pct = this.daySnapshots.length > 1 
                ? (this.currentDayIndex / (this.daySnapshots.length - 1)) * 100 
                : 0;
            progress.value = pct;
        }
        
        if (speedLabel) {
            speedLabel.textContent = `${(this.playbackSpeed / 1000).toFixed(1)}s`;
        }
    }

    createControls() {
        const el = document.createElement('div');
        el.className = 'timelapse-controls';
        el.innerHTML = `
            <div class="tl-header">
                <span class="tl-title">Time-Lapse</span>
                <span class="tl-day-label">No data loaded</span>
            </div>
            <div class="tl-buttons">
                <button class="tl-btn tl-back-btn" title="Previous day"><i class="fas fa-step-backward"></i></button>
                <button class="tl-btn tl-play-btn" title="Play/Pause"><i class="fas fa-play"></i></button>
                <button class="tl-btn tl-fwd-btn" title="Next day"><i class="fas fa-step-forward"></i></button>
            </div>
            <div class="tl-progress-row">
                <input type="range" class="tl-progress" min="0" max="100" value="0" />
            </div>
            <div class="tl-speed-row">
                <label>Speed:</label>
                <input type="range" class="tl-speed-slider" min="500" max="3000" value="1000" step="100" />
                <span class="tl-speed-label">1.0s</span>
            </div>
            <div class="tl-count-label"></div>
        `;
        
        // Wire events
        el.querySelector('.tl-play-btn').addEventListener('click', () => {
            this.isPlaying ? this.pause() : this.play();
        });
        el.querySelector('.tl-back-btn').addEventListener('click', () => this.stepBackward());
        el.querySelector('.tl-fwd-btn').addEventListener('click', () => this.stepForward());
        
        el.querySelector('.tl-progress').addEventListener('input', (e) => {
            const pct = parseFloat(e.target.value);
            const idx = Math.round((pct / 100) * (this.daySnapshots.length - 1));
            this.seekToDay(idx);
        });
        
        el.querySelector('.tl-speed-slider').addEventListener('input', (e) => {
            this.setSpeed(parseInt(e.target.value));
        });
        
        this.controlsEl = el;
        this.updateControls();
        return el;
    }

    destroy() {
        this.pause();
        if (this.heatmapLayer && this.map.hasLayer(this.heatmapLayer)) {
            this.map.removeLayer(this.heatmapLayer);
        }
        this.heatmapLayer = null;
        if (this.controlsEl && this.controlsEl.parentNode) {
            this.controlsEl.parentNode.removeChild(this.controlsEl);
        }
        this.controlsEl = null;
        this.daySnapshots = [];
        this.currentDayIndex = -1;
    }
}
