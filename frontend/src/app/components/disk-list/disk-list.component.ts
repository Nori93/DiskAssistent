import { Component, OnInit } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-disk-list',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './disk-list.component.html',
  styleUrl: './disk-list.component.scss'
})
export class DiskListComponent implements OnInit {
  disks: any[] = [];
  scanMessage = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getDisks().subscribe({
      next: (data) => (this.disks = data),
      error: (err) => console.error('Failed to load disks', err),
    });
  }

  scan(path: string): void {
    this.api.startScan(path).subscribe({
      next: (res) => (this.scanMessage = `Scan started (job #${res.job_id})`),
      error: (err) => console.error('Failed to start scan', err),
    });
  }
}

