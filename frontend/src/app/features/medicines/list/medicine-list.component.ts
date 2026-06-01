import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';

import { MatCardModule }            from '@angular/material/card';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatChipsModule }           from '@angular/material/chips';
import { MatToolbarModule }         from '@angular/material/toolbar';
import { MatDividerModule }         from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule }         from '@angular/material/tooltip';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';

import { ReminderService }    from '../../../core/services/reminder.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SpinnerComponent }   from '../../../shared/components/spinner/spinner.component';
import { MedicineSchedule }   from '../../../shared/models/reminder.model';

@Component({
  selector: 'app-medicine-list',
  standalone: true,
  imports: [
    RouterLink, DatePipe,
    MatCardModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatToolbarModule, MatDividerModule, MatProgressSpinnerModule,
    MatTooltipModule, MatDialogModule,
    SpinnerComponent,
  ],
  template: `
    <app-spinner [loading]="loading()" />

    <mat-toolbar color="primary">
      <button mat-icon-button routerLink="/dashboard" matTooltip="Back to Dashboard">
        <mat-icon>arrow_back</mat-icon>
      </button>
      <span class="toolbar-title">My Medicines</span>
      <span class="spacer"></span>
      <button mat-icon-button routerLink="/medicines/reminders" matTooltip="Today's Reminders">
        <mat-icon>notifications</mat-icon>
      </button>
      <button mat-icon-button routerLink="/medicines/history" matTooltip="Medication History">
        <mat-icon>history</mat-icon>
      </button>
    </mat-toolbar>

    <div class="page-container">

      @if (error()) {
        <div class="error-banner">
          <mat-icon>error_outline</mat-icon>
          <span>{{ error() }}</span>
          <button mat-button (click)="load()">Retry</button>
        </div>
      }

      @if (!loading() && medicines().length === 0 && !error()) {
        <div class="empty-state">
          <mat-icon class="empty-icon">medication</mat-icon>
          <h3>No medicines yet</h3>
          <p>Upload a prescription and run AI analysis to auto-generate medicine schedules.</p>
          <button mat-raised-button color="primary" routerLink="/prescriptions/upload">
            Upload Prescription
          </button>
        </div>
      }

      <div class="medicine-grid">
        @for (med of medicines(); track med.id) {
          <mat-card class="medicine-card" [class.inactive]="!med.is_active">
            <mat-card-header>
              <mat-icon mat-card-avatar class="med-icon">medication</mat-icon>
              <mat-card-title>{{ med.medicine_name }}</mat-card-title>
              <mat-card-subtitle>{{ med.dosage ?? 'No dosage info' }}</mat-card-subtitle>
            </mat-card-header>

            <mat-card-content>
              <div class="info-row">
                <mat-icon class="info-icon">schedule</mat-icon>
                <span>{{ med.frequency ?? 'Frequency not specified' }}</span>
              </div>
              <div class="info-row">
                <mat-icon class="info-icon">calendar_today</mat-icon>
                <span>{{ med.start_date | date:'mediumDate' }} – {{ med.end_date | date:'mediumDate' }}</span>
              </div>
              <div class="info-row">
                <mat-icon class="info-icon">timelapse</mat-icon>
                <span>{{ med.duration_days }} days</span>
              </div>
              @if (med.notes) {
                <div class="info-row notes">
                  <mat-icon class="info-icon">notes</mat-icon>
                  <span>{{ med.notes }}</span>
                </div>
              }
            </mat-card-content>

            <mat-card-footer class="card-footer">
              <mat-chip [class]="'status-chip ' + (med.is_active ? 'active' : 'inactive')">
                <mat-icon>{{ med.is_active ? 'check_circle' : 'cancel' }}</mat-icon>
                {{ med.is_active ? 'Active' : 'Inactive' }}
              </mat-chip>
              <div class="card-actions">
                <button mat-button color="primary" [routerLink]="['/medicines', med.id]">
                  Details
                </button>
                @if (med.is_active) {
                  <button mat-button color="warn"
                    (click)="deactivate(med)"
                    [disabled]="deactivating() === med.id">
                    Stop
                  </button>
                }
              </div>
            </mat-card-footer>
          </mat-card>
        }
      </div>
    </div>
  `,
  styles: [`
    .spacer { flex: 1; }
    .toolbar-title { margin-left: 8px; font-size: 1.1rem; font-weight: 500; }
    .page-container { padding: 24px; max-width: 1100px; margin: 0 auto; }

    .error-banner {
      display: flex; align-items: center; gap: 8px;
      background: #fdecea; color: #c62828; padding: 12px 16px;
      border-radius: 8px; margin-bottom: 20px;
    }

    .empty-state {
      text-align: center; padding: 80px 24px; color: #666;
      mat-icon { font-size: 64px; width: 64px; height: 64px; color: #bbb; display: block; margin: 0 auto 16px; }
      h3 { font-size: 1.3rem; margin-bottom: 8px; }
      p { margin-bottom: 24px; }
    }

    .medicine-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }

    .medicine-card {
      border-radius: 12px;
      transition: box-shadow 0.2s;
      &:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.12); }
      &.inactive { opacity: 0.65; }
    }

    .med-icon { color: #1976d2; font-size: 36px; width: 36px; height: 36px; }

    .info-row {
      display: flex; align-items: flex-start; gap: 8px;
      margin-bottom: 8px; font-size: 0.9rem; color: #444;
      &.notes { align-items: flex-start; }
    }
    .info-icon { font-size: 18px; width: 18px; height: 18px; color: #777; flex-shrink: 0; margin-top: 1px; }

    .card-footer {
      display: flex; align-items: center; justify-content: space-between;
      padding: 8px 16px 12px;
    }
    .card-actions { display: flex; gap: 4px; }

    .status-chip {
      font-size: 0.78rem; padding: 4px 8px;
      display: flex; align-items: center; gap: 4px;
      border-radius: 20px;
      mat-icon { font-size: 14px; width: 14px; height: 14px; }
      &.active { background: #e8f5e9; color: #2e7d32; }
      &.inactive { background: #fce4ec; color: #880e4f; }
    }
  `],
})
export class MedicineListComponent implements OnInit {
  private readonly reminderSvc  = inject(ReminderService);
  private readonly notification = inject(NotificationService);

  medicines  = signal<MedicineSchedule[]>([]);
  loading    = signal(false);
  deactivating = signal<number | null>(null);
  error      = signal<string | null>(null);

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.reminderSvc.getMedicines().subscribe({
      next: res => {
        this.medicines.set(res.data ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load medicines. Please try again.');
        this.loading.set(false);
      },
    });
  }

  deactivate(med: MedicineSchedule): void {
    if (!confirm(`Stop reminders for ${med.medicine_name}?`)) return;
    this.deactivating.set(med.id);
    this.reminderSvc.deactivateMedicine(med.id).subscribe({
      next: () => {
        this.notification.success(`${med.medicine_name} schedule deactivated`);
        this.load();
        this.deactivating.set(null);
      },
      error: () => {
        this.notification.error('Failed to deactivate schedule');
        this.deactivating.set(null);
      },
    });
  }
}





