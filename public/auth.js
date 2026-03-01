/**
 * auth.js - Google SSO authentication and role-based access control
 *
 * Roles: visitor (not logged in), pending, approved, superadmin, admin (legacy)
 */

let GOOGLE_CLIENT_ID = '';
let currentUser = null;
let userRole = 'visitor';

// Promise that resolves once initial auth check completes.
// Other code (e.g. initializeDatasetControls) can await this.
let _authResolve;
window.authReady = new Promise(resolve => { _authResolve = resolve; });

async function checkAuth() {
    try {
        const cfgResp = await fetch('/api/config');
        const cfg = await cfgResp.json();
        GOOGLE_CLIENT_ID = cfg.google_client_id || '';
        window.GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID;
        if (GOOGLE_CLIENT_ID && window.google && window.google.accounts) {
            google.accounts.id.initialize({
                client_id: GOOGLE_CLIENT_ID,
                callback: handleGoogleSignIn,
                auto_select: false,
            });
        }
    } catch (e) { console.warn('Config fetch failed:', e); }

    try {
        const resp = await fetch('/auth/me', { credentials: 'include' });
        const data = await resp.json();
        if (data.authenticated) {
            userRole = data.role || 'pending';
            currentUser = { email: data.email, role: userRole, name: data.email };
        } else {
            userRole = 'visitor';
            currentUser = null;
        }
    } catch (e) {
        userRole = 'visitor';
        currentUser = null;
    }
    applyRoleRestrictions();
    updateAccountUI();
    if (_authResolve) { _authResolve(); _authResolve = null; }
}

