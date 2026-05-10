/**
 * app.js ÔÇö main application logic.
 * Connects API calls, UI rendering, and user interactions.
 */

// ÔöÇÔöÇ State ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
const STATE = {
  currentCategory: '',      // '' = All Files
  currentGroupId:  null,    // null = not drilling into a group
  currentView:     'files',
  searchQuery:     '',
  offset:          0,
  limit:           100,
  total:           0,
  viewMode:        'list',  // 'list' | 'grid'
  categories:      [],
  scanJobId:       null,
  scanPollTimer:   null,
};

// ÔöÇÔöÇ Bootstrap ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
// All static event listeners are registered at module level further below
// (safe because this script is loaded at the end of <body>).
function bindEvents() {}

document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([loadDisks(), loadCategories()]);
  bindEvents();
  showView('files');
  loadFiles();

  // Reconnect to any scan that was running before the page (re)loaded
  try {
    const active = await API.getActiveScan();
    if (active && active.id) {
      const isRescanAll = active.root_path && active.root_path.includes(';');
      if (isRescanAll) {
        openRescanModal(active.id);
      } else {
        // Regular directory scan ÔÇö show the scan modal in progress state
        document.getElementById('scan-path').value = active.root_path || '';
        document.getElementById('scan-progress').classList.remove('hidden');
        document.getElementById('btn-scan-start').disabled = true;
        openModal('modal-scan');
        pollScanJob(active.id);
      }
    }
  } catch (_) { /* no active scan or network error ÔÇö that's fine */ }
});

// ÔöÇÔöÇ Disk sidebar ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function loadDisks() {
  try {
    const disks = await API.getDisks();
    const list  = document.getElementById('disk-list');
    list.innerHTML = disks.map(d => `
      <li class="nav-item" data-path="${d.path}" title="${d.path}">
        <span class="nav-icon">­čĺż</span>
        <div style="flex:1;min-width:0;">
          <div class="truncate">${d.label}</div>
          <div class="disk-bar-wrap">
            <div class="disk-bar"><div class="disk-bar-fill" style="width:${d.pct_used}%"></div></div>
          </div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:1px;">${d.free_human} free</div>
        </div>
      </li>
    `).join('');

    list.querySelectorAll('.nav-item').forEach(el => {
      el.addEventListener('click', () => {
        document.getElementById('scan-path').value = el.dataset.path;
        openModal('modal-scan');
      });
    });
  } catch (err) {
    toast('Could not load disks: ' + err.message, 'error');
  }
}

// ÔöÇÔöÇ Categories ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function loadCategories() {
  try {
    STATE.categories = await API.getCategories();
    const list = document.getElementById('category-list');

    // Remove previously-rendered category items (keep only the first "All Files" item)
    list.querySelectorAll('.nav-item[data-category]:not([data-category=""])').forEach(el => el.remove());

    STATE.categories.forEach(cat => {
      const li = document.createElement('li');
      li.className = 'nav-item';
      li.dataset.category = cat;
      li.innerHTML = `<span class="nav-icon">${catIcon(cat)}</span> ${cat}`;
      list.appendChild(li);
    });

    list.querySelectorAll('.nav-item').forEach(el => {
      el.addEventListener('click', () => {
        list.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        el.classList.add('active');
        STATE.currentCategory = el.dataset.category;
        STATE.currentGroupId  = null;
        STATE.offset          = 0;

        if (STATE.currentCategory) {
          // Show group tiles for this category
          showView('category');
          loadCategoryGroups(STATE.currentCategory);
        } else {
          // "All Files" Ôćĺ flat file list
          showView('files');
          loadFiles();
        }
      });
    });
  } catch (err) {
    toast('Could not load categories: ' + err.message, 'error');
  }
}

function catIcon(cat) {
  const icons = { Games:'­čÄ«', Movies:'­čÄČ', Documents:'­čôä', Music:'­čÄÁ', Images:'­čľ╝´ŞĆ', Software:'ÔÜÖ´ŞĆ', Other:'­čôŽ' };
  return icons[cat] || '­čôü';
}

// ÔöÇÔöÇ Load files ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function loadFiles() {
  const params = {
    limit:  STATE.limit,
    offset: STATE.offset,
  };
  if (STATE.currentCategory)              params.category = STATE.currentCategory;
  if (STATE.currentGroupId !== null)      params.group_id = STATE.currentGroupId;  // 0 = ungrouped
  if (STATE.searchQuery)                  params.search   = STATE.searchQuery;

  try {
    const data = await API.getFiles(params);
    STATE.total = data.total;
    renderFiles(data.items);
    updatePagination();
  } catch (err) {
    toast('Failed to load files: ' + err.message, 'error');
  }
}

