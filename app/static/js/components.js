/**
 * DrapeStudio — Alpine.js Component Functions
 * Loaded globally in base.html before the closing </body>
 */

'use strict';

// ── Analytics Helper ──────────────────────────────────────────────────────────
/**
 * Track a custom GA4 event.
 * Safe to call even if GA4 is not configured.
 *
 * @param {string} action   - e.g. 'generation_start'
 * @param {string} category - e.g. 'generation'
 * @param {string} label    - e.g. 'adult'
 * @param {number} [value]  - optional numeric value
 */
function trackEvent(action, category, label, value) {
    if (typeof gtag !== 'undefined') {
        gtag('event', action, {
            event_category: category,
            event_label: label,
            value: value,
        });
    }
}

// ── Toast Store ──────────────────────────────────────────────────────────────
function toastStore() {
    return {
        toasts: [],
        _counter: 0,

        init() {
            // Expose globally so any JS can call window.$toast.show(...)
            window.$toast = this;
            // Support @toast.window event: dispatch('toast', {type, message, duration})
            window.addEventListener('toast', (e) => this.addToast(e.detail));
        },

        /** Called by @toast.window Alpine events: { type, message, duration? } */
        addToast({ type = 'default', message = '', duration = 3500 } = {}) {
            this.show(message, type, duration);
        },

        show(message, type = 'default', duration = 3500) {
            const id = ++this._counter;
            this.toasts.push({ id, message, type, visible: true });

            setTimeout(() => this.dismiss(id), duration);
        },

        dismiss(id) {
            const t = this.toasts.find(t => t.id === id);
            if (t) {
                t.visible = false;
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 200);
            }
        },

        success(msg, duration)  { this.show(msg, 'success', duration); },
        error(msg, duration)    { this.show(msg, 'error', duration); },
        warning(msg, duration)  { this.show(msg, 'warning', duration); },
    };
}


// ── Upload Zone ───────────────────────────────────────────────────────────────
function uploadZone(options = {}) {
    const {
        maxFiles = 5,
        accept   = ['image/jpeg', 'image/png', 'image/webp'],
        maxMB    = 10,
        onFiles  = null,  // callback(files: File[])
    } = options;

    return {
        files: [],
        dragging: false,
        uploading: false,

        handleDragEnter(e) {
            e.preventDefault();
            this.dragging = true;
        },
        handleDragLeave(e) {
            if (!this.$el.contains(e.relatedTarget)) this.dragging = false;
        },
        handleDragOver(e) {
            e.preventDefault();
        },
        handleDrop(e) {
            e.preventDefault();
            this.dragging = false;
            const dropped = Array.from(e.dataTransfer.files);
            this._addFiles(dropped);
        },
        handleInput(e) {
            const selected = Array.from(e.target.files || []);
            this._addFiles(selected);
        },

        _addFiles(newFiles) {
            const filtered = newFiles.filter(f => accept.includes(f.type));
            const tooBig   = newFiles.filter(f => f.size > maxMB * 1024 * 1024);

            if (tooBig.length > 0 && window.$toast) {
                window.$toast.error(`File too large (max ${maxMB} MB)`);
            }

            const combined = [...this.files, ...filtered].slice(0, maxFiles);
            this.files = combined;

            if (typeof onFiles === 'function') onFiles(this.files);
        },

        removeFile(index) {
            this.files.splice(index, 1);
            if (typeof onFiles === 'function') onFiles(this.files);
        },

        get isEmpty() { return this.files.length === 0; },
        get isFull()  { return this.files.length >= maxFiles; },
    };
}


// ── Image Gallery ─────────────────────────────────────────────────────────────
function imageGallery(images = []) {
    return {
        images,
        current: 0,
        lightboxOpen: false,

        open(index) {
            this.current = index;
            this.lightboxOpen = true;
            document.body.style.overflow = 'hidden';
        },
        close() {
            this.lightboxOpen = false;
            document.body.style.overflow = '';
        },
        prev() {
            this.current = (this.current - 1 + this.images.length) % this.images.length;
        },
        next() {
            this.current = (this.current + 1) % this.images.length;
        },
        handleKey(e) {
            if (!this.lightboxOpen) return;
            if (e.key === 'ArrowLeft')  this.prev();
            if (e.key === 'ArrowRight') this.next();
            if (e.key === 'Escape')     this.close();
        },
    };
}


// ── PWA Install Prompt ────────────────────────────────────────────────────────
function installPrompt() {
    return {
        showBanner: false,
        _deferred: null,

        init() {
            // Only show once per session
            if (sessionStorage.getItem('pwa-install-dismissed')) return;

            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                this._deferred = e;
                // Delay banner so it doesn't appear immediately on load
                setTimeout(() => { this.showBanner = true; }, 3000);
            });
        },

        async install() {
            if (!this._deferred) return;
            this._deferred.prompt();
            const { outcome } = await this._deferred.userChoice;
            this.showBanner = false;
            this._deferred = null;
            if (outcome === 'accepted' && window.$toast) {
                window.$toast.success('DrapeStudio installed!');
            }
        },

        dismiss() {
            this.showBanner = false;
            sessionStorage.setItem('pwa-install-dismissed', '1');
        },
    };
}


// ── Utility helpers (non-Alpine) ──────────────────────────────────────────────
window.DS = {
    /**
     * Format bytes to human-readable string.
     * @param {number} bytes
     * @returns {string}
     */
    formatBytes(bytes) {
        if (bytes < 1024)        return bytes + ' B';
        if (bytes < 1048576)     return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    },

    /**
     * Copy text to clipboard and show toast.
     * @param {string} text
     */
    async copy(text) {
        try {
            await navigator.clipboard.writeText(text);
            if (window.$toast) window.$toast.success('Copied to clipboard');
        } catch {
            if (window.$toast) window.$toast.error('Copy failed');
        }
    },

    /**
     * Share an image URL using the Web Share API.
     * @param {string} url
     * @param {string} title
     */
    async share(url, title = 'DrapeStudio') {
        if (navigator.share) {
            try {
                await navigator.share({ title, url });
            } catch { /* user cancelled */ }
        } else {
            this.copy(url);
        }
    },
};

// ── Push subscription helper ──────────────────────────────────────────────────

/**
 * Subscribe the current browser to Web Push notifications.
 * Reads the VAPID public key from <meta name="vapid-public-key">.
 * Sends the subscription to /api/v1/notifications/subscribe.
 */
async function subscribeToPush() {
    if (!('serviceWorker' in navigator && 'PushManager' in window)) return false;

    const vapidKey = document.querySelector('meta[name="vapid-public-key"]')?.content;
    if (!vapidKey) return false;

    const perm = await Notification.requestPermission();
    if (perm !== 'granted') return false;

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: _urlBase64ToUint8Array(vapidKey),
    });

    const subJson = subscription.toJSON();
    const resp = await fetch('/api/v1/notifications/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: subJson.endpoint, keys: subJson.keys }),
    });
    return resp.ok;
}

function _urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = window.atob(base64);
    return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}