function handleGoogleSignIn(response) {
    fetch('/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ credential: response.credential })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            currentUser = data.user;
            userRole = data.user.role;
            applyRoleRestrictions();
            updateAccountUI();
            closeAccountModal();
            if (userRole === 'pending') {
                openAccountModal();
            } else if (window.authFullAccess && typeof switchToFullHeatmap === 'function') {
                // User just logged in with full access — switch from county overview to full heatmap
                switchToFullHeatmap();
            }
        } else {
            alert('Sign-in failed: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(err => alert('Sign-in failed. Please try again.'));
}

function signOut() {
    fetch('/auth/logout', { method: 'POST', credentials: 'include' })
    .then(() => {
        currentUser = null;
        userRole = 'visitor';
        applyRoleRestrictions();
        updateAccountUI();
        closeAccountModal();
        // Switch back to county overview heatmap
        if (typeof loadCountyOverview === 'function') {
            if (typeof clearMapMarkers === 'function') clearMapMarkers();
            loadCountyOverview('2026-03-03', 'early-voting');
        }
    });
}

function applyRoleRestrictions() {
    const full = ['approved', 'superadmin', 'admin'].includes(userRole);
    window.authFullAccess = full;

    // Hide these for visitors/pending
    ['dataIconBtn', 'mapIconBtn'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = full ? '' : 'none';
    });

    // Show registered-not-voted toggle for full-access users
    const regSection = document.getElementById('registeredToggleSection');
    if (regSection) regSection.style.display = full ? '' : 'none';

    // Hide party heatmap button for visitors
    document.querySelectorAll('[data-option="heatmap"]').forEach(btn => {
        if (btn.dataset.value === 'party') btn.style.display = full ? '' : 'none';
    });

    // Hide campaigns for visitors
    const cb = document.getElementById('campaignsBtn');
    if (cb) cb.style.display = full ? '' : 'none';

    // Show search icon for full-access users
    const searchBtn = document.querySelector('.search-icon-btn');
    if (searchBtn) searchBtn.style.display = full ? '' : 'none';
}

function updateAccountUI() {
    const btn = document.getElementById('accountBtn');
    if (!btn) return;
    if (currentUser && currentUser.picture) {
        btn.innerHTML = '<img src="' + currentUser.picture + '" alt="" style="width:28px;height:28px;border-radius:50%;border:2px solid white;">';
    } else if (currentUser) {
        btn.innerHTML = '<i class="fas fa-user-check" style="color:#4CAF50;"></i>';
    } else {
        btn.innerHTML = '<i class="fas fa-user"></i>';
    }
}

function openAccountModal() {
    let modal = document.getElementById('accountModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'accountModal';
        modal.className = 'account-modal-overlay';
        document.body.appendChild(modal);
    }
    let html = '';
    if (currentUser && userRole !== 'visitor') {
        const rl = userRole === 'pending' ? '\u23F3 Pending Approval' :
                   userRole === 'superadmin' ? '\uD83D\uDC51 Super Admin' :
                   userRole === 'approved' ? '\u2705 Approved' :
                   userRole === 'admin' ? '\uD83D\uDD27 Admin' : userRole;
        html = '<div class="account-modal">' +
            '<button class="account-modal-close" onclick="closeAccountModal()">&times;</button>' +
            '<div style="text-align:center;padding:20px;">' +
            (currentUser.picture ? '<img src="' + currentUser.picture + '" style="width:64px;height:64px;border-radius:50%;margin-bottom:10px;">' : '') +
            '<h3 style="margin:5px 0;">' + (currentUser.name || currentUser.email) + '</h3>' +
            '<p style="color:#666;font-size:13px;margin:5px 0;">' + currentUser.email + '</p>' +
            '<p style="font-size:12px;margin:8px 0;padding:4px 12px;background:#f0f0f0;border-radius:12px;display:inline-block;">' + rl + '</p>' +
            (userRole === 'pending' ? '<p style="color:#e65100;font-size:12px;margin-top:10px;">Your account is pending approval by an administrator.</p>' : '') +
            (['superadmin','admin'].includes(userRole) ? '<a href="/admin" style="display:block;margin-top:12px;color:#667eea;font-size:13px;">Admin Dashboard \u2192</a>' : '') +
            '<a href="#" onclick="closeAccountModal();document.getElementById(\'newspaperBtn\').click();return false;" style="display:block;margin-top:10px;color:#8B4513;font-size:13px;">\uD83D\uDCF0 Election Gazette</a>' +
            '<button onclick="signOut()" style="margin-top:15px;padding:8px 24px;background:#f44336;color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;">Sign Out</button>' +
            '</div></div>';
    } else {
        html = '<div class="account-modal">' +
            '<button class="account-modal-close" onclick="closeAccountModal()">&times;</button>' +
            '<div style="text-align:center;padding:20px 20px 10px;">' +
            '<h3 style="margin:0 0 5px;">Sign In</h3>' +
            '<p style="color:#666;font-size:13px;margin-bottom:15px;">Sign in to access all map features</p>' +
            '<div id="googleSignInBtn" style="display:flex;justify-content:center;margin-bottom:12px;"></div>' +
            '<div style="display:flex;align-items:center;gap:10px;margin:12px 0;">' +
            '<hr style="flex:1;border:none;border-top:1px solid #ddd;">' +
            '<span style="color:#999;font-size:12px;">or</span>' +
            '<hr style="flex:1;border:none;border-top:1px solid #ddd;">' +
            '</div>' +
            '<p style="color:#666;font-size:12px;margin-bottom:8px;">Request access with your email</p>' +
            '<div id="emailRequestMsg" style="display:none;padding:8px;border-radius:6px;font-size:12px;margin-bottom:8px;"></div>' +
            '<input id="emailRequestInput" type="email" placeholder="your@email.com" style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:13px;box-sizing:border-box;margin-bottom:8px;">' +
            '<button onclick="requestEmailAccess()" style="width:100%;padding:8px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;">Request Access</button>' +
            '<p style="color:#999;font-size:11px;margin-top:12px;">An admin will review and approve your request.</p>' +
            '</div></div>';
    }
    modal.innerHTML = html;
    modal.style.display = 'flex';
    if (!currentUser || userRole === 'visitor') {
        setTimeout(function() {
            if (window.google && window.google.accounts && GOOGLE_CLIENT_ID) {
                google.accounts.id.renderButton(
                    document.getElementById('googleSignInBtn'),
                    { theme: 'outline', size: 'large', width: 250, text: 'signin_with' }
                );
            }
        }, 100);
    }
}

function requestEmailAccess() {
    var input = document.getElementById('emailRequestInput');
    var msg = document.getElementById('emailRequestMsg');
    var email = (input.value || '').trim();
    if (!email || !email.includes('@')) {
        msg.style.display = 'block';
        msg.style.background = '#fee';
        msg.style.color = '#c33';
        msg.textContent = 'Please enter a valid email address.';
        return;
    }
    fetch('/auth/request-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        msg.style.display = 'block';
        if (data.success) {
            msg.style.background = '#efe';
            msg.style.color = '#2e7d32';
            msg.textContent = data.message || 'Request submitted! An admin will review it.';
            input.value = '';
        } else {
            msg.style.background = '#fee';
            msg.style.color = '#c33';
            msg.textContent = data.error || 'Request failed. Try again.';
        }
    })
    .catch(function() {
        msg.style.display = 'block';
        msg.style.background = '#fee';
        msg.style.color = '#c33';
        msg.textContent = 'Network error. Please try again.';
    });
}

function closeAccountModal() {
    var m = document.getElementById('accountModal');
    if (m) m.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    var ab = document.getElementById('accountBtn');
    if (ab) ab.addEventListener('click', openAccountModal);
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('account-modal-overlay')) closeAccountModal();
    });
});
