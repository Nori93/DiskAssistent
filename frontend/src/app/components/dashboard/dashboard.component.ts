import { Component, OnInit } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  stats: any = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getStats().subscribe({
      next: (data) => (this.stats = data),
      error: (err) => console.error('Failed to load stats', err),
    });
  }
}

