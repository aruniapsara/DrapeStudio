/**
 * DrapeStudio — Upload page helper (vanilla JS)
 * Handles garment + model photo selection, validation, compression, preview,
 * upload, and "Load from Previous Uploads" history reuse.
 */

const MAX_FILES       = 5;
const ACCEPTED_TYPES  = ['image/jpeg', 'image/png', 'image/webp'];
const MIN_DIMENSION   = 400;
const MAX_SIZE_MB     = 5;
const COMPRESS_QUALITY = 0.82;
const COMPRESS_MAX_PX  = 2048;

// Each entry in selectedFiles is either:
//   { file: File, dataUrl: string, width: number, height: number, fromHistory: false }   — new upload
//   { file: null, dataUrl: string, storageUrl: string, fromHistory: true, name: string } — from history
let selectedFiles      = [];
let selectedModelPhoto = null; // single optional model reference photo

// ── Image compression ────────────────────────────────────────────────────────
/**
 * Compress an image file if it exceeds MAX_SIZE_MB.
 * Scales the longest dimension to COMPRESS_MAX_PX and re-encodes as JPEG.
 * Returns a new File object (or the original if no compression needed).
 */
async function compressImage(file) {
    if (file.size <= MAX_SIZE_MB * 1024 * 1024) return file;

    return new Promise(function(resolve) {
        var reader = new FileReader();
        reader.onload = function(e) {
            var img = new Image();
            img.onload = function() {
                var w = img.width;
                var h = img.height;

                // Scale down so the longest side <= COMPRESS_MAX_PX
                if (w > COMPRESS_MAX_PX || h > COMPRESS_MAX_PX) {
                    if (w >= h) {
                        h = Math.round((h / w) * COMPRESS_MAX_PX);
                        w = COMPRESS_MAX_PX;
                    } else {
                        w = Math.round((w / h) * COMPRESS_MAX_PX);
                        h = COMPRESS_MAX_PX;
                    }
                }

                var canvas = document.createElement('canvas');
                canvas.width  = w;
                canvas.height = h;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, w, h);

                canvas.toBlob(function(blob) {
                    var compressed = new File(
                        [blob],
                        file.name.replace(/\.[^.]+$/, '') + '.jpg',
                        { type: 'image/jpeg', lastModified: Date.now() }
                    );
                    resolve(compressed);
                }, 'image/jpeg', COMPRESS_QUALITY);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}

// ── Type-card visual selection ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.type-card').forEach(function(card) {
        var radio = card.querySelector('input[type="radio"]');
        if (radio && radio.checked) card.classList.add('selected');
        card.addEventListener('click', function() {
            document.querySelectorAll('.type-card').forEach(function(c) { c.classList.remove('selected'); });
            card.classList.add('selected');
        });
    });
});

// ── Garment photo handling ────────────────────────────────────────────────────
function handleDrop(event) {
    event.preventDefault();
    var zone = document.getElementById('drop-zone');
    if (zone) zone.classList.remove('!border-primary', '!bg-primary/5');
    handleFiles(event.dataTransfer.files);
}

async function handleFiles(fileList) {
    var newFiles = Array.from(fileList);

    if (selectedFiles.length + newFiles.length > MAX_FILES) {
        showToast('Maximum ' + MAX_FILES + ' photos allowed. You already have ' + selectedFiles.length + ' selected.', 'error');
        return;
    }

    for (var i = 0; i < newFiles.length; i++) {
        if (!ACCEPTED_TYPES.includes(newFiles[i].type)) {
            showToast('"' + newFiles[i].name + '" is not supported. Use JPG, PNG, or WEBP.', 'error');
            return;
        }
    }

    for (var j = 0; j < newFiles.length; j++) {
        // Compress if needed, then validate & add
        var file = await compressImage(newFiles[j]);
        validateAndAdd(file);
    }
}

