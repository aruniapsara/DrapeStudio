/**
 * DrapeStudio — Drag-and-drop upload helper (vanilla JS)
 * Handles file selection, validation, preview, and upload to backend.
 */

const MAX_FILES = 5;
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MIN_DIMENSION = 400;

let selectedFiles = [];

function handleDrop(event) {
    event.preventDefault();
    event.target.closest('.drop-zone')?.classList.remove('drag-over');
    const files = event.dataTransfer.files;
    handleFiles(files);
}

function handleFiles(fileList) {
    const newFiles = Array.from(fileList);

    // Validate file count
    if (selectedFiles.length + newFiles.length > MAX_FILES) {
        alert(`Maximum ${MAX_FILES} files allowed. You have ${selectedFiles.length} selected.`);
        return;
    }

    // Validate each file
    for (const file of newFiles) {
        if (!ACCEPTED_TYPES.includes(file.type)) {
            alert(`"${file.name}" is not a supported format. Use JPG, PNG, or WEBP.`);
            return;
        }
    }

    // Add files and validate dimensions
    for (const file of newFiles) {
        validateAndAdd(file);
    }
}

function validateAndAdd(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
        const img = new Image();
        img.onload = function () {
            if (img.width < MIN_DIMENSION || img.height < MIN_DIMENSION) {
                alert(
                    `"${file.name}" is ${img.width}×${img.height}px. ` +
                    `Minimum recommended: ${MIN_DIMENSION}×${MIN_DIMENSION}px.`
                );
            }
            selectedFiles.push({
                file: file,
                dataUrl: e.target.result,
                width: img.width,
                height: img.height,
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
    const grid = document.getElementById('preview-grid');
    if (!grid) return;

    grid.innerHTML = selectedFiles
        .map(
            (f, i) => `
        <div class="preview-item">
            <img src="${f.dataUrl}" alt="${f.file.name}">
            <button class="remove-btn" onclick="removeFile(${i})" title="Remove">&times;</button>
        </div>
    `
        )
        .join('');
}

function updateNextButton() {
    const btn = document.getElementById('btn-next');
    if (btn) {
        btn.disabled = selectedFiles.length === 0;
    }
}

async function proceedToConfigure() {
    const btn = document.getElementById('btn-next');
    btn.disabled = true;
    btn.textContent = 'Uploading...';

    try {
        // 1. Request signed upload URLs
        const signPayload = {
            files: selectedFiles.map((f) => ({
                kind: 'image',
                filename: f.file.name,
                content_type: f.file.type,
            })),
        };

        const signResp = await fetch('/v1/uploads/sign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(signPayload),
        });

        if (!signResp.ok) {
            const err = await signResp.json();
            throw new Error(err.detail || 'Failed to get upload URLs');
        }

        const signData = await signResp.json();

        // 2. Upload each file
        const fileUrls = [];
        for (let i = 0; i < signData.uploads.length; i++) {
            const upload = signData.uploads[i];
            const fileObj = selectedFiles[i].file;

            const formData = new FormData();
            formData.append('file', fileObj);

            const uploadResp = await fetch(upload.upload_url, {
                method: 'POST',
                body: formData,
            });

            if (!uploadResp.ok) {
                throw new Error(`Upload failed for ${fileObj.name}`);
            }

            fileUrls.push(upload.file_url);
        }

        // 3. Store uploaded file URLs in sessionStorage
        sessionStorage.setItem('uploadedFiles', JSON.stringify(fileUrls));

        // 4. Navigate to configure page
        window.location.href = '/configure';
    } catch (err) {
        alert('Upload error: ' + err.message);
        btn.disabled = false;
        btn.textContent = 'Next: Configure Model';
    }
}