// ÔöÇÔöÇ Category Ôćĺ group tiles view ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function loadCategoryGroups(category) {
  const grid  = document.getElementById('category-groups-grid');
  const title = document.getElementById('category-view-title');
  title.innerHTML = `${catIcon(category)} ${category}`;
  grid.innerHTML  = '<p style="color:var(--text-muted)">LoadingÔÇŽ</p>';
  document.getElementById('category-ungrouped').classList.add('hidden');
  document.getElementById('category-breadcrumb').innerHTML = '';

  try {
    const resp   = await API.getGroups({ category });
    // Support both old array shape and new {groups, ungrouped_count} shape
    const groups          = Array.isArray(resp) ? resp : (resp.groups || []);
    const ungroupedCount  = Array.isArray(resp) ? 0    : (resp.ungrouped_count || 0);

    const tiles = [];

    // Named-group tiles
    groups.forEach(g => {
      if ((g.file_count || 0) > 0) {
        const iconHtml = g.thumbnail_path
          ? `<img class="group-tile-img" src="${g.thumbnail_path}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display=''">
             <div class="group-tile-icon" style="display:none">${catIcon(g.category)}</div>`
          : `<div class="group-tile-icon">${catIcon(g.category)}</div>`;
        tiles.push(`
          <div class="group-tile" data-gid="${g.id}" data-root="${escHtml(g.root_path)}" title="${escHtml(g.root_path)}">
            <div class="group-tile-thumb">
              ${iconHtml}
              <button class="group-tile-refresh" title="Refresh icon" onclick="event.stopPropagation();refreshGroupIcon(${g.id},this)">Ôć║</button>
            </div>
            <div class="group-tile-name">${escHtml(g.name)}</div>
            <div class="group-tile-meta">${g.file_count.toLocaleString()} files</div>
            <button class="group-tile-open-btn" title="Open in Explorer" onclick="event.stopPropagation();openFolderPath('${escHtml(g.root_path).replace(/'/g, "\\'")}')">­čôé Open</button>
          </div>`);
      }
    });

    // Ungrouped tile (files with no group assigned)
    if (ungroupedCount > 0) {
      tiles.push(`
        <div class="group-tile group-tile-ungrouped" data-gid="0" title="Files not assigned to any group">
          <div class="group-tile-icon">­čôé</div>
          <div class="group-tile-name">Ungrouped</div>
          <div class="group-tile-meta">${ungroupedCount.toLocaleString()} files</div>
        </div>`);
    }

    if (!tiles.length) {
      grid.innerHTML = `<p style="color:var(--text-muted);padding:24px 0">No files found in "${escHtml(category)}".</p>`;
      return;
    }

    grid.innerHTML = tiles.join('');
    grid.querySelectorAll('.group-tile').forEach(tile => {
      // Open-in-Explorer button ÔÇö read path from data-root to avoid JS escape issues
      const openBtn = tile.querySelector('.group-tile-open-btn');
      if (openBtn) openBtn.addEventListener('click', e => {
        e.stopPropagation();
        openFolderPath(tile.dataset.root || '');
      });

      tile.addEventListener('click', () => {
        const gid      = Number(tile.dataset.gid);
        const name     = tile.querySelector('.group-tile-name').textContent;
        const rootPath = tile.dataset.root || '';
        openGroupFiles(gid, name, rootPath);
      });
    });

  } catch (err) {
    toast('Failed to load groups: ' + err.message, 'error');
  }
}

async function openFolderPath(path) {
  try {
    await API.openFolder(path);
  } catch (err) {
    toast('Could not open folder: ' + err.message, 'error');
  }
}

async function refreshGroupIcon(groupId, btn) {
  btn.disabled   = true;
  btn.textContent = 'ÔÇŽ';
  try {
    const { thumbnail_path } = await API.refreshGroupIcon(groupId);
    // Update the tile in place
    const tile  = btn.closest('.group-tile');
    const thumb = tile.querySelector('.group-tile-thumb');
    let   img   = thumb.querySelector('.group-tile-img');
    if (!img) {
      img = document.createElement('img');
      img.className = 'group-tile-img';
      img.addEventListener('error', () => {
        img.style.display = 'none';
        const fb = thumb.querySelector('.group-tile-icon');
        if (fb) fb.style.display = '';
      });
      const fallback = thumb.querySelector('.group-tile-icon');
      if (fallback) fallback.style.display = 'none';
      thumb.prepend(img);
    }
    img.src           = thumbnail_path + '?t=' + Date.now();
    img.style.display = '';
    toast('Icon updated.', 'success');
  } catch (err) {
    toast('Icon refresh failed: ' + err.message, 'error');
  } finally {
    btn.disabled   = false;
    btn.textContent = 'Ôć║';
  }
}

async function openGroupFiles(groupId, groupName, rootPath) {
  STATE.currentGroupId = groupId;
  STATE.offset         = 0;

  // Breadcrumb
  document.getElementById('category-breadcrumb').innerHTML =
    `<button class="btn btn-sm" id="btn-back-category">ÔćÉ ${escHtml(STATE.currentCategory)}</button>
     <span style="color:var(--text-muted)"> / </span>
     <strong>${escHtml(groupName)}</strong>`;
  document.getElementById('btn-back-category').addEventListener('click', () => {
    STATE.currentGroupId = null;
    document.getElementById('category-breadcrumb').innerHTML = '';
    document.getElementById('category-ungrouped').classList.add('hidden');
    loadCategoryGroups(STATE.currentCategory);
  });

  // Hide tiles, show explorer container
  document.getElementById('category-groups-grid').innerHTML = '';
  document.getElementById('category-ungrouped').classList.remove('hidden');

  const explorerEl = document.getElementById('file-explorer');
  const countEl    = document.getElementById('files-count-cat');
  explorerEl.innerHTML = '<p class="fe-loading">Loading filesÔÇŽ</p>';
  countEl.textContent  = '';

  try {
    let tree;

    if (groupId === 0) {
      // Ungrouped files: no cached tree ÔÇö page all files and build client-side
      let allFiles = [];
      const limit  = 500;
      let   offset = 0;
      while (true) {
        const chunk = await API.getFiles({ group_id: groupId, limit, offset });
        allFiles = allFiles.concat(chunk.items);
        if (allFiles.length >= chunk.total || chunk.items.length < limit) break;
        offset += limit;
      }
      tree = buildFileTree(allFiles, '');
    } else {
      // Named group: use server-side cached tree (built once, stored in DB)
      tree = await API.getGroupTree(groupId);
    }

    // Show total file count from tree
    const totalFiles = countTreeFiles(tree);
    countEl.textContent = `${totalFiles.toLocaleString()} file${totalFiles !== 1 ? 's' : ''}`;

    explorerEl.innerHTML = '';
    renderFileExplorer(explorerEl, tree, 0);

    if (!Object.keys(tree.children).length && !tree.files.length) {
      explorerEl.innerHTML = '<p class="fe-loading">No files found.</p>';
    }
  } catch (err) {
    toast('Failed to load group files: ' + err.message, 'error');
    explorerEl.innerHTML = '<p class="fe-loading" style="color:var(--danger)">Failed to load files.</p>';
  }
}

