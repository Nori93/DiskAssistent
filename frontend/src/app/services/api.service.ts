import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  // ── Disks ──────────────────────────────────────────────────────────────────
  getDisks(): Observable<any[]> {
    return this.http.get<any[]>('/api/disks/');
  }

  getTree(path: string, depth = 2): Observable<any[]> {
    return this.http.get<any[]>('/api/disks/tree', { params: { path, depth } });
  }

  // ── Scan ───────────────────────────────────────────────────────────────────
  startScan(path: string): Observable<any> {
    return this.http.post<any>('/api/scan/start', { path });
  }

  getScanStatus(jobId: number): Observable<any> {
    return this.http.get<any>(`/api/scan/status/${jobId}`);
  }

  getActiveScan(): Observable<any> {
    return this.http.get<any>('/api/scan/active');
  }

  getScanHistory(): Observable<any[]> {
    return this.http.get<any[]>('/api/scan/history');
  }

  rescanAll(): Observable<any> {
    return this.http.post<any>('/api/scan/rescan-all', {});
  }

  // ── Files ──────────────────────────────────────────────────────────────────
  getFiles(params: Record<string, any> = {}): Observable<any> {
    let httpParams = new HttpParams();
    for (const [key, val] of Object.entries(params)) {
      if (val !== null && val !== undefined) httpParams = httpParams.set(key, String(val));
    }
    return this.http.get<any>('/api/files/', { params: httpParams });
  }

  getFile(id: number): Observable<any> {
    return this.http.get<any>(`/api/files/${id}`);
  }

  updateFile(id: number, data: Record<string, any>): Observable<any> {
    return this.http.patch<any>(`/api/files/${id}`, data);
  }

  getStats(): Observable<any> {
    return this.http.get<any>('/api/files/stats');
  }

  getCategories(): Observable<string[]> {
    return this.http.get<string[]>('/api/files/categories');
  }

  startRecategorize(body: Record<string, any> = {}): Observable<any> {
    return this.http.post<any>('/api/files/recategorize', body);
  }

  getRecatStatus(jobId: number): Observable<any> {
    return this.http.get<any>(`/api/files/recategorize/status/${jobId}`);
  }

  cleanup(): Observable<any> {
    return this.http.post<any>('/api/files/cleanup', {});
  }

  startRegroup(): Observable<any> {
    return this.http.post<any>('/api/files/regroup', {});
  }

  // ── Groups ─────────────────────────────────────────────────────────────────
  getGroups(params: Record<string, any> = {}): Observable<any> {
    let httpParams = new HttpParams();
    for (const [key, val] of Object.entries(params)) {
      if (val !== null && val !== undefined) httpParams = httpParams.set(key, String(val));
    }
    return this.http.get<any>('/api/groups/', { params: httpParams });
  }

  getGroup(id: number): Observable<any> {
    return this.http.get<any>(`/api/groups/${id}`);
  }

  getGroupTree(id: number): Observable<any> {
    return this.http.get<any>(`/api/groups/${id}/tree`);
  }

  updateGroup(id: number, data: Record<string, any>): Observable<any> {
    return this.http.patch<any>(`/api/groups/${id}`, data);
  }

  deleteGroup(id: number): Observable<any> {
    return this.http.delete<any>(`/api/groups/${id}`);
  }

  refreshGroupIcon(id: number): Observable<any> {
    return this.http.post<any>(`/api/groups/${id}/refresh-icon`, {});
  }

  // ── Operations ─────────────────────────────────────────────────────────────
  moveFile(fileId: number, destDir: string): Observable<any> {
    return this.http.post<any>('/api/operations/move', { file_id: fileId, dest_dir: destDir });
  }

  renameFile(fileId: number, newName: string): Observable<any> {
    return this.http.post<any>('/api/operations/rename', { file_id: fileId, new_name: newName });
  }

  deleteFile(fileId: number): Observable<any> {
    return this.http.delete<any>('/api/operations/delete', { body: { file_id: fileId, confirm: true } });
  }

  openFolder(path: string): Observable<any> {
    return this.http.post<any>('/api/operations/open-folder', { path });
  }

  // ── Archive ────────────────────────────────────────────────────────────────
  archiveGroup(groupId: number): Observable<any> {
    return this.http.post<any>(`/api/archive/${groupId}/archive`, {});
  }

  restoreGroup(groupId: number): Observable<any> {
    return this.http.post<any>(`/api/archive/${groupId}/restore`, {});
  }

  getArchiveStatus(groupId: number): Observable<any> {
    return this.http.get<any>(`/api/archive/${groupId}/status`);
  }

  // ── Settings ───────────────────────────────────────────────────────────────
  getSettings(): Observable<any> {
    return this.http.get<any>('/api/archive/settings');
  }

  saveSettings(data: { archive_dir: string; dedup_shared_dir: string }): Observable<any> {
    return this.http.put<any>('/api/archive/settings', data);
  }
}
