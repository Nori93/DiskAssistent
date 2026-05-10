import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-groups',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './groups.component.html',
  styleUrl: './groups.component.scss'
})
export class GroupsComponent implements OnInit {
  groups: any[] = [];
  categories: string[] = [];
  category = '';

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
    this.api.getGroups(params).subscribe({
      next: (res) => (this.groups = res.groups ?? res),
      error: (err) => console.error('Failed to load groups', err),
    });
  }
}

