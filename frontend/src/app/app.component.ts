import { ChangeDetectorRef, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from './services/api.service';

interface Toast { id: number; message: string; type: string; }

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
        <li class="nav-item" [class.active]="activeDiskPath === disk.path" (click)="selectDisk(disk)">
          <span class="nav-icon">💾</span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{disk.label || disk.path}}</span>
          <div class="disk-bar-wrap">
            <div class="disk-bar"><div class="disk-bar-fill" [style.width.%]="disk.percent"></div></div>
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
          <div class="group-tile" (click)="openCategoryGroup(g)" [title]="g.root_path">
            <div class="group-tile-thumb">
              @if (g.thumbnail_path) {
                <img class="group-tile-img" [src]="g.thumbnail_path" [alt]="g.name" />
              } @else {
                <div class="group-tile-icon">{{catIcon(g.category)}}</div>
              }
            </div>
            <div class="group-tile-name">{{g.name}}</div>
            <div class="group-tile-meta"><span [class]="'badge badge-' + g.category">{{g.category}}</span> · {{(g.file_count || 0) | number}} files</div>
            <button class="group-tile-open-btn" (click)="stopAndOpenFolder($event, g.root_path)">📂 Open</button>
          </div>
        }
        @empty { <p style="color:var(--text-muted)">No groups found for this category.</p> }
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
      <h2 class="view-title">Detected Groups</h2>
      <div class="file-grid">
        @for (g of groups; track g.id) {
          <div class="group-tile" (click)="openGroup(g)" [title]="g.root_path">
            <div class="group-tile-thumb">
              @if (g.thumbnail_path) {
                <img class="group-tile-img" [src]="g.thumbnail_path" [alt]="g.name" />
              } @else {
                <div class="group-tile-icon">{{catIcon(g.category)}}</div>
              }
              <button class="group-tile-refresh" title="Refresh icon" (click)="stopAndRefreshIcon($event, g.id)">↺</button>
            </div>
            <div class="group-tile-name">{{g.name}}</div>
            <div class="group-tile-meta"><span [class]="'badge badge-' + g.category">{{g.category}}</span> · {{(g.file_count || 0) | number}} files</div>
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

<!-- Confirm delete modal -->
<div class="modal-backdrop" [class.hidden]="!showConfirmModal">
  <div class="modal modal-sm">
    <h3>Confirm Delete</h3>
    <p>{{confirmMessage}}</p>
    <div class="modal-footer">
      <button class="btn" (click)="resolveConfirm(false)">Cancel</button>
      <button class="btn btn-danger" (click)="resolveConfirm(true)">Delete</button>
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

  openCategoryGroup(group: any): void {
    this.currentGroupId = group.id;
    this.currentView = 'files';
    this.offset = 0;
    this.loadFiles();
  }

  openGroup(group: any): void {
    this.currentGroupId = group.id;
    this.currentCategory = group.category;
    this.currentView = 'files';
    this.offset = 0;
    this.loadFiles();
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

  stopAndRefreshIcon(event: MouseEvent, id: number): void {
    event.stopPropagation();
    this.api.refreshGroupIcon(id).subscribe({
      next: () => this.toast('Icon refreshed.', 'success'),
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

  private confirmAction(message: string): Promise<boolean> {
    this.confirmMessage = message;
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
