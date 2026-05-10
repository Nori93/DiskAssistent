import { Component, OnInit } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-file-browser',
  standalone: true,
  imports: [DecimalPipe, FormsModule],
  templateUrl: './file-browser.component.html',
  styleUrl: './file-browser.component.scss'
})
export class FileBrowserComponent implements OnInit {
  files: any[] = [];
  categories: string[] = [];
  category = '';
  search = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getCategories().subscribe({
      next: (cats) => (this.categories = cats),
    });
    this.load();
  }

  load(): void {
    const params: Record<string, any> = {};
    if (this.category) params['category'] = this.category;
    if (this.search) params['search'] = this.search;
    this.api.getFiles(params).subscribe({
      next: (res) => (this.files = res.files ?? res),
      error: (err) => console.error('Failed to load files', err),
    });
  }
}

