import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { DiskListComponent } from './components/disk-list/disk-list.component';
import { FileBrowserComponent } from './components/file-browser/file-browser.component';
import { GroupsComponent } from './components/groups/groups.component';
import { SettingsComponent } from './components/settings/settings.component';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'disks', component: DiskListComponent },
  { path: 'files', component: FileBrowserComponent },
  { path: 'groups', component: GroupsComponent },
  { path: 'settings', component: SettingsComponent },
];
