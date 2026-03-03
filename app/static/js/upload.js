/**
 * DrapeStudio — Upload page helper (vanilla JS)
 * Handles garment + model photo selection, validation, compression, preview, and upload.
 */

const MAX_FILES       = 5;
const ACCEPTED_TYPES  = ['image/jpeg', 'image/png', 'image/webp'];
const MIN_DIMENSION   = 400;
const MAX_SIZE_MB     = 5;
const COMPRESS_QUALITY = 0.82;
const COMPRESS_MAX_PX  = 2048;

let selectedFiles      = [];   // garment photos: [{file, dataUrl, width, height}]
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

                // Scale down so the longest side ≤ COMPRESS_MAX_PX
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
            selectedFiles.push({ file: file, dataUrl: e.target.result, width: img.width, height: img.height });
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
        return '<div class="relative aspect-square rounded-xl overflow-hidden bg-gray-100">' +
            '<img src="' + f.dataUrl + '" alt="' + f.file.name + '" class="w-full h-full object-cover">' +
            '<button onclick="removeFile(' + i + ')" ' +
                    'class="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/60 text-white text-xs ' +
                           'flex items-center justify-center hover:bg-black/80 transition-colors" ' +
                    'title="Remove">' +
                '&times;' +
            '</button>' +
            '<p class="absolute bottom-0 inset-x-0 bg-black/40 text-white text-[9px] px-1 py-0.5 truncate">' +
                f.file.name +
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
        // 1. Sign garment photo uploads
        var signResp = await fetch('/v1/uploads/sign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                files: selectedFiles.map(function(f) {
                    return { kind: 'image', filename: f.file.name, content_type: f.file.type };
                }),
            }),
        });
        if (!signResp.ok) {
            var err = await signResp.json();
            throw new Error(err.detail || 'Failed to get upload URLs');
        }
        var signData = await signResp.json();

        // 2. Upload garment photos
        var fileUrls = [];
        for (var i = 0; i < signData.uploads.length; i++) {
            var upload = signData.uploads[i];
            var formData = new FormData();
            formData.append('file', selectedFiles[i].file);
            var uploadResp = await fetch(upload.upload_url, { method: 'POST', body: formData });
            if (!uploadResp.ok) throw new Error('Upload failed for ' + selectedFiles[i].file.name);
            fileUrls.push(upload.file_url);
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
