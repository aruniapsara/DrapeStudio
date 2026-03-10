/**
 * DrapeStudio — Results gallery Alpine.js state
 * Swipeable image gallery with social sharing (WhatsApp, FB, Instagram, TikTok).
 */

function galleryState() {
    return {
        // ── State ─────────────────────────────────────────────────────────────
        images:       [],
        labels:       ['Front View', '45° Side View', 'Back View'],
        current:      0,
        loaded:       false,
        failed:       false,
        errorMessage: '',
        genId:        '',

        // Touch tracking
        touchStartX: 0,
        touchStartY: 0,

        // ── Computed getters ──────────────────────────────────────────────────

        get currentImage() {
            return this.images[this.current] || null;
        },

        get currentLabel() {
            return this.labels[this.current] || ('Image ' + (this.current + 1));
        },

        get hasPrev() {
            return this.current > 0;
        },

        get hasNext() {
            return this.current < this.images.length - 1;
        },

        // ── Init ──────────────────────────────────────────────────────────────

        init() {
            var root = document.getElementById('gallery-root');
            this.genId = root ? (root.dataset.genId || '') : '';
            if (this.genId) this.loadImages();
        },

        // ── Load images ───────────────────────────────────────────────────────

        async loadImages() {
            try {
                var resp = await fetch('/v1/generations/' + this.genId + '/outputs');
                if (!resp.ok) throw new Error('Server error ' + resp.status);
                var data = await resp.json();

                if (data.status === 'succeeded' && data.outputs && data.outputs.length > 0) {
                    this.images = data.outputs.map(function(o) { return o.image_url; });
                    this.loaded = true;
                } else if (data.status === 'failed') {
                    this.failed = true;
                    this.errorMessage = data.error_message || 'Generation failed.';
                } else {
                    this.failed = true;
                    this.errorMessage = 'Images not yet available. Status: ' + (data.status || 'unknown');
                }
            } catch (err) {
                this.failed = true;
                this.errorMessage = err.message || 'Could not load images.';
            }
        },

        // ── Navigation ────────────────────────────────────────────────────────

        next() {
            if (this.current < this.images.length - 1) this.current++;
        },

        prev() {
            if (this.current > 0) this.current--;
        },

        goTo(i) {
            if (i >= 0 && i < this.images.length) this.current = i;
        },

        // ── Touch / swipe ─────────────────────────────────────────────────────

        onTouchStart(e) {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        },

        onTouchEnd(e) {
            var dx = this.touchStartX - e.changedTouches[0].clientX;
            var dy = this.touchStartY - e.changedTouches[0].clientY;
            // Only register horizontal swipes that are longer than 50px and
            // more horizontal than vertical (to avoid interfering with scroll)
            if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
                if (dx > 0) this.next();
                else this.prev();
            }
        },

        // ── Downloads ─────────────────────────────────────────────────────────

        downloadAll() {
            window.open('/v1/generations/' + this.genId + '/download-zip', '_blank');
        },

        downloadCurrent() {
            var url = this.images[this.current];
            if (!url) return;
            this._triggerDownload(url, 'drapestudio_' + this.genId + '_' + (this.current + 1) + '.jpg');
        },

        _triggerDownload(url, filename) {
            var a = document.createElement('a');
            a.href = url;
            a.download = filename || 'drapestudio-image.jpg';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        },

        _toast(type, message) {
            if (window.$toast && typeof window.$toast.addToast === 'function') {
                window.$toast.addToast({ type: type, message: message });
            }
        },

        // ── Social sharing ────────────────────────────────────────────────────

        /**
         * WhatsApp: uses Web Share API (with image file) if available,
         * falls back to wa.me text URL.
         */
        async shareToWhatsApp() {
            var url  = this.images[this.current];
            var text = 'Check out this outfit generated with DrapeStudio! 👗✨\n\n';

            if (navigator.share && navigator.canShare) {
                try {
                    var resp = await fetch(url);
                    var blob = await resp.blob();
                    var file = new File([blob], 'drapestudio.jpg', { type: blob.type || 'image/jpeg' });
                    if (navigator.canShare({ files: [file] })) {
                        await navigator.share({ title: 'DrapeStudio Image', text: text, files: [file] });
                        return;
                    }
                } catch (e) {
                    // Fall through to URL-based share
                }
            }
            window.open('https://wa.me/?text=' + encodeURIComponent(text + window.location.href), '_blank');
        },

        /**
         * Facebook: opens the Facebook Share Dialog with the page URL.
         * (Facebook doesn't support direct image upload via URL schemes.)
         */
        shareToFacebook() {
            var shareUrl = window.location.href;
            window.open(
                'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(shareUrl),
                '_blank',
                'width=600,height=400'
            );
        },

        /**
         * Instagram: download optimised image + show toast.
         * Instagram has no public sharing API; user opens the app manually.
         */
        saveForInstagram() {
            var url  = this.images[this.current];
            if (!url) return;
            this._triggerDownload(url, 'drapestudio_instagram_' + (this.current + 1) + '.jpg');
            this._toast('success', '📸 Image saved! Open Instagram to post it.');
        },

        /**
         * TikTok: download optimised image + show toast.
         */
        saveForTikTok() {
            var url = this.images[this.current];
            if (!url) return;
            this._triggerDownload(url, 'drapestudio_tiktok_' + (this.current + 1) + '.jpg');
            this._toast('success', '🎵 Image saved! Open TikTok to post it.');
        },
    };
}