function validateAndAdd(file) {
    var reader = new FileReader();
    reader.onload = function(e) {
        var img = new Image();
        img.onload = function() {
            if (img.width < MIN_DIMENSION || img.height < MIN_DIMENSION) {
                showToast(
                    '"' + file.name + '" is ' + img.width + 'x' + img.height + 'px — ' +
                    'minimum recommended is ' + MIN_DIMENSION + 'x' + MIN_DIMENSION + 'px.',
                    'warning'
                );
            }
            selectedFiles.push({
                file: file,
                dataUrl: e.target.result,
                width: img.width,
                height: img.height,
                fromHistory: false,
                name: file.name,
            });
            renderPreviews();
            updateNextButton();
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderPreviews();
    updateNextButton();
}

function renderPreviews() {
    var grid  = document.getElementById('preview-grid');
    var label = document.getElementById('photo-count-label');
    var count = document.getElementById('photo-count');
    if (!grid) return;

    grid.innerHTML = selectedFiles.map(function(f, i) {
        var displayName = f.fromHistory ? (f.name || 'History image') : (f.file ? f.file.name : 'Image');
        var badge = f.fromHistory
            ? '<span class="absolute top-1 left-1 bg-primary/80 text-white text-[8px] px-1.5 py-0.5 rounded-full font-medium">History</span>'
            : '';
        return '<div class="relative aspect-square rounded-xl overflow-hidden bg-gray-100">' +
            '<img src="' + f.dataUrl + '" alt="' + displayName + '" class="w-full h-full object-cover">' +
            badge +
            '<button onclick="removeFile(' + i + ')" ' +
                    'class="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/60 text-white text-xs ' +
                           'flex items-center justify-center hover:bg-black/80 transition-colors" ' +
                    'title="Remove">' +
                '&times;' +
            '</button>' +
            '<p class="absolute bottom-0 inset-x-0 bg-black/40 text-white text-[9px] px-1 py-0.5 truncate">' +
                displayName +
            '</p>' +
        '</div>';
    }).join('');

    // Photo count badge
    if (label && count) {
        if (selectedFiles.length > 0) {
            count.textContent = selectedFiles.length;
            label.classList.remove('hidden');
        } else {
            label.classList.add('hidden');
        }
    }
}

// ── History: Load from Previous Uploads ──────────────────────────────────────
async function loadHistoryImages() {
    var loadingEl = document.getElementById('history-loading');
    var emptyEl   = document.getElementById('history-empty');
    var gridEl    = document.getElementById('history-grid');

    try {
        var resp = await fetch('/v1/uploads/history?image_type=garment&per_page=20');
        if (!resp.ok) throw new Error('Failed to load history');
        var data = await resp.json();

        if (loadingEl) loadingEl.classList.add('hidden');

        if (!data.items || data.items.length === 0) {
            if (emptyEl) emptyEl.classList.remove('hidden');
            return;
        }

        if (gridEl) {
            gridEl.innerHTML = data.items.map(function(img) {
                var label = img.original_filename || 'Image';
                // Encode the item as a data attribute for the click handler
                return '<div class="relative aspect-square rounded-xl overflow-hidden bg-gray-100 cursor-pointer ' +
                           'ring-2 ring-transparent hover:ring-primary/40 transition-all" ' +
                       'onclick=\'addFromHistory(' + JSON.stringify({
                           image_url: img.image_url,
                           storage_url: img.storage_url,
                           name: img.original_filename || 'History image'
                       }).replace(/'/g, '&#39;') + ')\'>' +
                    '<img src="' + img.image_url + '" alt="' + label + '" class="w-full h-full object-cover">' +
                    '<p class="absolute bottom-0 inset-x-0 bg-black/40 text-white text-[8px] px-1 py-0.5 truncate">' +
                        label +
                    '</p>' +
                '</div>';
            }).join('');
        }

    } catch (err) {
        if (loadingEl) loadingEl.classList.add('hidden');
        if (emptyEl) {
            emptyEl.classList.remove('hidden');
            emptyEl.innerHTML = '<p class="text-xs text-gray-400">Could not load previous uploads.</p>';
        }
    }
}

function addFromHistory(img) {
    if (selectedFiles.length >= MAX_FILES) {
        showToast('Maximum ' + MAX_FILES + ' photos allowed.', 'error');
        return;
    }

    // Check if this storage URL is already selected
    for (var i = 0; i < selectedFiles.length; i++) {
        if (selectedFiles[i].storageUrl === img.storage_url) {
            showToast('This image is already selected.', 'warning');
            return;
        }
    }

    selectedFiles.push({
        file: null,
        dataUrl: img.image_url,
        storageUrl: img.storage_url,
        fromHistory: true,
        name: img.name || 'History image',
    });

    renderPreviews();
    updateNextButton();
    showToast('Added "' + (img.name || 'image') + '" from history.', 'default');
}

// ── Model photo handling ──────────────────────────────────────────────────────
function handleModelDrop(event) {
    event.preventDefault();
    var zone = document.getElementById('model-drop-zone');
    if (zone) zone.classList.remove('!border-primary', '!bg-primary/5');
    var files = event.dataTransfer.files;
    if (files.length > 0) handleModelFile(files[0]);
}

async function handleModelFile(file) {
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
        showToast('"' + file.name + '" is not supported. Use JPG, PNG, or WEBP.', 'error');
        return;
    }
    file = await compressImage(file);
    var reader = new FileReader();
    reader.onload = function(e) {
        selectedModelPhoto = { file: file, dataUrl: e.target.result };
        renderModelPhotoPreview();
    };
    reader.readAsDataURL(file);
}

function removeModelPhoto() {
    selectedModelPhoto = null;
    var inp = document.getElementById('model-photo-file');
    if (inp) inp.value = '';
    renderModelPhotoPreview();
}

function renderModelPhotoPreview() {
    var preview     = document.getElementById('model-photo-preview');
    var dropContent = document.getElementById('model-drop-content');
    if (!preview || !dropContent) return;

    if (selectedModelPhoto) {
        preview.style.display = 'flex';
        preview.style.alignItems = 'center';
        preview.style.gap = '0.75rem';
        preview.style.marginTop = '0.5rem';
        preview.innerHTML =
            '<div class="relative w-16 h-16 rounded-xl overflow-hidden flex-shrink-0">' +
                '<img src="' + selectedModelPhoto.dataUrl + '" alt="Model reference" class="w-full h-full object-cover">' +
                '<button onclick="removeModelPhoto(); event.stopPropagation();" ' +
                        'class="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-black/60 text-white text-[10px] ' +
                               'flex items-center justify-center" title="Remove">&times;</button>' +
            '</div>' +
            '<span class="text-xs text-gray-500">Tap the box above to change photo</span>';

        dropContent.innerHTML =
            '<p class="text-xl mb-1">🔄</p>' +
            '<p class="text-xs text-gray-500">Click to change model photo</p>';
    } else {
        preview.style.display = 'none';
        preview.innerHTML = '';
        dropContent.innerHTML =
            '<p class="text-2xl mb-1">🧍</p>' +
            '<p class="text-xs text-gray-500 font-medium">Drag &amp; drop or tap to select</p>' +
            '<p class="text-[10px] text-gray-400 mt-0.5">1 photo · JPG / PNG / WEBP</p>';
    }
}

// ── Next button state ─────────────────────────────────────────────────────────
function updateNextButton() {
    var btn      = document.getElementById('btn-next');
    if (!btn) return;
    var hasFiles  = selectedFiles.length > 0;
    var genderEl  = document.querySelector('input[name="_gender"]:checked');
    var hasGender = !!genderEl;
    btn.disabled  = !hasFiles || !hasGender;
}

// ── Toast helper (uses Alpine toastStore if available, else alert) ─────────────
function showToast(message, type) {
    type = type || 'default';
    if (window.$toast && typeof window.$toast.addToast === 'function') {
        window.$toast.addToast({ type: type, message: message });
    } else {
        alert(message);
    }
}

// ── Upload and proceed ────────────────────────────────────────────────────────
async function proceedToConfigure() {
    var btn = document.getElementById('btn-next');

    var ptEl      = document.querySelector('input[name="_product_type"]:checked');
    var productType = ptEl ? ptEl.value : 'casual';
    var genderEl  = document.querySelector('input[name="_gender"]:checked');
    var gender    = genderEl ? genderEl.value : null;

    if (!gender) {
        showToast('Please select a model gender.', 'error');
        return;
    }
    if (selectedFiles.length === 0) {
        showToast('Please upload at least one garment photo.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">' +
        '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>' +
        '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>' +
        '</svg>Uploading...';

    try {
        // Split selected files into new uploads and history reuses
        var newFiles = selectedFiles.filter(function(f) { return !f.fromHistory; });
        var historyFiles = selectedFiles.filter(function(f) { return f.fromHistory; });

        var fileUrls = [];

        // 1. History files: already uploaded — use their storage URLs directly
        for (var h = 0; h < historyFiles.length; h++) {
            fileUrls.push(historyFiles[h].storageUrl);
        }

        // 2. New files: sign + upload
        if (newFiles.length > 0) {
            var signResp = await fetch('/v1/uploads/sign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    files: newFiles.map(function(f) {
                        return { kind: 'image', filename: f.file.name, content_type: f.file.type };
                    }),
                }),
            });
            if (!signResp.ok) {
                var err = await signResp.json();
                throw new Error(err.detail || 'Failed to get upload URLs');
            }
            var signData = await signResp.json();

            for (var i = 0; i < signData.uploads.length; i++) {
                var upload = signData.uploads[i];
                var formData = new FormData();
                formData.append('file', newFiles[i].file);
                var uploadResp = await fetch(upload.upload_url, { method: 'POST', body: formData });
                if (!uploadResp.ok) throw new Error('Upload failed for ' + newFiles[i].file.name);
                fileUrls.push(upload.file_url);
            }
        }

        // 3. Upload model reference photo (optional)
        var modelPhotoUrl = null;
        if (selectedModelPhoto) {
            var modelSignResp = await fetch('/v1/uploads/sign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    files: [{ kind: 'model_photo', filename: selectedModelPhoto.file.name, content_type: selectedModelPhoto.file.type }],
                }),
            });
            if (!modelSignResp.ok) {
                var mErr = await modelSignResp.json();
                throw new Error(mErr.detail || 'Failed to get model photo upload URL');
            }
            var modelSignData = await modelSignResp.json();
            var modelUpload   = modelSignData.uploads[0];
            var mFormData     = new FormData();
            mFormData.append('file', selectedModelPhoto.file);
            var modelUploadResp = await fetch(modelUpload.upload_url, { method: 'POST', body: mFormData });
            if (!modelUploadResp.ok) throw new Error('Failed to upload model photo');
            modelPhotoUrl = modelUpload.file_url;
        }

        // 4. Persist to sessionStorage for configure step
        sessionStorage.setItem('uploadedFiles',      JSON.stringify(fileUrls));
        sessionStorage.setItem('productType',        productType);
        sessionStorage.setItem('genderPresentation', gender);
        if (modelPhotoUrl) {
            sessionStorage.setItem('modelPhotoUrl', modelPhotoUrl);
        } else {
            sessionStorage.removeItem('modelPhotoUrl');
        }

        // 5. Navigate to configure
        window.location.href = '/configure';

    } catch (err) {
        showToast('Upload error: ' + err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = 'Next: Configure Model' +
            '<svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">' +
            '<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>';
    }
}
