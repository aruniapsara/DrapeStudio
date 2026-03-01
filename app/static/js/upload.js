/**
 * DrapeStudio — Upload page helper (vanilla JS)
 * Handles garment + model photo selection, validation, preview, and upload.
 */

const MAX_FILES = 5;
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MIN_DIMENSION = 400;

let selectedFiles = [];        // garment photos
let selectedModelPhoto = null; // single optional model reference photo

// ── Type-card visual selection ──────────────────────────────────────────────
document.querySelectorAll('.type-card').forEach(function(card) {
    var radio = card.querySelector('input[type="radio"]');
    if (radio && radio.checked) card.classList.add('selected');
    card.addEventListener('click', function() {
        document.querySelectorAll('.type-card').forEach(function(c) { c.classList.remove('selected'); });
        card.classList.add('selected');
    });
});

// ── Garment photo handling ───────────────────────────────────────────────────
function handleDrop(event) {
    event.preventDefault();
    var zone = event.target.closest('.drop-zone');
    if (zone) zone.classList.remove('drag-over');
    handleFiles(event.dataTransfer.files);
}

function handleFiles(fileList) {
    var newFiles = Array.from(fileList);

    if (selectedFiles.length + newFiles.length > MAX_FILES) {
        alert('Maximum ' + MAX_FILES + ' files allowed. You already have ' + selectedFiles.length + ' selected.');
        return;
    }

    for (var i = 0; i < newFiles.length; i++) {
        if (!ACCEPTED_TYPES.includes(newFiles[i].type)) {
            alert('"' + newFiles[i].name + '" is not supported. Use JPG, PNG, or WEBP.');
            return;
        }
    }

    for (var j = 0; j < newFiles.length; j++) {
        validateAndAdd(newFiles[j]);
    }
}

function validateAndAdd(file) {
    var reader = new FileReader();
    reader.onload = function(e) {
        var img = new Image();
        img.onload = function() {
            if (img.width < MIN_DIMENSION || img.height < MIN_DIMENSION) {
                alert('"' + file.name + '" is ' + img.width + 'x' + img.height + 'px. ' +
                      'Minimum recommended: ' + MIN_DIMENSION + 'x' + MIN_DIMENSION + 'px.');
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
    var grid = document.getElementById('preview-grid');
    if (!grid) return;
    grid.innerHTML = selectedFiles.map(function(f, i) {
        return '<div class="preview-item">' +
            '<img src="' + f.dataUrl + '" alt="' + f.file.name + '">' +
            '<button class="remove-btn" onclick="removeFile(' + i + ')" title="Remove">&times;</button>' +
            '</div>';
    }).join('');
}

// ── Model photo handling ─────────────────────────────────────────────────────
function handleModelDrop(event) {
    event.preventDefault();
    var zone = event.target.closest('.drop-zone');
    if (zone) zone.classList.remove('drag-over');
    var files = event.dataTransfer.files;
    if (files.length > 0) handleModelFile(files[0]);
}

function handleModelFile(file) {
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
        alert('"' + file.name + '" is not supported. Use JPG, PNG, or WEBP.');
        return;
    }
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
    var preview = document.getElementById('model-photo-preview');
    var dropContent = document.getElementById('model-drop-content');
    if (!preview || !dropContent) return;

    if (selectedModelPhoto) {
        // Show thumbnail + remove button below the zone
        preview.style.display = 'flex';
        preview.style.alignItems = 'center';
        preview.style.gap = '0.75rem';
        preview.style.marginTop = '0.5rem';
        preview.innerHTML =
            '<div class="model-photo-thumb-wrap">' +
                '<img src="' + selectedModelPhoto.dataUrl + '" alt="Model photo" class="model-photo-thumb">' +
                '<button class="remove-btn" onclick="removeModelPhoto(); event.stopPropagation();" title="Remove">&times;</button>' +
            '</div>' +
            '<span style="font-size:0.85rem;color:var(--color-text-muted)">Click the box above to change photo</span>';
        // Update drop zone to show "Change" hint instead of empty dashed box
        dropContent.innerHTML =
            '<p class="drop-zone-icon" style="font-size:1.5rem;margin-bottom:0.25rem">🔄</p>' +
            '<p style="font-size:0.85rem">Click to change model photo</p>';
    } else {
        preview.style.display = 'none';
        preview.innerHTML = '';
        // Restore original drop zone content
        dropContent.innerHTML =
            '<p class="drop-zone-icon">🧍</p>' +
            '<p>Drag and drop a model photo, or click to select</p>' +
            '<p class="drop-zone-hint">Optional — 1 photo, JPG / PNG / WEBP</p>';
    }
}

// ── Next button state ────────────────────────────────────────────────────────
function updateNextButton() {
    var btn = document.getElementById('btn-next');
    if (!btn) return;
    var hasFiles = selectedFiles.length > 0;
    var genderEl = document.querySelector('input[name="_gender"]:checked');
    var hasGender = !!genderEl;
    btn.disabled = !hasFiles || !hasGender;
}

// ── Upload and proceed ───────────────────────────────────────────────────────
async function proceedToConfigure() {
    var btn = document.getElementById('btn-next');

    var ptEl = document.querySelector('input[name="_product_type"]:checked');
    var productType = ptEl ? ptEl.value : 'clothing';
    var genderEl = document.querySelector('input[name="_gender"]:checked');
    var gender = genderEl ? genderEl.value : null;

    if (!gender) {
        alert('Please select a model gender.');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Uploading...';

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

        // 3. Upload model photo (optional)
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
            var modelUpload = modelSignData.uploads[0];
            var mFormData = new FormData();
            mFormData.append('file', selectedModelPhoto.file);
            var modelUploadResp = await fetch(modelUpload.upload_url, { method: 'POST', body: mFormData });
            if (!modelUploadResp.ok) throw new Error('Failed to upload model photo');
            modelPhotoUrl = modelUpload.file_url;
        }

        // 4. Persist to sessionStorage
        sessionStorage.setItem('uploadedFiles', JSON.stringify(fileUrls));
        sessionStorage.setItem('productType', productType);
        sessionStorage.setItem('genderPresentation', gender);
        if (modelPhotoUrl) {
            sessionStorage.setItem('modelPhotoUrl', modelPhotoUrl);
        } else {
            sessionStorage.removeItem('modelPhotoUrl');
        }

        // 5. Navigate to configure
        window.location.href = '/configure';

    } catch (err) {
        alert('Upload error: ' + err.message);
        btn.disabled = false;
        btn.textContent = 'Next: Configure Model';
    }
}