// ÔöÇÔöÇ File-explorer tree helpers ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ

/**
 * Build a virtual folder tree from a flat list of file records.
 * rootPath is the group's root_path (may be empty for ungrouped files).
 */
function buildFileTree(files, rootPath) {
  const hasSep = /\\/.test(rootPath);
  const sep    = hasSep ? '\\' : '/';
  const clean  = rootPath ? rootPath.replace(/[/\\]+$/, '') : '';
  const root   = {
    name:     clean ? (clean.split(/[/\\]/).pop() || clean) : '(ungrouped)',
    path:     clean,
    children: {},
    files:    [],
  };

  for (const file of files) {
    let rel = file.full_path;

    // Strip the group root prefix so we work with relative paths only
    if (clean && rel.toLowerCase().startsWith(clean.toLowerCase())) {
      rel = rel.substring(clean.length).replace(/^[/\\]+/, '');
    } else {
      // File not under root (ungrouped or different drive) ÔÇö treat as root-level
      rel = file.name;
    }

    // Split into directory parts; last part is the filename itself
    const parts = rel.split(/[/\\]/);
    parts.pop(); // remove the file name ÔÇö only keep the path to its parent

    let node = root;
    for (const part of parts) {
      if (!part) continue;
      if (!node.children[part]) {
        node.children[part] = {
          name:     part,
          path:     node.path ? node.path + sep + part : part,
          children: {},
          files:    [],
        };
      }
      node = node.children[part];
    }
    node.files.push(file);
  }

  return root;
}

/** Recursively count files in a subtree (for folder badges). */
function countTreeFiles(node) {
  let n = node.files.length;
  for (const child of Object.values(node.children)) n += countTreeFiles(child);
  return n;
}

/**
 * Render a tree node into `container` at the given indentation depth.
 * Folders are collapsible; files open the detail modal on click.
 */
function renderFileExplorer(container, node, depth) {
  const sortedFolders = Object.keys(node.children)
    .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  const sortedFiles   = [...node.files]
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));

  // ÔöÇÔöÇ Folders ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
  for (const folderName of sortedFolders) {
    const child  = node.children[folderName];
    const fCount = countTreeFiles(child);

    const row         = document.createElement('div');
    row.className     = 'fe-row fe-folder-row';
    row.style.paddingLeft = `${8 + depth * 20}px`;
    row.dataset.open  = '0';
    row.dataset.path  = child.path;
    row.innerHTML =
      `<span class="fe-chevron">Ôľ║</span>` +
      `<span class="fe-icon-folder">­čôü</span>` +
      `<span class="fe-name">${escHtml(folderName)}</span>` +
      `<span class="fe-badge">${fCount.toLocaleString()}</span>`;

    // Open button ÔÇö DOM element so path is never JS-string-escaped
    const openBtn = document.createElement('button');
    openBtn.className   = 'fe-open-btn';
    openBtn.title       = 'Open in Explorer';
    openBtn.textContent = '­čôé';
    openBtn.addEventListener('click', e => {
      e.stopPropagation();
      openFolderPath(child.path);
    });
    row.appendChild(openBtn);

    const content     = document.createElement('div');
    content.className = 'fe-folder-content';
    content.style.display = 'none';

    row.addEventListener('click', () => {
      const open        = row.dataset.open === '1';
      row.dataset.open  = open ? '0' : '1';
      row.querySelector('.fe-chevron').textContent = open ? 'Ôľ║' : 'Ôľż';
      content.style.display = open ? 'none' : '';
    });

    container.appendChild(row);
    container.appendChild(content);
    renderFileExplorer(content, child, depth + 1);
  }

  // ÔöÇÔöÇ Files ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
  for (const file of sortedFiles) {
    const row     = document.createElement('div');
    row.className = 'fe-row fe-file-row';
    row.style.paddingLeft = `${8 + depth * 20 + 20}px`;
    row.dataset.id = file.id;
    row.innerHTML =
      `<span class="fe-icon-file">${fileIcon(file.extension)}</span>` +
      `<span class="fe-name fe-file-name" title="${escHtml(file.full_path)}">${escHtml(file.name)}</span>` +
      `<span class="fe-size">${humanSize(file.size_bytes)}</span>` +
      `<span class="fe-date">${file.modified_at ? new Date(file.modified_at).toLocaleDateString() : 'ÔÇö'}</span>` +
      `<span class="fe-actions"><button class="btn btn-sm fe-info-btn" title="Details">Ôä╣</button></span>`;

    row.querySelector('.fe-info-btn').addEventListener('click', e => {
      e.stopPropagation();
      openFileDetail(file.id);
    });
    row.addEventListener('click', () => openFileDetail(file.id));
    container.appendChild(row);
  }
}

// ÔöÇÔöÇ Render ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function renderFiles(files) {
  const countEl = document.getElementById('files-count');
  if (countEl) countEl.textContent =
    `${STATE.total.toLocaleString()} file${STATE.total !== 1 ? 's' : ''}`;

  if (STATE.viewMode === 'grid') {
    renderGrid(files);
  } else {
    renderTable(files);
  }
}

function renderTable(files) {
  document.getElementById('file-table').classList.remove('hidden');
  document.getElementById('file-grid').classList.add('hidden');
  renderTableIn('file-tbody', files);
}

