import { ChangeDetectorRef, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from './services/api.service';

interface Toast { id: number; message: string; type: string; }
interface FlatNode {
  id: string;
  type: 'folder' | 'file';
  name: string;
  path: string;
  depth: number;
  fileCount: number;
  file?: any;
  parentPaths: string[];
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<!-- ═══════════════════════════════════════════════ SIDEBAR ══ -->
<aside id="sidebar">
  <div class="sidebar-header">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="3" width="20" height="14" rx="2"/>
      <line x1="8" y1="21" x2="16" y2="21"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
    <span>DiskAssistent</span>
  </div>

  <section class="sidebar-section">
    <div class="sidebar-section-title">Disks</div>
    <ul class="nav-list">
      @for (disk of disks; track disk.path) {
        <li class="nav-item disk-nav-item" [class.active]="activeDiskPath === disk.path" (click)="selectDisk(disk)">
          <span class="nav-icon">💾</span>
          <div class="disk-nav-info">
            <div class="disk-nav-top">
              <span class="disk-nav-label">{{disk.label || disk.path}}</span>
              <span class="disk-nav-pct" [class.disk-pct-warn]="disk.pct_used > 85">{{disk.pct_used}}%</span>
            </div>
            <div class="disk-bar">
              <div class="disk-bar-fill" [class.disk-bar-warn]="disk.pct_used > 85" [style.width.%]="disk.pct_used"></div>
            </div>
            <div class="disk-nav-bottom">
              <span>{{disk.used_human}} used</span>
              <span>{{disk.free_human}} free / {{disk.total_human}}</span>
            </div>
          </div>
        </li>
      }
    </ul>
  </section>

  <section class="sidebar-section">
    <div class="sidebar-section-title-row">
      <span class="sidebar-section-title">Categories</span>
      <button class="sidebar-icon-btn" (click)="runCleanup()" title="Remove missing files &amp; fix wrong categories">🧹</button>
    </div>
    <ul class="nav-list">
      <li class="nav-item" [class.active]="currentCategory === '' && currentView !== 'dashboard' && currentView !== 'groups' && currentView !== 'logs'" (click)="selectCategory('')">
        <span class="nav-icon">📁</span> All Files
      </li>
      @for (cat of categories; track cat) {
        <li class="nav-item" [class.active]="currentCategory === cat" (click)="selectCategory(cat)">
          <span class="nav-icon">{{catIcon(cat)}}</span> {{cat}}
        </li>
      }
    </ul>
  </section>

  <section class="sidebar-section">
    <div class="sidebar-section-title">Views</div>
    <ul class="nav-list">
      <li class="nav-item" [class.active]="currentView === 'dashboard'" (click)="showView('dashboard')"><span class="nav-icon">📊</span> Dashboard</li>
      <li class="nav-item" [class.active]="currentView === 'groups'"    (click)="showView('groups')"><span class="nav-icon">📦</span> Groups</li>
      <li class="nav-item" [class.active]="currentView === 'logs'"      (click)="showView('logs')"><span class="nav-icon">📋</span> Logs</li>
    </ul>
  </section>
</aside>

<!-- ═══════════════════════════════════════════════ MAIN ════════ -->
<main id="main">
  <header id="topbar">
    <div id="search-wrapper">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input id="search-input" type="text" placeholder="Search files…" autocomplete="off"
        [(ngModel)]="search" (input)="onSearch()" />
    </div>
    <div id="topbar-actions">
      <button class="btn" (click)="runRescanAll()" title="Wipe database and rescan all disks from scratch">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
        </svg> Rescan All
      </button>
      <button class="btn" (click)="runRegroup()" title="Rebuild file groups from current database (no disk scan)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="7" width="6" height="10" rx="1"/><rect x="9" y="4" width="6" height="16" rx="1"/><rect x="16" y="7" width="6" height="10" rx="1"/>
        </svg> Regroup
      </button>
      <button class="btn" (click)="runRecategorize()" title="Re-run AI categorization on all auto-categorized files">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg> Re-categorize
      </button>
      <button class="btn btn-primary" (click)="openScanModal()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
        </svg> Scan Directory
      </button>
      <span id="view-mode-toggle">
        <button class="icon-btn" [class.active]="viewMode === 'list'" (click)="setViewMode('list')" title="List view">☰</button>
        <button class="icon-btn" [class.active]="viewMode === 'grid'" (click)="setViewMode('grid')" title="Grid view">⊞</button>
      </span>
    </div>
  </header>

  <div id="content">

    <!-- ── CATEGORY GROUP TILES VIEW ── -->
    <div class="view" [class.active]="currentView === 'category'">
      <div class="category-view-header">
        <h2 class="view-title">{{categoryTitle}}</h2>
      </div>
      <div class="groups-tiles-grid">
        @for (g of categoryGroups; track g.id) {
          <div class="group-tile" (click)="openGroupExplorer(g)" [title]="g.root_path">
            <div class="group-tile-thumb">
              @if (g.thumbnail_path) {
                <img class="group-tile-img" [src]="'/api/groups/' + g.id + '/thumbnail?t=' + (g._ts || 0)" [alt]="g.name" (error)="g.thumbnail_path = ''" />
              } @else {
                <div class="group-tile-icon">{{catIcon(g.category)}}</div>
              }
              <button class="group-tile-refresh" title="Refresh icon" (click)="stopAndRefreshIcon($event, g.id)">↺</button>
            </div>
            <div class="group-tile-name">{{g.name}}</div>
            <div class="group-tile-meta"><span [class]="'badge badge-' + g.category">{{g.category}}</span> · {{(g.file_count || 0) | number}} files@if (g.is_archived) { <span style="margin-left:6px;font-size:11px;color:#6dbf6d">✅ Archived</span>}</div>
            <button class="group-tile-open-btn" (click)="stopAndOpenFolder($event, g.root_path)">📂 Open</button>
          </div>
        }
        @empty { <p style="color:var(--text-muted)">No groups found for this category.</p> }
      </div>
    </div>

    <!-- ── FILE EXPLORER (group detail) VIEW ── -->
    <div class="view" [class.active]="currentView === 'explorer'">
      <div class="category-view-header" style="margin-bottom:12px">
        <button class="btn btn-sm" (click)="backToCategory()">← {{categoryTitle}}</button>
        <span style="color:var(--text-muted);margin:0 8px">/</span>
        <strong>{{explorerGroup?.name}}</strong>
        <span style="margin-left:auto;font-size:13px;color:var(--text-muted)">{{explorerFileCount | number}} files</span>
        <button class="btn btn-sm" title="Open folder in Explorer" (click)="stopAndOpenFolder($event, explorerGroup?.root_path)">📂 Open Folder</button>
        <button class="btn btn-sm" title="Refresh icon" (click)="stopAndRefreshIcon($event, explorerGroup?.id)">↺ Refresh Icon</button>
        @if (!explorerGroup?.is_archived) {
          <button class="btn btn-sm" title="Archive group to archive directory" (click)="archiveExplorerGroup($event)"
            [disabled]="archiveJobStatus === 'running'">
            📦 Archive
          </button>
        } @else {
          <button class="btn btn-sm" title="Restore group from archive" (click)="unarchiveExplorerGroup($event)"
            [disabled]="archiveJobStatus === 'running'">
            ♻️ Unarchive
          </button>
        }
        <button class="btn btn-sm btn-danger" title="Delete this group" (click)="deleteExplorerGroup($event)" [disabled]="archiveJobStatus === 'running'">🗑 Delete Group</button>
      </div>
      @if (archiveJobStatus === 'running') {
        <div style="margin-bottom:12px;padding:10px 12px;background:var(--surface);border-radius:6px;display:flex;align-items:center;gap:12px">
          <span style="font-size:13px">{{_archiveJobType === 'restore' ? '♻️ Restoring…' : '📦 Archiving…'}} {{archiveJobProgress}}%</span>
          <div style="flex:1;background:var(--border);border-radius:4px;height:6px">
            <div style="height:6px;border-radius:4px;background:var(--accent);transition:width .4s" [style.width.%]="archiveJobProgress"></div>
          </div>
        </div>
      }
      @if (archiveJobStatus === 'done') {
        <div style="margin-bottom:12px;padding:10px 12px;background:#1a3a1a;border-radius:6px;font-size:13px">✅ {{_archiveJobType === 'restore' ? 'Restore complete.' : 'Archive complete.'}}</div>
      }
      @if (archiveJobStatus === 'error') {
        <div style="margin-bottom:12px;padding:10px 12px;background:#3a1a1a;border-radius:6px;font-size:13px">❌ {{_archiveJobType === 'restore' ? 'Restore error:' : 'Archive error:'}} {{archiveJobError}}</div>
      }
      <div id="file-explorer">
        @if (explorerLoading) {
          <p style="color:var(--text-muted);padding:24px">Loading…</p>
        } @else {
          @for (node of visibleNodes; track node.id) {
            @if (node.type === 'folder') {
              <div class="fe-row fe-folder-row" [style.padding-left.px]="8 + node.depth * 20"
                   (click)="toggleFolder(node.path)">
                <span class="fe-chevron">{{collapsedPaths.has(node.path) ? '▶' : '▼'}}</span>
                <span class="fe-icon-folder">📁</span>
                <span class="fe-name">{{node.name}}</span>
                <span class="fe-badge">{{node.fileCount | number}}</span>
                <button class="fe-open-btn" title="Open in Explorer" (click)="stopAndOpenFolder($event, node.path)">📂</button>
              </div>
            } @else {
              <div class="fe-row fe-file-row" [style.padding-left.px]="8 + node.depth * 20 + 20"
                   (click)="openFileDetail(node.file.id)">
                <span class="fe-icon-file">{{fileIcon(node.file.extension)}}</span>
                <span class="fe-name fe-file-name" [title]="node.file.full_path">{{node.file.name}}</span>
                <span class="fe-size">{{humanSize(node.file.size_bytes)}}</span>
                <span class="fe-date">{{node.file.modified_at ? (node.file.modified_at | date:'shortDate') : '—'}}</span>
                <span class="fe-actions">
                  <button class="btn btn-sm fe-info-btn" title="Details" (click)="$event.stopPropagation(); openFileDetail(node.file.id)">ℹ</button>
                </span>
              </div>
            }
          }
          @empty {
            <p style="color:var(--text-muted);padding:24px">No files found.</p>
          }
        }
      </div>
    </div>

    <!-- ── FILE LIST VIEW ── -->
    <div class="view" [class.active]="currentView === 'files'">
      <div id="files-toolbar">
        <span id="files-count">{{total | number}} file{{total !== 1 ? 's' : ''}}</span>
        <div id="pagination-controls">
          <button class="btn btn-sm" [disabled]="offset === 0" (click)="prevPage()">‹ Prev</button>
          <span id="page-info">Page {{currentPage}} / {{totalPages}}</span>
          <button class="btn btn-sm" [disabled]="offset + limit >= total" (click)="nextPage()">Next ›</button>
        </div>
      </div>

      @if (viewMode === 'list') {
        <table class="file-table">
          <thead>
            <tr><th>Name</th><th>Category</th><th>Extension</th><th>Size</th><th>Modified</th><th>Actions</th></tr>
          </thead>
          <tbody>
            @for (f of files; track f.id) {
              <tr [class.missing]="f.is_missing" (click)="openFileDetail(f.id)" style="cursor:pointer">
                <td class="cell-name" [title]="f.full_path">
                  {{fileIcon(f.extension)}} {{f.name}}
                  @if (f.is_missing) { <span class="badge badge-Other" style="font-size:9px">MISSING</span> }
                </td>
                <td><span [class]="'badge badge-' + f.category">{{f.category}}</span></td>
                <td>{{f.extension || '—'}}</td>
                <td>{{humanSize(f.size_bytes)}}</td>
                <td>{{f.modified_at ? (f.modified_at | date:'shortDate') : '—'}}</td>
                <td class="cell-actions" (click)="$event.stopPropagation()">
                  <button class="btn btn-sm" (click)="openFileDetail(f.id)">ℹ</button>
                  <button class="btn btn-sm btn-danger" (click)="deleteFileById(f.id, f.name)">🗑</button>
                </td>
              </tr>
            }
            @empty {
              <tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-muted)">No files found.</td></tr>
            }
          </tbody>
        </table>
      }

      @if (viewMode === 'grid') {
        <div class="file-grid" style="padding:20px">
          @for (f of files; track f.id) {
            <div class="grid-card" (click)="openFileDetail(f.id)">
              <div class="grid-card-thumb">{{fileIcon(f.extension)}}</div>
              <div class="grid-card-body">
                <div class="grid-card-name" [title]="f.name">{{f.name}}</div>
                <div class="grid-card-meta">{{humanSize(f.size_bytes)}} · <span [class]="'badge badge-' + f.category" style="font-size:10px">{{f.category}}</span></div>
              </div>
            </div>
          }
          @empty { <p style="color:var(--text-muted);grid-column:1/-1">No files found.</p> }
        </div>
      }
    </div>

    <!-- ── DASHBOARD VIEW ── -->
    <div class="view" [class.active]="currentView === 'dashboard'">
      <h2 class="view-title">Dashboard</h2>
      @if (stats) {
        <div class="stat-cards">
          <div class="stat-card">
            <div class="stat-card-label">Total Files</div>
            <div class="stat-card-value">{{stats.total_files | number}}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-label">Total Size</div>
            <div class="stat-card-value">{{humanSize(stats.total_size)}}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-label">Missing Files</div>
            <div class="stat-card-value" style="color:var(--danger)">{{stats.missing_files | number}}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-label">Categories</div>
            <div class="stat-card-value">{{stats.by_category?.length}}</div>
          </div>
        </div>
        <div class="charts-row">
          <div class="chart-card">
            <h3>Files by Category</h3>
            @for (item of stats.by_category; track item.category) {
              <div class="bar-chart-row">
                <div class="bar-chart-label" [title]="item.category">{{item.category}}</div>
                <div class="bar-chart-track">
                  <div class="bar-chart-fill" [style.width.%]="maxCategoryCount > 0 ? (item.count / maxCategoryCount * 100) : 0"></div>
                </div>
                <div class="bar-chart-count">{{item.count | number}}</div>
              </div>
            }
          </div>
          <div class="chart-card">
            <h3>Top Extensions</h3>
            @for (item of topExtensions; track item.extension) {
              <div class="bar-chart-row">
                <div class="bar-chart-label" [title]="item.extension">{{item.extension}}</div>
                <div class="bar-chart-track">
                  <div class="bar-chart-fill" [style.width.%]="maxExtCount > 0 ? (item.count / maxExtCount * 100) : 0"></div>
                </div>
                <div class="bar-chart-count">{{item.count | number}}</div>
              </div>
            }
          </div>
        </div>
      } @else {
        <p style="color:var(--text-muted);padding:40px 0">Loading stats…</p>
      }
    </div>

    <!-- ── GROUPS VIEW ── -->
    <div class="view" [class.active]="currentView === 'groups'">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
        <h2 class="view-title" style="margin:0">Detected Groups</h2>
        <button class="btn btn-sm" (click)="refreshAllIcons()" [disabled]="refreshAllInProgress" style="margin-left:auto">
          ↺ {{refreshAllInProgress ? 'Refreshing… (' + refreshAllDone + '/' + refreshAllTotal + ')' : 'Refresh All Icons'}}
        </button>
      </div>
      <div class="file-grid">
        @for (g of groups; track g.id) {
          <div class="group-tile" (click)="openGroupExplorer(g)" [title]="g.root_path">
            <div class="group-tile-thumb">
              @if (g.thumbnail_path) {
                <img class="group-tile-img" [src]="'/api/groups/' + g.id + '/thumbnail?t=' + (g._ts || 0)" [alt]="g.name" (error)="g.thumbnail_path = ''" />
              } @else {
                <div class="group-tile-icon">{{catIcon(g.category)}}</div>
              }
              <button class="group-tile-refresh" title="Refresh icon" (click)="stopAndRefreshIcon($event, g.id)">↺</button>
            </div>
            <div class="group-tile-name">{{g.name}}</div>
            <div class="group-tile-meta"><span [class]="'badge badge-' + g.category">{{g.category}}</span> · {{(g.file_count || 0) | number}} files@if (g.is_archived) { <span style="margin-left:6px;font-size:11px;color:#6dbf6d">✅ Archived</span>}</div>
            <button class="group-tile-open-btn" (click)="stopAndOpenFolder($event, g.root_path)">📂 Open</button>
          </div>
        }
        @empty { <p style="color:var(--text-muted)">No groups detected yet. Run a scan first.</p> }
      </div>
    </div>

    <!-- ── LOGS VIEW ── -->
    <div class="view" [class.active]="currentView === 'logs'">
      <div class="logs-header">
        <h2 class="view-title">Operation Logs</h2>
        <button class="btn btn-sm" (click)="loadLogsView()">↺ Refresh</button>
      </div>
      <div id="logs-list">
        @for (log of logs; track log.id) {
          <div class="log-entry" [class.log-running]="log.status === 'running'" [class.log-error]="log.status === 'error'">
            <span [class]="'log-badge ' + (log.type === 'recat' ? 'log-badge-recat' : 'log-badge-scan')">{{log.type === 'recat' ? 'RECAT' : 'SCAN'}}</span>
            <span class="log-scope">{{log.path || log.scope || 'All disks'}}</span>
            <span [class]="'log-status log-status-' + log.status">{{log.status}}</span>
            <span class="log-duration">{{logDuration(log)}}</span>
            <div class="log-bar-wrap">
              <div class="log-bar-fill" [class.fill-done]="log.status === 'done'" [class.fill-error]="log.status === 'error'" [style.width.%]="logProgress(log)"></div>
            </div>
            <div class="log-meta">
              <span><strong>{{log.files_found || 0}}</strong> found</span>
              <span><strong>{{log.files_new || 0}}</strong> new</span>
              @if (log.started_at) { <span>{{log.started_at | date:'short'}}</span> }
            </div>
          </div>
        }
        @empty { <p style="color:var(--text-muted)">No scan history found.</p> }
      </div>
    </div>

  </div><!-- /#content -->
</main>

<!-- ═══════════════════════════════════════════════ MODALS ═══════ -->

<!-- Scan modal -->
<div class="modal-backdrop" [class.hidden]="!showScanModal" (click)="closeScanModal()">
  <div class="modal" (click)="$event.stopPropagation()">
    <h3>Scan Directory</h3>
    <label>Directory path</label>
    <input type="text" [(ngModel)]="scanPath" placeholder="e.g. C:\\Users or /home/user" (keyup.enter)="startScan()" />
    @if (scanInProgress) {
      <div id="scan-progress">
        <div class="progress-bar"><div id="progress-fill" [style.width.%]="scanProgress"></div></div>
        <span id="progress-label">{{scanProgressLabel}}</span>
      </div>
    }
    <div class="modal-footer">
      <button class="btn" (click)="closeScanModal()" [disabled]="scanInProgress">Cancel</button>
      <button class="btn btn-primary" (click)="startScan()" [disabled]="scanInProgress">Start Scan</button>
    </div>
  </div>
</div>

<!-- Rescan-all modal -->
<div class="modal-backdrop" [class.hidden]="!showRescanModal">
  <div class="modal modal-rescan">
    <h3>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:-3px;margin-right:6px">
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
      </svg>
      Rescanning All Disks
    </h3>
    <p class="rescan-overall-label">{{rescanLabel}}</p>
    <div class="progress-bar rescan-overall-bar"><div id="rescan-overall-fill" [style.width.%]="rescanProgress"></div></div>
    <div class="modal-footer">
      <button class="btn" [disabled]="!rescanDone" (click)="showRescanModal = false">Close</button>
    </div>
  </div>
</div>

<!-- File details modal -->
<div class="modal-backdrop" [class.hidden]="!showFileModal" (click)="closeFileModal()">
  <div class="modal modal-lg" (click)="$event.stopPropagation()">
    <button class="modal-close" (click)="closeFileModal()">✕</button>
    @if (selectedFile) {
      <h3>{{fileIcon(selectedFile.extension)}} {{selectedFile.name}}</h3>
      <div class="detail-grid">
        <div class="detail-item detail-full">
          <label>Full Path</label>
          <p class="truncate">{{selectedFile.full_path}}</p>
        </div>
        <div class="detail-item"><label>Size</label><p>{{humanSize(selectedFile.size_bytes)}}</p></div>
        <div class="detail-item"><label>Extension</label><p>{{selectedFile.extension || '—'}}</p></div>
        <div class="detail-item"><label>Modified</label><p>{{selectedFile.modified_at | date:'medium'}}</p></div>
        <div class="detail-item"><label>Created</label><p>{{selectedFile.created_at | date:'medium'}}</p></div>
        <div class="detail-item detail-full">
          <label>Category</label>
          <select [(ngModel)]="selectedFile.category" class="mt-1">
            @for (cat of categories; track cat) { <option [value]="cat">{{cat}}</option> }
          </select>
          @if (selectedFile.category_overridden) {
            <small class="text-muted"> (manually set)</small>
          } @else {
            <small class="text-muted"> AI suggested: {{selectedFile.ai_category}}</small>
          }
        </div>
        <div class="detail-item detail-full">
          <label>Tags (comma-separated)</label>
          <input type="text" [(ngModel)]="selectedFile.tags" />
        </div>
        <div class="detail-item detail-full">
          <label>Description</label>
          <textarea rows="3" [(ngModel)]="selectedFile.description"></textarea>
        </div>
      </div>
      <div class="detail-actions">
        <button class="btn btn-primary" (click)="saveFileDetail()">Save Changes</button>
        <button class="btn" (click)="renameSelectedFile()">Rename</button>
        <button class="btn" (click)="moveSelectedFile()">Move</button>
        <button class="btn" (click)="openFolderPath(selectedFile.parent_dir)">📂 Open Folder</button>
        <button class="btn btn-danger" (click)="deleteSelectedFile()">Delete</button>
      </div>
    }
  </div>
</div>

<!-- Confirm modal -->
<div class="modal-backdrop" [class.hidden]="!showConfirmModal">
  <div class="modal modal-sm">
    <h3>{{confirmTitle}}</h3>
    <p>{{confirmMessage}}</p>
    <div class="modal-footer">
      <button class="btn" (click)="resolveConfirm(false)">Cancel</button>
      <button class="btn btn-danger" (click)="resolveConfirm(true)">{{confirmLabel}}</button>
    </div>
  </div>
</div>

<!-- Toast notifications -->
<div id="toast-container">
  @for (t of toasts; track t.id) {
    <div class="toast" [class.error]="t.type === 'error'" [class.success]="t.type === 'success'">{{t.message}}</div>
  }
</div>
  `,
})
export class AppComponent implements OnInit, OnDestroy {

  // ── Data ──────────────────────────────────────────────────────
  disks: any[] = [];
  files: any[] = [];
  categories: string[] = [];
  groups: any[] = [];
  logs: any[] = [];
  stats: any = null;
  categoryGroups: any[] = [];

  // ── Explorer state ────────────────────────────────────────────
  explorerGroup: any = null;
  explorerLoading = false;
  explorerNodes: FlatNode[] = [];
  collapsedPaths = new Set<string>();

  get visibleNodes(): FlatNode[] {
    return this.explorerNodes.filter(
      node => !node.parentPaths.some(p => this.collapsedPaths.has(p))
    );
  }

  get explorerFileCount(): number {
    return this.explorerNodes.filter(n => n.type === 'file').length;
  }

  // ── State ─────────────────────────────────────────────────────
  total = 0;
  offset = 0;
  limit = 50;
  search = '';
  currentCategory = '';
  currentGroupId: number | null = null;
  currentView = 'files';
  viewMode: 'list' | 'grid' = 'list';
  activeDiskPath = '';
  categoryTitle = '';

  // ── Scan modal ────────────────────────────────────────────────
  showScanModal = false;
  scanPath = '';
  scanInProgress = false;
  scanProgress = 0;
  scanProgressLabel = '';

  // ── Rescan-all modal ──────────────────────────────────────────
  showRescanModal = false;
  rescanProgress = 0;
  rescanLabel = 'Counting files…';
  rescanDone = false;

  // ── File detail modal ─────────────────────────────────────────
  showFileModal = false;
  selectedFile: any = null;

  // ── Confirm modal ─────────────────────────────────────────────
  showConfirmModal = false;
  confirmMessage = '';
  confirmTitle = 'Confirm Delete';
  confirmLabel = 'Delete';
  private confirmResolve: ((v: boolean) => void) | null = null;

  // ── Toast ─────────────────────────────────────────────────────
  toasts: Toast[] = [];
  private toastCounter = 0;

  // ── Poll timer ────────────────────────────────────────────────
  private pollTimer: any = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadDisks();
    this.loadCategories();
    this.loadFiles();
  }

  ngOnDestroy(): void {
    if (this.pollTimer) clearTimeout(this.pollTimer);
  }

  // ── Data loading ──────────────────────────────────────────────

  loadDisks(): void {
    this.api.getDisks().subscribe({
      next: (d) => { this.disks = d; },
      error: (e) => this.toast('Failed to load disks: ' + e.message, 'error'),
    });
  }

  loadCategories(): void {
    this.api.getCategories().subscribe({ next: (c) => { this.categories = c; } });
  }

  loadFiles(): void {
    const params: Record<string, any> = { limit: this.limit, offset: this.offset };
    if (this.search) params['search'] = this.search;
    if (this.currentCategory) params['category'] = this.currentCategory;
    if (this.currentGroupId !== null) params['group_id'] = this.currentGroupId;

    this.api.getFiles(params).subscribe({
      next: (res) => {
        this.files = res.items ?? res.files ?? res;
        this.total = res.total ?? this.files.length;
      },
      error: (e) => this.toast('Failed to load files: ' + e.message, 'error'),
    });
  }

  loadDashboard(): void {
    this.api.getStats().subscribe({
      next: (s) => { this.stats = s; },
      error: (e) => this.toast('Failed to load stats: ' + e.message, 'error'),
    });
  }

  loadGroups(): void {
    this.api.getGroups().subscribe({
      next: (res) => { this.groups = Array.isArray(res) ? res : (res.groups ?? []); },
      error: (e) => this.toast('Failed to load groups: ' + e.message, 'error'),
    });
  }

  loadLogsView(): void {
    this.api.getScanHistory().subscribe({
      next: (h) => { this.logs = (h ?? []).map((j: any) => ({ ...j, type: 'scan' })); },
      error: (e) => this.toast('Failed to load logs: ' + e.message, 'error'),
    });
  }

  // ── View switching ────────────────────────────────────────────

  showView(name: string): void {
    this.currentView = name;
    this.currentGroupId = null;
    this.currentCategory = '';
    if (name === 'dashboard') this.loadDashboard();
    else if (name === 'groups') this.loadGroups();
    else if (name === 'logs') this.loadLogsView();
    else if (name === 'files') this.loadFiles();
  }

  // ── Sidebar ───────────────────────────────────────────────────

  selectCategory(cat: string): void {
    this.currentCategory = cat;
    this.currentGroupId = null;
    this.offset = 0;

    if (cat) {
      this.currentView = 'category';
      this.categoryTitle = cat;
      this.api.getGroups({ category: cat }).subscribe({
        next: (res) => { this.categoryGroups = Array.isArray(res) ? res : (res.groups ?? []); },
        error: (e) => this.toast('Failed to load groups: ' + e.message, 'error'),
      });
    } else {
      this.currentView = 'files';
      this.loadFiles();
    }
  }

  selectDisk(disk: any): void {
    this.activeDiskPath = disk.path;
    this.scanPath = disk.path;
    this.showScanModal = true;
  }

  openGroupExplorer(group: any): void {
    this.explorerGroup = group;
    this.explorerLoading = true;
    this.collapsedPaths.clear();
    this.explorerNodes = [];
    this.currentView = 'explorer';

    this.api.getGroupTree(group.id).subscribe({
      next: (tree) => {
        this.explorerNodes = [];
        this._flattenTree(tree, 0, []);
        // Collapse all folders by default
        this.collapsedPaths = new Set(
          this.explorerNodes.filter(n => n.type === 'folder').map(n => n.path)
        );
        this.explorerLoading = false;
      },
      error: (e) => {
        this.explorerLoading = false;
        this.toast('Failed to load group files: ' + e.message, 'error');
      },
    });
  }

  private _flattenTree(node: any, depth: number, parentPaths: string[]): void {
    const sortedFolders = Object.keys(node.children || {}).sort((a, b) =>
      a.localeCompare(b, undefined, { sensitivity: 'base' })
    );
    const sortedFiles = [...(node.files || [])].sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
    );

    for (const folderName of sortedFolders) {
      const child = node.children[folderName];
      const fc = this._countTreeFiles(child);
      this.explorerNodes.push({
        id: 'f_' + child.path,
        type: 'folder',
        name: folderName,
        path: child.path,
        depth,
        fileCount: fc,
        parentPaths: [...parentPaths],
      });
      this._flattenTree(child, depth + 1, [...parentPaths, child.path]);
    }

    for (const file of sortedFiles) {
      this.explorerNodes.push({
        id: 'file_' + file.id,
        type: 'file',
        name: file.name,
        path: file.full_path,
        depth,
        fileCount: 0,
        file,
        parentPaths: [...parentPaths],
      });
    }
  }

  private _countTreeFiles(node: any): number {
    let n = (node.files || []).length;
    for (const child of Object.values(node.children || {})) {
      n += this._countTreeFiles(child);
    }
    return n;
  }

  toggleFolder(path: string): void {
    if (this.collapsedPaths.has(path)) this.collapsedPaths.delete(path);
    else this.collapsedPaths.add(path);
    // Force angular to re-evaluate visibleNodes getter
    this.collapsedPaths = new Set(this.collapsedPaths);
  }

  backToCategory(): void {
    this.currentView = 'category';
    this.explorerGroup = null;
    this.archiveJobStatus = 'idle';
    this.archiveJobProgress = 0;
    if (this.archivePollTimer) { clearTimeout(this.archivePollTimer); this.archivePollTimer = null; }
  }

  archiveJobStatus: 'idle' | 'running' | 'done' | 'error' = 'idle';
  archiveJobProgress = 0;
  archiveJobError = '';
  private archivePollTimer: any = null;
  _archiveJobType: 'archive' | 'restore' = 'archive';

  archiveExplorerGroup(event: MouseEvent): void {
    event.stopPropagation();
    const g = this.explorerGroup;
    if (!g) return;
    this.confirmAction(`Archive group "${g.name}"? Files will be moved to the archive directory.`, 'Confirm Archive', 'Archive').then(ok => {
      if (!ok) return;
      this.api.archiveGroup(g.id).subscribe({
        next: () => {
          this.toast(`Archive started for "${g.name}".`, 'success');
          this.archiveJobStatus = 'running';
          this.archiveJobProgress = 0;
          this._archiveJobType = 'archive';
          this._pollArchive(g.id);
        },
        error: (e) => this.toast('Archive failed: ' + (e.error?.detail || e.message), 'error'),
      });
    });
  }

  unarchiveExplorerGroup(event: MouseEvent): void {
    event.stopPropagation();
    const g = this.explorerGroup;
    if (!g) return;
    this.confirmAction(`Restore group "${g.name}" from archive? Files will be moved back to their original location.`, 'Confirm Unarchive', 'Unarchive').then(ok => {
      if (!ok) return;
      this.api.restoreGroup(g.id).subscribe({
        next: () => {
          this.toast(`Restore started for "${g.name}".`, 'success');
          this.archiveJobStatus = 'running';
          this.archiveJobProgress = 0;
          this._archiveJobType = 'restore';
          this._pollArchive(g.id);
        },
        error: (e) => this.toast('Unarchive failed: ' + (e.error?.detail || e.message), 'error'),
      });
    });
  }

  private _pollArchive(groupId: number): void {
    if (this.archivePollTimer) clearTimeout(this.archivePollTimer);
    this.api.getArchiveStatus(groupId).subscribe({
      next: (s) => {
        this.archiveJobProgress = s.progress ?? 0;
        if (s.status === 'running') {
          this.archivePollTimer = setTimeout(() => this._pollArchive(groupId), 2000);
        } else if (s.status === 'done') {
          this.archiveJobStatus = 'done';
          this.archiveJobProgress = 100;
          // Sync is_archived flag based on job type
          if (this.explorerGroup) {
            const archived = this._archiveJobType === 'archive';
            this.explorerGroup.is_archived = archived;
            const id = this.explorerGroup.id;
            const patch = (arr: any[]) => { const g = arr.find(x => x.id === id); if (g) g.is_archived = archived; };
            patch(this.groups);
            patch(this.categoryGroups);
          }
        } else if (s.status === 'error') {
          this.archiveJobStatus = 'error';
          this.archiveJobError = s.error || 'Unknown error';
        }
      },
      error: () => {
        this.archivePollTimer = setTimeout(() => this._pollArchive(groupId), 3000);
      },
    });
  }

  deleteExplorerGroup(event: MouseEvent): void {
    event.stopPropagation();
    const g = this.explorerGroup;
    if (!g) return;
    this.confirmAction(`Permanently delete group "${g.name}" and all its file records?`).then(ok => {
      if (!ok) return;
      this.api.deleteGroup(g.id).subscribe({
        next: () => {
          this.toast(`Group "${g.name}" deleted.`, 'success');
          this.groups = this.groups.filter(x => x.id !== g.id);
          this.categoryGroups = this.categoryGroups.filter(x => x.id !== g.id);
          this.backToCategory();
        },
        error: (e) => this.toast('Delete failed: ' + e.message, 'error'),
      });
    });
  }

  openCategoryGroup(group: any): void {
    this.openGroupExplorer(group);
  }

  openGroup(group: any): void {
    this.openGroupExplorer(group);
  }

  // ── Topbar ────────────────────────────────────────────────────

  onSearch(): void {
    this.offset = 0;
    this.loadFiles();
  }

  setViewMode(mode: 'list' | 'grid'): void { this.viewMode = mode; }

  runCleanup(): void {
    this.api.cleanup().subscribe({
      next: (res) => { this.toast(`Cleanup done: ${res.removed ?? 0} records removed.`, 'success'); this.loadFiles(); },
      error: (e) => this.toast('Cleanup failed: ' + e.message, 'error'),
    });
  }

  runRegroup(): void {
    this.api.startRegroup().subscribe({
      next: () => this.toast('Regroup started.', 'success'),
      error: (e) => this.toast('Regroup failed: ' + e.message, 'error'),
    });
  }

  runRecategorize(): void {
    this.api.startRecategorize().subscribe({
      next: (res) => { this.toast('Re-categorization started.', 'success'); this.pollRecat(res.job_id); },
      error: (e) => this.toast('Failed: ' + e.message, 'error'),
    });
  }

  private pollRecat(jobId: number): void {
    const poll = () => {
      this.api.getRecatStatus(jobId).subscribe({
        next: (s) => {
          if (s.status === 'running' || s.status === 'pending') {
            this.pollTimer = setTimeout(poll, 2000);
          } else {
            this.toast('Re-categorization complete.', 'success');
            this.loadFiles();
          }
        },
      });
    };
    this.pollTimer = setTimeout(poll, 1000);
  }

  // ── Scan modal ────────────────────────────────────────────────

  openScanModal(): void {
    this.scanPath = '';
    this.scanInProgress = false;
    this.scanProgress = 0;
    this.scanProgressLabel = '';
    this.showScanModal = true;
  }

  closeScanModal(): void {
    if (!this.scanInProgress) this.showScanModal = false;
  }

  startScan(): void {
    if (!this.scanPath.trim()) { this.toast('Path is required.', 'error'); return; }
    this.scanInProgress = true;
    this.scanProgress = 0;
    this.scanProgressLabel = 'Starting…';
    this.api.startScan(this.scanPath.trim()).subscribe({
      next: (res) => this.pollScan(res.job_id),
      error: (e) => { this.scanInProgress = false; this.toast('Scan failed: ' + e.message, 'error'); },
    });
  }

  private pollScan(jobId: number): void {
    const poll = () => {
      this.api.getScanStatus(jobId).subscribe({
        next: (s) => {
          const found = s.files_found || 0;
          const ttl = s.files_total || 0;
          this.scanProgress = ttl > 0 ? Math.round((found / ttl) * 100) : 0;
          this.scanProgressLabel = `${found.toLocaleString()} / ${ttl.toLocaleString()} files`;
          if (s.status === 'running' || s.status === 'pending') {
            this.pollTimer = setTimeout(poll, 1000);
          } else {
            this.scanInProgress = false;
            this.showScanModal = false;
            this.toast('Scan complete!', 'success');
            this.loadFiles();
            this.loadDisks();
          }
        },
        error: () => { this.scanInProgress = false; this.showScanModal = false; },
      });
    };
    this.pollTimer = setTimeout(poll, 1000);
  }

  // ── Rescan All ────────────────────────────────────────────────

  runRescanAll(): void {
    if (!confirm('This will wipe the database and rescan all disks. Continue?')) return;
    this.showRescanModal = true;
    this.rescanProgress = 0;
    this.rescanLabel = 'Starting rescan…';
    this.rescanDone = false;
    this.api.rescanAll().subscribe({
      next: (res) => this.pollRescan(res.job_id),
      error: (e) => { this.showRescanModal = false; this.toast('Rescan failed: ' + e.message, 'error'); },
    });
  }

  private pollRescan(jobId: number): void {
    const poll = () => {
      this.api.getScanStatus(jobId).subscribe({
        next: (s) => {
          const found = s.files_found || 0;
          const ttl = s.files_total || 0;
          this.rescanProgress = ttl > 0 ? Math.round((found / ttl) * 100) : 0;
          this.rescanLabel = `${found.toLocaleString()} / ${ttl > 0 ? ttl.toLocaleString() : '?'} files`;
          if (s.status === 'running' || s.status === 'pending') {
            this.pollTimer = setTimeout(poll, 1500);
          } else {
            this.rescanDone = true;
            this.rescanLabel = 'Done!';
            this.loadFiles();
            this.loadDisks();
          }
        },
      });
    };
    this.pollTimer = setTimeout(poll, 1000);
  }

  // ── File detail modal ─────────────────────────────────────────

  openFileDetail(id: number): void {
    this.api.getFile(id).subscribe({
      next: (f) => { this.selectedFile = { ...f }; this.showFileModal = true; },
      error: (e) => this.toast('Failed to load file: ' + e.message, 'error'),
    });
  }

  closeFileModal(): void { this.showFileModal = false; this.selectedFile = null; }

  saveFileDetail(): void {
    if (!this.selectedFile) return;
    const { id, category, tags, description } = this.selectedFile;
    this.api.updateFile(id, { category, tags, description }).subscribe({
      next: () => { this.toast('File updated.', 'success'); this.closeFileModal(); this.loadFiles(); },
      error: (e) => this.toast(e.message, 'error'),
    });
  }

  renameSelectedFile(): void {
    if (!this.selectedFile) return;
    const n = prompt('New filename:', this.selectedFile.name);
    if (!n || n === this.selectedFile.name) return;
    this.api.renameFile(this.selectedFile.id, n).subscribe({
      next: () => { this.toast('File renamed.', 'success'); this.closeFileModal(); this.loadFiles(); },
      error: (e) => this.toast(e.message, 'error'),
    });
  }

  moveSelectedFile(): void {
    if (!this.selectedFile) return;
    const dest = prompt('Destination directory:');
    if (!dest) return;
    this.api.moveFile(this.selectedFile.id, dest).subscribe({
      next: () => { this.toast('File moved.', 'success'); this.closeFileModal(); this.loadFiles(); },
      error: (e) => this.toast(e.message, 'error'),
    });
  }

  deleteSelectedFile(): void {
    if (!this.selectedFile) return;
    this.confirmAction(`Delete "${this.selectedFile.name}"?`).then((ok) => {
      if (!ok) return;
      this.api.deleteFile(this.selectedFile!.id).subscribe({
        next: () => { this.toast('File deleted.', 'success'); this.closeFileModal(); this.loadFiles(); },
        error: (e) => this.toast(e.message, 'error'),
      });
    });
  }

  deleteFileById(id: number, name: string): void {
    this.confirmAction(`Delete "${name}"?`).then((ok) => {
      if (!ok) return;
      this.api.deleteFile(id).subscribe({
        next: () => { this.toast('File deleted.', 'success'); this.loadFiles(); },
        error: (e) => this.toast(e.message, 'error'),
      });
    });
  }

  // ── Groups ────────────────────────────────────────────────────

  refreshAllInProgress = false;
  refreshAllDone = 0;
  refreshAllTotal = 0;

  refreshAllIcons(): void {
    const list = [...this.groups];
    if (!list.length) return;
    this.refreshAllInProgress = true;
    this.refreshAllDone = 0;
    this.refreshAllTotal = list.length;

    const next = (idx: number) => {
      if (idx >= list.length) {
        this.refreshAllInProgress = false;
        this.toast(`Refreshed icons for ${list.length} groups.`, 'success');
        return;
      }
      const g = list[idx];
      this.api.refreshGroupIcon(g.id).subscribe({
        next: (res) => {
          const ts = Date.now();
          const update = (arr: any[]) => {
            const found = arr.find(x => x.id === g.id);
            if (found) { found.thumbnail_path = res.thumbnail_path; found._ts = ts; }
          };
          update(this.groups);
          update(this.categoryGroups);
          this.refreshAllDone++;
          next(idx + 1);
        },
        error: () => {
          this.refreshAllDone++;
          next(idx + 1);
        },
      });
    };
    next(0);
  }

  stopAndRefreshIcon(event: MouseEvent, id: number): void {
    event.stopPropagation();
    this.api.refreshGroupIcon(id).subscribe({
      next: (res) => {
        const ts = Date.now();
        // Update both groups and categoryGroups in-memory so img src re-fetches
        const update = (arr: any[]) => {
          const g = arr.find(x => x.id === id);
          if (g) { g.thumbnail_path = res.thumbnail_path; g._ts = ts; }
        };
        update(this.groups);
        update(this.categoryGroups);
        if (this.explorerGroup?.id === id) {
          this.explorerGroup.thumbnail_path = res.thumbnail_path;
          this.explorerGroup._ts = ts;
        }
        this.toast('Icon refreshed.', 'success');
      },
      error: (e) => this.toast('Refresh failed: ' + e.message, 'error'),
    });
  }

  stopAndOpenFolder(event: MouseEvent, path: string): void {
    event.stopPropagation();
    this.openFolderPath(path);
  }

  // ── Operations ────────────────────────────────────────────────

  openFolderPath(path: string): void {
    if (!path) return;
    this.api.openFolder(path).subscribe({
      error: (e) => this.toast('Failed to open folder: ' + e.message, 'error'),
    });
  }

  // ── Pagination ────────────────────────────────────────────────

  get currentPage(): number { return Math.floor(this.offset / this.limit) + 1; }
  get totalPages(): number  { return Math.max(1, Math.ceil(this.total / this.limit)); }

  prevPage(): void { if (this.offset > 0) { this.offset = Math.max(0, this.offset - this.limit); this.loadFiles(); } }
  nextPage(): void { if (this.offset + this.limit < this.total) { this.offset += this.limit; this.loadFiles(); } }

  // ── Confirm modal ─────────────────────────────────────────────

  private confirmAction(message: string, title = 'Confirm Delete', label = 'Delete'): Promise<boolean> {
    this.confirmMessage = message;
    this.confirmTitle = title;
    this.confirmLabel = label;
    this.showConfirmModal = true;
    return new Promise((resolve) => { this.confirmResolve = resolve; });
  }

  resolveConfirm(result: boolean): void {
    this.showConfirmModal = false;
    if (this.confirmResolve) { this.confirmResolve(result); this.confirmResolve = null; }
  }

  // ── Toast ─────────────────────────────────────────────────────

  toast(message: string, type = 'info', duration = 3500): void {
    const id = ++this.toastCounter;
    this.toasts.push({ id, message, type });
    setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id); }, duration);
  }

  // ── Dashboard computed ────────────────────────────────────────

  get maxCategoryCount(): number {
    if (!this.stats?.by_category?.length) return 1;
    return Math.max(...this.stats.by_category.map((c: any) => c.count));
  }

  get topExtensions(): any[] { return this.stats?.by_extension?.slice(0, 12) ?? []; }
  get maxExtCount(): number {
    if (!this.topExtensions.length) return 1;
    return Math.max(...this.topExtensions.map((e: any) => e.count));
  }

  // ── Log helpers ───────────────────────────────────────────────

  logProgress(log: any): number {
    if (log.status === 'done' || log.status === 'error') return 100;
    const found = log.files_found || 0;
    const ttl = log.files_total || 0;
    return ttl > 0 ? Math.round((found / ttl) * 100) : 0;
  }

  logDuration(log: any): string {
    if (!log.started_at || !log.finished_at) return '';
    const ms = new Date(log.finished_at).getTime() - new Date(log.started_at).getTime();
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  }

  // ── Helpers ───────────────────────────────────────────────────

  humanSize(bytes: number): string {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
    return `${bytes.toFixed(1)} ${units[i]}`;
  }

  fileIcon(ext: string): string {
    const m: Record<string, string> = {
      mp4: '🎬', mkv: '🎬', avi: '🎬', mov: '🎬', wmv: '🎬', webm: '🎬',
      mp3: '🎵', flac: '🎵', wav: '🎵', aac: '🎵', ogg: '🎵',
      jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', webp: '🖼️', svg: '🖼️',
      pdf: '📄', doc: '📝', docx: '📝', xls: '📊', xlsx: '📊', txt: '📄', md: '📄',
      exe: '⚙️', msi: '⚙️', iso: '💿', zip: '📦', rar: '📦', '7z': '📦',
    };
    return m[(ext ?? '').replace('.', '').toLowerCase()] ?? '📄';
  }

  catIcon(cat: string): string {
    const m: Record<string, string> = {
      Games: '🎮', Movies: '🎬', Documents: '📄', Music: '🎵',
      Images: '🖼️', Software: '💿', Other: '📁',
    };
    return m[cat] ?? '📁';
  }
}
