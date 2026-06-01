import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';

import { MatCardModule }            from '@angular/material/card';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatChipsModule }           from '@angular/material/chips';
import { MatToolbarModule }         from '@angular/material/toolbar';
import { MatDividerModule }         from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule }         from '@angular/material/tooltip';
import { MatListModule }            from '@angular/material/list';

import { ReminderService }    from '../../../core/services/reminder.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SpinnerComponent }   from '../../../shared/components/spinner/spinner.component';
import { MedicineSchedule, Reminder } from '../../../shared/models/reminder.model';

@Component({
  selector: 'app-medicine-detail',
  standalone: true,
  imports: [
    RouterLink, DatePipe,
    MatCardModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatToolbarModule, MatDividerModule, MatProgressSpinnerModule,
    MatTooltipModule, MatListModule,
    SpinnerComponent,
  ],
  template: `
    <app-spinner [loading]="loading()" />

    <mat-toolbar color="primary">
      <button mat-icon-button routerLink="/medicines" matTooltip="Back">
        <mat-icon>arrow_back</mat-icon>
      </button>
      <span class="toolbar-title">Medicine Details</span>
    </mat-toolbar>

    <div class="page-container">

      @if (error()) {
        <div class="error-banner">
          <mat-icon>error_outline</mat-icon>
          <span>{{ error() }}</span>
        </div>
      }

      @if (medicine()) {
        <mat-card class="detail-card">
          <mat-card-header>
            <mat-icon mat-card-avatar class="med-icon">medication</mat-icon>
            <mat-card-title>{{ medicine()!.medicine_name }}</mat-card-title>
            <mat-card-subtitle>{{ medicine()!.dosage ?? 'No dosage info' }}</mat-card-subtitle>
          </mat-card-header>

          <mat-card-content>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">Frequency</span>
                <span class="value">{{ medicine()!.frequency ?? 'Not specified' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Duration</span>
                <span class="value">{{ medicine()!.duration_days }} days</span>
              </div>
              <div class="detail-item">
                <span class="label">Start Date</span>
                <span class="value">{{ medicine()!.start_date | date:'mediumDate' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">End Date</span>
                <span class="value">{{ medicine()!.end_date | date:'mediumDate' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Status</span>
                <mat-chip [class]="'status-chip ' + (medicine()!.is_active ? 'active' : 'inactive')">
                  {{ medicine()!.is_active ? 'Active' : 'Inactive' }}
                </mat-chip>
              </div>
              @if (medicine()!.notes) {
                <div class="detail-item full-width">
                  <span class="label">Notes</span>
                  <span class="value">{{ medicine()!.notes }}</span>
                </div>
              }
            </div>

            <mat-divider class="section-divider" />

            <h3 class="section-title">
              <mat-icon>today</mat-icon> Today's Reminders
            </h3>

            @if (todayReminders().length === 0) {
              <p class="no-reminders">No reminders for today.</p>
            } @else {
              <mat-list>
                @for (r of todayReminders(); track r.id) {
                  <mat-list-item class="reminder-item">
                    <mat-icon matListItemIcon [class]="'status-icon ' + r.status">
                      {{ r.status === 'taken' ? 'check_circle' : r.status === 'skipped' ? 'cancel' : 'alarm' }}
                    </mat-icon>
                    <span matListItemTitle>{{ r.reminder_time | date:'shortTime' }}</span>
                    <span matListItemLine>
                      <mat-chip [class]="'reminder-chip ' + r.status">{{ r.status }}</mat-chip>
                    </span>
                  </mat-list-item>
                }
              </mat-list>
            }
          </mat-card-content>

          <mat-card-actions>
            <button mat-button routerLink="/medicines/reminders">
              <mat-icon>notifications</mat-icon> View All Reminders
            </button>
            @if (medicine()!.is_active) {
              <button mat-button color="warn" (click)="deactivate()">
                <mat-icon>stop_circle</mat-icon> Stop Schedule
              </button>
            }
          </mat-card-actions>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .spacer { flex: 1; }
    .toolbar-title { margin-left: 8px; font-size: 1.1rem; font-weight: 500; }
    .page-container { padding: 24px; max-width: 800px; margin: 0 auto; }
    .error-banner {
      display: flex; align-items: center; gap: 8px;
      background: #fdecea; color: #c62828; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px;
    }
    .detail-card { border-radius: 12px; }
    .med-icon { color: #1976d2; font-size: 36px; width: 36px; height: 36px; }
    .detail-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0;
      .full-width { grid-column: 1 / -1; }
    }
    .detail-item { display: flex; flex-direction: column; gap: 4px; }
    .label { font-size: 0.78rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .value { font-size: 0.95rem; color: #222; }
    .section-divider { margin: 20px 0; }
    .section-title { display: flex; align-items: center; gap: 8px; font-size: 1rem; color: #444; margin-bottom: 8px; mat-icon { font-size: 20px; } }
    .no-reminders { color: #888; font-style: italic; padding: 8px 0; }
    .reminder-item { border-radius: 8px; margin-bottom: 4px; }
    .status-icon { &.taken { color: #2e7d32; } &.skipped { color: #c62828; } &.pending { color: #f57c00; } }
    .status-chip { border-radius: 20px; font-size: 0.78rem; padding: 2px 10px;
      &.active { background: #e8f5e9; color: #2e7d32; } &.inactive { background: #fce4ec; color: #880e4f; } }
    .reminder-chip { border-radius: 12px; font-size: 0.72rem; padding: 2px 8px;
      &.pending  { background: #fff3e0; color: #e65100; }
      &.taken    { background: #e8f5e9; color: #1b5e20; }
      &.skipped  { background: #fce4ec; color: #880e4f; } }
  `],
})
export class MedicineDetailComponent implements OnInit {
  private readonly route        = inject(ActivatedRoute);
  private readonly reminderSvc  = inject(ReminderService);
  private readonly notification = inject(NotificationService);

  medicine       = signal<MedicineSchedule | null>(null);
  todayReminders = signal<Reminder[]>([]);
  loading        = signal(false);
  error          = signal<string | null>(null);

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.loading.set(true);
    this.reminderSvc.getMedicineById(id).subscribe({
      next: res => {
        this.medicine.set(res.data);
        this.todayReminders.set(res.data?.reminders_today ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load medicine details.');
        this.loading.set(false);
      },
    });
  }

  deactivate(): void {
    const med = this.medicine();
    if (!med || !confirm(`Stop reminders for ${med.medicine_name}?`)) return;
    this.reminderSvc.deactivateMedicine(med.id).subscribe({
      next: () => {
        this.notification.success('Schedule deactivated');
        this.medicine.update(m => m ? { ...m, is_active: false } : m);
      },
      error: () => this.notification.error('Failed to deactivate'),
    });
  }
}