function renderTableIn(tbodyId, files) {
  const tbody = document.getElementById(tbodyId);
  if (!files.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-muted)">No files found.</td></tr>`;
    return;
  }

  tbody.innerHTML = files.map(f => `
    <tr data-id="${f.id}" class="${f.is_missing ? 'missing' : ''}">
      <td class="cell-name" title="${f.full_path}">
        ${fileIcon(f.extension)} ${f.name}
        ${f.is_missing ? '<span class="badge badge-Other" style="font-size:9px">MISSING</span>' : ''}
      </td>
      <td>${categoryBadge(f.category)}</td>
      <td>${f.extension || 'ÔÇö'}</td>
      <td>${humanSize(f.size_bytes)}</td>
      <td>${f.modified_at ? new Date(f.modified_at).toLocaleDateString() : 'ÔÇö'}</td>
      <td class="cell-actions" onclick="event.stopPropagation()">
        <button class="btn btn-sm" onclick="openFileDetail(${f.id})">Ôä╣</button>
        <button class="btn btn-sm btn-danger" onclick="deleteFileById(${f.id}, '${escHtml(f.name)}')">­čŚĹ</button>
      </td>
    </tr>
  `).join('');

  tbody.querySelectorAll('tr[data-id]').forEach(row => {
    row.addEventListener('click', () => openFileDetail(Number(row.dataset.id)));
    row.setAttribute('draggable', 'true');
    row.addEventListener('dragstart', e => e.dataTransfer.setData('text/plain', row.dataset.id));
  });
}

function renderGrid(files) {
  document.getElementById('file-table').classList.add('hidden');
  const grid = document.getElementById('file-grid');
  grid.classList.remove('hidden');

  if (!files.length) {
    grid.innerHTML = `<p style="color:var(--text-muted);grid-column:1/-1">No files found.</p>`;
    return;
  }

  grid.innerHTML = files.map(f => `
    <div class="grid-card" data-id="${f.id}">
      <div class="grid-card-thumb">${fileIcon(f.extension)}</div>
      <div class="grid-card-body">
        <div class="grid-card-name" title="${f.name}">${f.name}</div>
        <div class="grid-card-meta">${humanSize(f.size_bytes)} ┬Ě ${categoryBadge(f.category)}</div>
      </div>
    </div>
  `).join('');

  grid.querySelectorAll('.grid-card').forEach(card => {
    card.addEventListener('click', () => openFileDetail(Number(card.dataset.id)));
  });
}

// ÔöÇÔöÇ Pagination ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function updatePagination() {
  updatePaginationIn('btn-prev', 'btn-next', 'page-info');
}

function updatePaginationIn(prevId, nextId, infoId) {
  const page  = Math.floor(STATE.offset / STATE.limit) + 1;
  const pages = Math.max(1, Math.ceil(STATE.total / STATE.limit));
  const info  = document.getElementById(infoId);
  const prev  = document.getElementById(prevId);
  const next  = document.getElementById(nextId);
  if (info) info.textContent  = `Page ${page} / ${pages}`;
  if (prev) prev.disabled      = STATE.offset === 0;
  if (next) next.disabled      = STATE.offset + STATE.limit >= STATE.total;
}

// ÔöÇÔöÇ View switching ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const el = document.getElementById(`view-${name}`);
  if (el) el.classList.add('active');

  document.querySelectorAll('[data-view]').forEach(el => {
    el.classList.toggle('active', el.dataset.view === name);
  });

  STATE.currentView = name;

  if (name === 'dashboard') loadDashboard();
  if (name === 'groups')    loadGroups();
  if (name === 'logs')      loadLogsView();
}

// ÔöÇÔöÇ Dashboard ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function loadDashboard() {
  try {
    const stats = await API.getStats();
    document.getElementById('stat-cards').innerHTML = `
      <div class="stat-card">
        <div class="stat-card-label">Total Files</div>
        <div class="stat-card-value">${stats.total_files.toLocaleString()}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-label">Total Size</div>
        <div class="stat-card-value">${humanSize(stats.total_size)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-label">Missing Files</div>
        <div class="stat-card-value" style="color:var(--danger)">${stats.missing_files.toLocaleString()}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-label">Categories</div>
        <div class="stat-card-value">${stats.by_category.length}</div>
      </div>
    `;

    renderBarChart('chart-category', stats.by_category, 'category', 'count');
    renderBarChart('chart-ext', stats.by_extension.slice(0, 12), 'extension', 'count');
  } catch (err) {
    toast('Failed to load stats: ' + err.message, 'error');
  }
}

// ÔöÇÔöÇ Groups (all-groups view) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function loadGroups() {
  try {
    const resp   = await API.getGroups();
    const groups = Array.isArray(resp) ? resp : (resp.groups || []);
    const grid   = document.getElementById('groups-grid');
    if (!groups.length) {
      grid.innerHTML = '<p style="color:var(--text-muted)">No groups detected yet. Run a scan first.</p>';
      return;
    }
    grid.innerHTML = groups.map(g => {
      const iconHtml = g.thumbnail_path
        ? `<img class="group-tile-img" src="${g.thumbnail_path}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display=''">
           <div class="group-tile-icon" style="display:none">${catIcon(g.category)}</div>`
        : `<div class="group-tile-icon">${catIcon(g.category)}</div>`;
      return `
        <div class="group-tile" data-gid="${g.id}" data-root="${escHtml(g.root_path)}" title="${escHtml(g.root_path)}">
          <div class="group-tile-thumb">
            ${iconHtml}
            <button class="group-tile-refresh" title="Refresh icon">Ôć║</button>
          </div>
          <div class="group-tile-name">${escHtml(g.name)}</div>
          <div class="group-tile-meta">${categoryBadge(g.category)} ┬Ě ${(g.file_count || 0).toLocaleString()} files</div>
          <button class="group-tile-open-btn" title="Open in Explorer">­čôé Open</button>
        </div>`;
    }).join('');

    grid.querySelectorAll('.group-tile').forEach(tile => {
      tile.querySelector('.group-tile-refresh')?.addEventListener('click', e => {
        e.stopPropagation();
        refreshGroupIcon(Number(tile.dataset.gid), e.currentTarget);
      });
      tile.querySelector('.group-tile-open-btn')?.addEventListener('click', e => {
        e.stopPropagation();
        openFolderPath(tile.dataset.root || '');
      });
      tile.addEventListener('click', () => {
        STATE.currentCategory = '';
        STATE.currentGroupId  = Number(tile.dataset.gid);
        STATE.offset          = 0;
        showView('files');
        loadFiles();
      });
    });
  } catch (err) {
    toast('Failed to load groups: ' + err.message, 'error');
  }
}

