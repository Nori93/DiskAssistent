/**
 * api.js ÔÇö thin wrapper around the DiskAssistent REST API.
 * All functions return Promises.
 */

const API = (() => {
  const BASE = '';   // same origin

  async function request(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== null) opts.body = JSON.stringify(body);

    const res = await fetch(BASE + path, opts);
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    return res.json();
  }

  return {
    // ÔöÇÔöÇ Disks ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    getDisks:          ()               => request('GET', '/api/disks/'),
    getTree:           (path, depth=2)  => request('GET', `/api/disks/tree?path=${encodeURIComponent(path)}&depth=${depth}`),

    // ÔöÇÔöÇ Scan ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    startScan:         (path)           => request('POST', '/api/scan/start', { path }),
    getScanStatus:     (jobId)          => request('GET', `/api/scan/status/${jobId}`),
    getActiveScan:     ()               => request('GET', '/api/scan/active'),
    getScanHistory:    ()               => request('GET', '/api/scan/history'),

    // ÔöÇÔöÇ Files ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    getFiles:          (params = {})    => {
      const q = new URLSearchParams(params).toString();
      return request('GET', `/api/files/?${q}`);
    },
    getFile:           (id)             => request('GET', `/api/files/${id}`),
    updateFile:        (id, data)       => request('PATCH', `/api/files/${id}`, data),
    getStats:          ()               => request('GET', '/api/files/stats'),
    getCategories:     ()               => request('GET', '/api/files/categories'),
    startRecategorize: (body = {})      => request('POST', '/api/files/recategorize', body),
    getRecatStatus:    (jobId)          => request('GET', `/api/files/recategorize/status/${jobId}`),
    getRecatHistory:   ()               => request('GET', '/api/files/recategorize/history'),
    startRegroup:      ()               => request('POST', '/api/files/regroup'),
    cleanup:           ()               => request('POST', '/api/files/cleanup'),
    rescanAll:         ()               => request('POST', '/api/scan/rescan-all'),

    // ÔöÇÔöÇ Operations ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    moveFile:          (fileId, destDir)  => request('POST', '/api/operations/move', { file_id: fileId, dest_dir: destDir }),
    renameFile:        (fileId, newName)  => request('POST', '/api/operations/rename', { file_id: fileId, new_name: newName }),
    deleteFile:        (fileId)           => request('DELETE', '/api/operations/delete', { file_id: fileId, confirm: true }),    openFolder:        (path)             => request('POST', '/api/operations/open-folder', { path }),
    // ÔöÇÔöÇ Groups ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    getGroups:         (params = {})    => {
      const q = new URLSearchParams(params).toString();
      return request('GET', `/api/groups/${q ? '?' + q : ''}`);
    },
    getGroup:          (id)             => request('GET', `/api/groups/${id}`),
    getGroupTree:      (id)             => request('GET', `/api/groups/${id}/tree`),
    refreshGroupIcon:  (id)             => request('POST', `/api/groups/${id}/refresh-icon`),
    updateGroup:       (id, data)       => request('PATCH', `/api/groups/${id}`, data),
  };
})();
