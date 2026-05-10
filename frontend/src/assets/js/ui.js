/**
 * ui.js ÔÇö reusable UI helpers (toast, modal, badges, charts, etc.)
 */

// ÔöÇÔöÇ Toast ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function toast(msg, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ÔöÇÔöÇ Modal helpers ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function openModal(id)  { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ÔöÇÔöÇ Category badge ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function categoryBadge(cat) {
  return `<span class="badge badge-${cat}">${cat}</span>`;
}

// ÔöÇÔöÇ File icon by extension ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
const EXT_ICONS = {
  // Video
  mp4: '­čÄČ', mkv: '­čÄČ', avi: '­čÄČ', mov: '­čÄČ', wmv: '­čÄČ', webm: '­čÄČ',
  // Audio
  mp3: '­čÄÁ', flac: '­čÄÁ', wav: '­čÄÁ', aac: '­čÄÁ', ogg: '­čÄÁ',
  // Images
  jpg: '­čľ╝´ŞĆ', jpeg: '­čľ╝´ŞĆ', png: '­čľ╝´ŞĆ', gif: '­čľ╝´ŞĆ', webp: '­čľ╝´ŞĆ', svg: '­čľ╝´ŞĆ',
  // Docs
  pdf: '­čôä', doc: '­čôŁ', docx: '­čôŁ', xls: '­čôŐ', xlsx: '­čôŐ', ppt: '­čôĹ', pptx: '­čôĹ', txt: '­čôä', md: '­čôä',
  // Executables
  exe: 'ÔÜÖ´ŞĆ', msi: 'ÔÜÖ´ŞĆ', iso: '­čĺ┐', zip: '­čôŽ', rar: '­čôŽ', '7z': '­čôŽ',
};

function fileIcon(extension) {
  const ext = (extension || '').replace('.', '').toLowerCase();
  return EXT_ICONS[ext] || '­čôä';
}

// ÔöÇÔöÇ Human-readable size ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function humanSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
  return `${bytes.toFixed(1)} ${units[i]}`;
}

// ÔöÇÔöÇ Date formatting ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function fmtDate(isoStr) {
  if (!isoStr) return 'ÔÇö';
  return new Date(isoStr).toLocaleString();
}

// ÔöÇÔöÇ Simple horizontal bar chart ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function renderBarChart(containerId, data, labelKey, valueKey, colorVar = '--accent') {
  const container = document.getElementById(containerId);
  if (!container) return;
  const max = Math.max(...data.map(d => d[valueKey]), 1);
  container.innerHTML = data.map(d => `
    <div class="bar-chart-row">
      <div class="bar-chart-label" title="${d[labelKey]}">${d[labelKey]}</div>
      <div class="bar-chart-track">
        <div class="bar-chart-fill" style="width:${(d[valueKey]/max*100).toFixed(1)}%"></div>
      </div>
      <div class="bar-chart-count">${d[valueKey].toLocaleString()}</div>
    </div>
  `).join('');
}

// ÔöÇÔöÇ Confirmation promise ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function confirmAction(message) {
  return new Promise(resolve => {
    document.getElementById('confirm-msg').textContent = message;
    openModal('modal-confirm');

    const okBtn     = document.getElementById('btn-confirm-ok');
    const cancelBtn = document.getElementById('btn-confirm-cancel');

    function cleanup(result) {
      closeModal('modal-confirm');
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      resolve(result);
    }
    const onOk     = () => cleanup(true);
    const onCancel = () => cleanup(false);
    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
  });
}

// ÔöÇÔöÇ File detail modal content ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function renderFileDetail(file, categories) {
  const catOptions = categories.map(c =>
    `<option value="${c}" ${c === file.category ? 'selected' : ''}>${c}</option>`
  ).join('');

  return `
    <h3>${fileIcon(file.extension)} ${file.name}</h3>
    <div class="detail-grid">

      <div class="detail-item detail-full">
        <label>Full Path</label>
        <p class="truncate">${file.full_path}</p>
      </div>

      <div class="detail-item">
        <label>Size</label>
        <p>${humanSize(file.size_bytes)}</p>
      </div>

      <div class="detail-item">
        <label>Extension</label>
        <p>${file.extension || 'ÔÇö'}</p>
      </div>

      <div class="detail-item">
        <label>Modified</label>
        <p>${fmtDate(file.modified_at)}</p>
      </div>

      <div class="detail-item">
        <label>Created</label>
        <p>${fmtDate(file.created_at)}</p>
      </div>

      <div class="detail-item detail-full">
        <label>Category</label>
        <select id="detail-category" class="mt-1">${catOptions}</select>
        ${file.category_overridden ? '<small class="text-muted"> (manually set)</small>' : `<small class="text-muted"> AI suggested: ${file.ai_category}</small>`}
      </div>

      <div class="detail-item detail-full">
        <label>Tags (comma-separated)</label>
        <input id="detail-tags" type="text" value="${file.tags}" />
      </div>

      <div class="detail-item detail-full">
        <label>Description</label>
        <textarea id="detail-desc" rows="3">${file.description}</textarea>
      </div>

    </div>
    <div class="detail-actions">
      <button class="btn btn-primary" id="detail-save" data-id="${file.id}">Save Changes</button>
      <button class="btn" id="detail-rename" data-id="${file.id}" data-name="${file.name}">Rename</button>
      <button class="btn" id="detail-move" data-id="${file.id}">Move</button>
      <button class="btn" id="detail-open-folder" data-path="${file.parent_dir}">­čôé Open Folder</button>
      <button class="btn btn-danger" id="detail-delete" data-id="${file.id}">Delete</button>
    </div>
  `;
}