// ÔöÇÔöÇ File detail modal ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function openFileDetail(id) {
  try {
    const file = await API.getFile(id);
    const content = document.getElementById('file-detail-content');
    content.innerHTML = renderFileDetail(file, STATE.categories);
    openModal('modal-file');

    // Save button
    document.getElementById('detail-save').addEventListener('click', async () => {
      const cat  = document.getElementById('detail-category').value;
      const tags = document.getElementById('detail-tags').value;
      const desc = document.getElementById('detail-desc').value;
      try {
        await API.updateFile(id, { category: cat, tags, description: desc });
        toast('File updated.', 'success');
        closeModal('modal-file');
        if (STATE.currentView === 'files') loadFiles();
      } catch (err) { toast(err.message, 'error'); }
    });

    // Rename button
    document.getElementById('detail-rename').addEventListener('click', async () => {
      const newName = prompt('New filename:', file.name);
      if (!newName || newName === file.name) return;
      try {
        await API.renameFile(id, newName);
        toast('File renamed.', 'success');
        closeModal('modal-file');
        loadFiles();
      } catch (err) { toast(err.message, 'error'); }
    });

    // Move button
    document.getElementById('detail-move').addEventListener('click', async () => {
      const dest = prompt('Destination directory:');
      if (!dest) return;
      try {
        await API.moveFile(id, dest);
        toast('File moved.', 'success');
        closeModal('modal-file');
        loadFiles();
      } catch (err) { toast(err.message, 'error'); }
    });

    // Open Folder button
    document.getElementById('detail-open-folder').addEventListener('click', () => {
      openFolderPath(file.parent_dir);
    });

    // Delete button
    document.getElementById('detail-delete').addEventListener('click', async () => {
      const ok = await confirmAction(`Permanently delete "${file.name}"?`);
      if (!ok) return;
      try {
        await API.deleteFile(id);
        toast('File deleted.', 'success');
        closeModal('modal-file');
        loadFiles();
      } catch (err) { toast(err.message, 'error'); }
    });

  } catch (err) {
    toast('Could not load file details: ' + err.message, 'error');
  }
}

async function deleteFileById(id, name) {
  const ok = await confirmAction(`Permanently delete "${name}"?`);
  if (!ok) return;
  try {
    await API.deleteFile(id);
    toast('File deleted.', 'success');
    loadFiles();
  } catch (err) { toast(err.message, 'error'); }
}

// ÔöÇÔöÇ Re-categorize ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('btn-regroup').addEventListener('click', async () => {
  const btn = document.getElementById('btn-regroup');
  btn.disabled = true;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><rect x="2" y="7" width="6" height="10" rx="1"/><rect x="9" y="4" width="6" height="16" rx="1"/><rect x="16" y="7" width="6" height="10" rx="1"/></svg> RegroupingÔÇŽ`;
  try {
    const { job_id } = await API.startRegroup();
    toast('Regroup started.', 'info');
    pollRegroup(job_id, btn);
  } catch (err) {
    toast(err.message, 'error');
    btn.disabled = false;
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="6" height="10" rx="1"/><rect x="9" y="4" width="6" height="16" rx="1"/><rect x="16" y="7" width="6" height="10" rx="1"/></svg> Regroup`;
  }
});

