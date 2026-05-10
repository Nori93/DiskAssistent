import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit {
  settings: any = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getSettings().subscribe({
      next: (data) => (this.settings = data),
      error: (err) => console.error('Failed to load settings', err),
    });
  }

  save(event: Event): void {
    event.preventDefault();
    this.api.saveSettings(this.settings).subscribe({
      next: () => alert('Settings saved.'),
      error: (err) => console.error('Failed to save settings', err),
    });
  }
}

