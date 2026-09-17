/**
 * VeritasVideo Upload & Drag-Drop Module
 * Manages quiet editorial drop zone drag states, file validation, and multipart upload.
 */

/**
 * Validates that the uploaded file is a supported video format.
 * @param {File} file
 * @returns {boolean}
 */
export function isValidVideoFile(file) {
  if (!file) return false;
  return file.type.startsWith('video/') || /\.(mp4|webm|mov|avi|mkv)$/i.test(file.name);
}

/**
 * Executes multipart analysis request to POST /api/analyze without changing endpoint or keys.
 * @param {File} file
 * @param {Object} options { geminiApiKey, sampleCount }
 * @returns {Promise<Object>} Analyzed forensic payload
 */
export async function uploadVideoFile(file, options = {}) {
  if (!isValidVideoFile(file)) {
    throw new Error('Please select a valid video file (MP4, WebM, MOV, AVI).');
  }

  const formData = new FormData();
  formData.append('file', file);
  if (options.geminiApiKey) {
    formData.append('gemini_api_key', options.geminiApiKey);
  }
  formData.append('sample_count', options.sampleCount || '16');

  const response = await fetch('/api/analyze', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server returned error ${response.status}`);
  }

  return await response.json();
}

/**
 * Binds dragenter, dragover, dragleave, drop to toggle .is-dragover on the dropZone element.
 * @param {HTMLElement} dropZone
 * @param {Function} onFileSelected
 */
export function setupDragEvents(dropZone, onFileSelected) {
  if (!dropZone) return;

  let dragCounter = 0;

  const onDragEnter = (e) => {
    e.preventDefault();
    dragCounter++;
    dropZone.classList.add('is-dragover');
  };

  const onDragOver = (e) => {
    e.preventDefault();
    dropZone.classList.add('is-dragover');
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      dropZone.classList.remove('is-dragover');
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    dragCounter = 0;
    dropZone.classList.remove('is-dragover');

    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (isValidVideoFile(file)) {
        if (onFileSelected) onFileSelected(file);
      } else {
        alert('Please select a valid video file (MP4, WebM, MOV, AVI).');
      }
    }
  };

  dropZone.addEventListener('dragenter', onDragEnter);
  dropZone.addEventListener('dragover', onDragOver);
  dropZone.addEventListener('dragleave', onDragLeave);
  dropZone.addEventListener('drop', onDrop);

  return () => {
    dropZone.removeEventListener('dragenter', onDragEnter);
    dropZone.removeEventListener('dragover', onDragOver);
    dropZone.removeEventListener('dragleave', onDragLeave);
    dropZone.removeEventListener('drop', onDrop);
  };
}

// Window global fallback for legacy script access
if (typeof window !== 'undefined') {
  window.VeritasUpload = {
    isValidVideoFile,
    uploadVideoFile,
    setupDragEvents
  };
}