function pollRegroup(jobId, btn) {
  const LABEL_IDLE = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="6" height="10" rx="1"/><rect x="9" y="4" width="6" height="16" rx="1"/><rect x="16" y="7" width="6" height="10" rx="1"/></svg> Regroup`;
  const timer = setInterval(async () => {
    try {
      const job = await API.getRecatStatus(jobId);
      if (job.status === 'done') {
        clearInterval(timer);
        toast('Regroup complete!', 'success');
        btn.disabled = false;
        btn.innerHTML = LABEL_IDLE;
        if (STATE.currentView === 'groups') showView('groups');
        else if (STATE.currentView === 'logs') loadLogsView();
        loadCategories();
      } else if (job.status === 'error') {
        clearInterval(timer);
        toast('Regroup error: ' + job.error_msg, 'error');
        btn.disabled = false;
        btn.innerHTML = LABEL_IDLE;
      }
    } catch (err) {
      clearInterval(timer);
      toast('Regroup polling lost: ' + err.message, 'error');
      btn.disabled = false;
      btn.innerHTML = LABEL_IDLE;
    }
  }, 1200);
}

document.getElementById('btn-recategorize').addEventListener('click', async () => {
  const btn = document.getElementById('btn-recategorize');
  btn.disabled = true;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Re-categorizingÔÇŽ`;
  try {
    const body = { only_auto: true, regroup: true };
    if (STATE.currentCategory) body.category = STATE.currentCategory;
    if (STATE.currentGroupId)  body.group_id  = STATE.currentGroupId;
    const { job_id } = await API.startRecategorize(body);
    toast('Re-categorize started.', 'info');
    pollRecategorize(job_id, btn);
  } catch (err) {
    toast(err.message, 'error');
    btn.disabled = false;
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Re-categorize`;
  }
});

function pollRecategorize(jobId, btn) {
  const timer = setInterval(async () => {
    try {
      const job = await API.getRecatStatus(jobId);
      if (job.status === 'done') {
        clearInterval(timer);
        toast(`Re-categorized & regrouped: ${job.changed} of ${job.total} files changed.`, 'success');
        btn.disabled = false;
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Re-categorize`;
        if (STATE.currentView === 'category') loadCategoryGroups(STATE.currentCategory);
        else if (STATE.currentView === 'logs') loadLogsView();
        else loadFiles();
      } else if (job.status === 'error') {
        clearInterval(timer);
        toast('Re-categorize error: ' + job.error_msg, 'error');
        btn.disabled = false;
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Re-categorize`;
      } else {
        // Update button with live progress
        const pct = job.progress_pct || 0;
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> ${pct}%`;
      }
    } catch (err) {
      clearInterval(timer);
      toast('Re-categorize polling lost: ' + err.message, 'error');
      btn.disabled = false;
      btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Re-categorize`;
    }
  }, 1200);
}

// ÔöÇÔöÇ Cleanup (remove missing files + fix wrong categories) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('btn-cleanup').addEventListener('click', async () => {
  const btn = document.getElementById('btn-cleanup');
  btn.disabled = true;
  btn.textContent = 'ÔĆ│';
  try {
    const result = await API.cleanup();
    toast(result.message, 'success');
    // Refresh current view (category names themselves don't change)
    if (STATE.currentView === 'category') loadCategoryGroups();
    else loadFiles();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '­čž╣';
  }
});

// ÔöÇÔöÇ Rescan all disks ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('btn-rescan-all').addEventListener('click', async () => {
  if (!confirm('This will wipe the entire database and rescan all disks from scratch.\nAny manual category overrides will be lost. Continue?')) return;

  const btn = document.getElementById('btn-rescan-all');
  btn.disabled = true;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> ScanningÔÇŽ`;

  try {
    const { job_id } = await API.rescanAll();
    openRescanModal(job_id);
  } catch (err) {
    toast('Rescan failed: ' + err.message, 'error');
    btn.disabled = false;
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Rescan All`;
  }
});

function openRescanModal(jobId) {
  // Reset modal UI
  document.getElementById('rescan-overall-fill').style.width = '0%';
  document.getElementById('rescan-overall-label').textContent = 'Counting filesÔÇŽ';
  document.getElementById('rescan-disk-rows').innerHTML = '';
  document.getElementById('btn-rescan-close').disabled = true;
  openModal('modal-rescan-all');
  pollRescanAll(jobId);
}

// Sanitize a disk path into a safe HTML id fragment: "C:\" Ôćĺ "C__"
function diskSafeId(disk) {
  return disk.replace(/[^a-zA-Z0-9]/g, '_');
}

function pollRescanAll(jobId) {
  const DISK_ICONS  = { C: '­čĺ┐', D: '­čĺż', E: '­čĺż', F: '­čĺż', G: '­čĺż' };
  const STATUS_LABEL = { pending: 'WaitingÔÇŽ', scanning: 'ScanningÔÇŽ', done: 'Ôťô Done', error: 'ÔťŚ Error' };

  let rowsBuilt = false;
  let errorCount = 0;

  STATE.scanPollTimer = setInterval(async () => {
    try {
      const job = await API.getScanStatus(jobId);
      const pct = job.progress_pct || 0;
      const dp  = (typeof job.disk_progress === 'object' && job.disk_progress !== null)
                  ? job.disk_progress : {};

      // ÔöÇÔöÇ Overall bar ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
      document.getElementById('rescan-overall-fill').style.width = pct + '%';
      const cur = job.current_disk;
      if (cur === '__finalizing__') {
        document.getElementById('rescan-overall-label').innerHTML =
          `<strong>Finalizing groupsÔÇŽ</strong> &nbsp;┬Ě&nbsp; ${job.processed.toLocaleString()} files indexed`;
      } else if (cur) {
        document.getElementById('rescan-overall-label').innerHTML =
          `<strong>Now scanning:</strong> ${escHtml(cur)} &nbsp;┬Ě&nbsp; ${job.processed.toLocaleString()} / ${job.total_files.toLocaleString()} files (${pct}%)`;
      } else if (job.total_files > 0) {
        document.getElementById('rescan-overall-label').textContent =
          `${job.processed.toLocaleString()} / ${job.total_files.toLocaleString()} files (${pct}%)`;
      }

      // ÔöÇÔöÇ Per-disk rows ÔÇö build once when data arrives ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
      const diskList = Object.keys(dp);
      if (diskList.length && !rowsBuilt) {
        rowsBuilt = true;
        const container = document.getElementById('rescan-disk-rows');
        container.innerHTML = diskList.map(disk => {
          const sid  = diskSafeId(disk);
          const icon = DISK_ICONS[disk[0].toUpperCase()] || '­čĺż';
          return `
            <div class="rescan-disk-row" id="row-${sid}">
              <div class="rescan-disk-header">
                <span class="rescan-disk-name">${icon} <strong>${escHtml(disk)}</strong></span>
                <span class="rescan-status-pending" id="status-${sid}">WaitingÔÇŽ</span>
              </div>
              <div class="rescan-disk-bar-wrap">
                <div class="rescan-disk-bar-fill" id="fill-${sid}"></div>
              </div>
              <span class="rescan-disk-count" id="count-${sid}">0 files</span>
            </div>`;
        }).join('');
      }

      // ÔöÇÔöÇ Update each disk row ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
      for (const [disk, info] of Object.entries(dp)) {
        const sid      = diskSafeId(disk);
        const fillEl   = document.getElementById('fill-'   + sid);
        const statusEl = document.getElementById('status-' + sid);
        const countEl  = document.getElementById('count-'  + sid);
        if (!fillEl) continue;

        const diskPct = info.total > 0 ? Math.round(info.processed / info.total * 100) : 0;
        fillEl.style.width       = diskPct + '%';
        fillEl.style.background  = info.status === 'done'  ? '#4caf50'
                                 : info.status === 'error' ? '#f44336'
                                 : '';   // fallback to CSS var(--accent)
        statusEl.className       = `rescan-status-${info.status || 'pending'}`;
        statusEl.textContent     = STATUS_LABEL[info.status] || info.status;
        countEl.textContent      = `${(info.processed || 0).toLocaleString()} / ${(info.total || 0).toLocaleString()} files`;
      }

      // ÔöÇÔöÇ Terminal states ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
      if (job.status === 'done') {
        clearInterval(STATE.scanPollTimer);
        document.getElementById('rescan-overall-fill').style.width = '100%';
        document.getElementById('rescan-overall-label').textContent =
          `Done ÔÇö ${job.processed.toLocaleString()} files indexed across ${diskList.length} disk(s).`;
        document.getElementById('btn-rescan-close').disabled = false;
        toast('Rescan complete!', 'success');
        loadFiles(); loadDisks(); loadCategories();
        const b = document.getElementById('btn-rescan-all');
        b.disabled = false;
        b.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Rescan All`;
      } else if (job.status === 'error') {
        clearInterval(STATE.scanPollTimer);
        document.getElementById('rescan-overall-label').textContent = 'Error: ' + (job.error_msg || 'unknown');
        document.getElementById('btn-rescan-close').disabled = false;
        toast('Rescan error: ' + job.error_msg, 'error');
        document.getElementById('btn-rescan-all').disabled = false;
      }

    } catch (err) {
      errorCount++;
      console.warn('pollRescanAll error #' + errorCount + ':', err);
      if (errorCount >= 5) {
        clearInterval(STATE.scanPollTimer);
        document.getElementById('rescan-overall-label').textContent = 'Polling failed ÔÇö check console.';
        document.getElementById('btn-rescan-close').disabled = false;
      }
    }
  }, 1500);
}

document.getElementById('btn-rescan-close').addEventListener('click', () => {
  clearInterval(STATE.scanPollTimer);
  closeModal('modal-rescan-all');
});

// ÔöÇÔöÇ Scan modal ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('btn-scan').addEventListener('click', () => {
  openModal('modal-scan');
});
document.getElementById('btn-scan-cancel').addEventListener('click', () => {
  clearInterval(STATE.scanPollTimer);
  closeModal('modal-scan');
});

document.getElementById('btn-scan-start').addEventListener('click', async () => {
  const path = document.getElementById('scan-path').value.trim();
  if (!path) { toast('Enter a directory path.', 'error'); return; }

  document.getElementById('btn-scan-start').disabled = true;
  document.getElementById('scan-progress').classList.remove('hidden');

  try {
    const { job_id } = await API.startScan(path);
    STATE.scanJobId = job_id;
    pollScanJob(job_id);
    toast('Scan started.', 'info');
  } catch (err) {
    toast('Scan failed: ' + err.message, 'error');
    document.getElementById('btn-scan-start').disabled = false;
  }
});

function pollScanJob(jobId) {
  STATE.scanPollTimer = setInterval(async () => {
    try {
      const job = await API.getScanStatus(jobId);
      const pct = job.progress_pct || 0;
      document.getElementById('progress-fill').style.width  = pct + '%';
      document.getElementById('progress-label').textContent =
        `${job.processed.toLocaleString()} / ${job.total_files.toLocaleString()} files (${pct}%)`;

      if (job.status === 'done') {
        clearInterval(STATE.scanPollTimer);
        toast('Scan complete!', 'success');
        closeModal('modal-scan');
        document.getElementById('btn-scan-start').disabled = false;
        document.getElementById('scan-progress').classList.add('hidden');
        document.getElementById('progress-fill').style.width = '0%';
        loadFiles();
        loadDisks();
        loadCategories();
      } else if (job.status === 'error') {
        clearInterval(STATE.scanPollTimer);
        toast('Scan error: ' + job.error_msg, 'error');
        document.getElementById('btn-scan-start').disabled = false;
      }
    } catch { clearInterval(STATE.scanPollTimer); }
  }, 1500);
}

// ÔöÇÔöÇ Search ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
let searchTimer;
document.getElementById('search-input').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    STATE.searchQuery = e.target.value.trim();
    STATE.offset      = 0;
    if (STATE.currentView === 'files') loadFiles();
  }, 350);
});

// ÔöÇÔöÇ Pagination buttons ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('btn-prev').addEventListener('click', () => {
  STATE.offset = Math.max(0, STATE.offset - STATE.limit);
  loadFiles();
});
document.getElementById('btn-next').addEventListener('click', () => {
  STATE.offset += STATE.limit;
  loadFiles();
});

// Category view pagination
document.addEventListener('click', e => {
  if (e.target.id === 'btn-prev-cat') {
    STATE.offset = Math.max(0, STATE.offset - STATE.limit);
    loadFiles();
  }
  if (e.target.id === 'btn-next-cat') {
    STATE.offset += STATE.limit;
    loadFiles();
  }
});

// ÔöÇÔöÇ View mode toggle ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('btn-list-view').addEventListener('click', () => {
  STATE.viewMode = 'list';
  document.getElementById('btn-list-view').classList.add('active');
  document.getElementById('btn-grid-view').classList.remove('active');
  loadFiles();
});
document.getElementById('btn-grid-view').addEventListener('click', () => {
  STATE.viewMode = 'grid';
  document.getElementById('btn-grid-view').classList.add('active');
  document.getElementById('btn-list-view').classList.remove('active');
  loadFiles();
});

// ÔöÇÔöÇ Sidebar view navigation ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.querySelectorAll('[data-view]').forEach(el => {
  el.addEventListener('click', () => showView(el.dataset.view));
});

// ÔöÇÔöÇ File modal close ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('btn-file-close').addEventListener('click', () => closeModal('modal-file'));

// ÔöÇÔöÇ Drag & drop file moving ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
document.getElementById('file-tbody').addEventListener('dragover', e => {
  e.preventDefault();
  e.currentTarget.classList.add('drop-target');
});
document.getElementById('file-tbody').addEventListener('dragleave', e => {
  e.currentTarget.classList.remove('drop-target');
});
document.getElementById('file-tbody').addEventListener('drop', async e => {
  e.preventDefault();
  e.currentTarget.classList.remove('drop-target');
  const fileId = e.dataTransfer.getData('text/plain');
  if (!fileId) return;
  const dest = prompt('Move to directory:');
  if (!dest) return;
  try {
    await API.moveFile(Number(fileId), dest);
    toast('File moved.', 'success');
    loadFiles();
  } catch (err) { toast(err.message, 'error'); }
});

// ÔöÇÔöÇ Logs view ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
async function loadLogsView() {
  const container = document.getElementById('logs-list');
  container.innerHTML = '<p style="color:var(--text-muted)">LoadingÔÇŽ</p>';

  try {
    const [scanJobs, recatJobs] = await Promise.all([
      API.getScanHistory(),
      API.getRecatHistory(),
    ]);

    // Merge and sort by started_at desc (use id as fallback)
    const entries = [
      ...scanJobs.map(j  => ({ ...j, _type: 'scan' })),
      ...recatJobs.map(j => ({ ...j, _type: 'recat' })),
    ].sort((a, b) => {
      const ta = a.started_at || '';
      const tb = b.started_at || '';
      return tb.localeCompare(ta) || b.id - a.id;
    });

    if (!entries.length) {
      container.innerHTML = '<p style="color:var(--text-muted)">No operations logged yet. Run a scan or re-categorize to see history here.</p>';
      return;
    }

    container.innerHTML = entries.map(e => renderLogEntry(e)).join('');

    // Auto-refresh running entries after 2 s
    if (entries.some(e => e.status === 'running' || e.status === 'pending')) {
      setTimeout(() => { if (STATE.currentView === 'logs') loadLogsView(); }, 2000);
    }
  } catch (err) {
    container.innerHTML = `<p style="color:var(--danger)">Failed to load logs: ${escHtml(err.message)}</p>`;
  }
}

function renderLogEntry(e) {
  const isScan  = e._type === 'scan';
  const badge   = isScan
    ? `<span class="log-badge log-badge-scan">­čöŹ Scan</span>`
    : `<span class="log-badge log-badge-recat">­čĆĚ Re-cat</span>`;

  // Scope / path label
  const scope = isScan
    ? escHtml(e.root_path || '')
    : escHtml(e.scope || 'all');

  // Status badge
  const statusCls = `log-status log-status-${e.status}`;
  const statusLabel = { pending: 'Pending', running: 'RunningÔÇŽ', done: 'Done', error: 'Error' }[e.status] || e.status;
  const statusBadge = `<span class="${statusCls}">${statusLabel}</span>`;

  // Duration
  let dur = '';
  if (e.duration_sec != null) {
    if (e.duration_sec < 60)       dur = `${e.duration_sec}s`;
    else if (e.duration_sec < 3600) dur = `${Math.floor(e.duration_sec/60)}m ${Math.round(e.duration_sec%60)}s`;
    else                            dur = `${Math.floor(e.duration_sec/3600)}h ${Math.floor((e.duration_sec%3600)/60)}m`;
  } else if (e.status === 'running') {
    dur = 'ÔÇŽ';
  }

  // Progress bar
  const pct     = e.progress_pct || 0;
  const fillCls = e.status === 'done' ? 'fill-done' : e.status === 'error' ? 'fill-error' : '';
  const bar = `<div class="log-bar-wrap"><div class="log-bar-fill ${fillCls}" style="width:${pct}%"></div></div>`;

  // Metrics row
  let meta = '';
  if (isScan) {
    const processed = (e.processed || 0).toLocaleString();
    const total     = (e.total_files || 0).toLocaleString();
    meta = `<span><strong>${processed}</strong> / <strong>${total}</strong> files</span>`;
    if (e.status === 'running' && e.current_disk)
      meta += `<span>Now: <strong>${escHtml(e.current_disk)}</strong></span>`;
    if (e.error_msg) meta += `<span style="color:var(--danger)">${escHtml(e.error_msg)}</span>`;
  } else {
    const processed = (e.processed || 0).toLocaleString();
    const total     = (e.total || 0).toLocaleString();
    const changed   = (e.changed  || 0).toLocaleString();
    meta = `<span><strong>${processed}</strong> / <strong>${total}</strong> processed</span>`;
    meta += `<span><strong>${changed}</strong> changed</span>`;
    if (e.error_msg) meta += `<span style="color:var(--danger)">${escHtml(e.error_msg)}</span>`;
  }

  const entryCls = e.status === 'running' ? 'log-entry log-running' : e.status === 'error' ? 'log-entry log-error' : 'log-entry';

  return `
    <div class="${entryCls}">
      ${badge}
      <span class="log-scope" title="${scope}">${scope}</span>
      ${statusBadge}
      <span class="log-duration">${dur}</span>
      ${bar}
      <div class="log-meta">${meta}<span>${e.started_at ? e.started_at.replace('T', ' ').slice(0, 19) : 'ÔÇö'}</span></div>
    </div>`;
}

document.getElementById('btn-logs-refresh').addEventListener('click', loadLogsView);

// ÔöÇÔöÇ Helpers ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
function escHtml(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/'/g,'&#39;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
