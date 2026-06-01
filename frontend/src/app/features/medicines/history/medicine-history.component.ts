import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { MatCardModule }            from '@angular/material/card';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatChipsModule }           from '@angular/material/chips';
import { MatToolbarModule }         from '@angular/material/toolbar';
import { MatDividerModule }         from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule }          from '@angular/material/select';
import { MatFormFieldModule }       from '@angular/material/form-field';
import { MatTooltipModule }         from '@angular/material/tooltip';

import { ReminderService }    from '../../../core/services/reminder.service';
import { SpinnerComponent }   from '../../../shared/components/spinner/spinner.component';
import { HistoryDay }         from '../../../shared/models/reminder.model';

@Component({
  selector: 'app-medicine-history',
  standalone: true,
  imports: [
    RouterLink, DatePipe, FormsModule,
    MatCardModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatToolbarModule, MatDividerModule, MatProgressSpinnerModule,
    MatSelectModule, MatFormFieldModule, MatTooltipModule,
    SpinnerComponent,
  ],
  template: `
    <app-spinner [loading]="loading()" />

    <mat-toolbar color="primary">
      <button mat-icon-button routerLink="/medicines" matTooltip="Back">
        <mat-icon>arrow_back</mat-icon>
      </button>
      <span class="toolbar-title">Medication History</span>
      <span class="spacer"></span>
    </mat-toolbar>

    <div class="page-container">

      <!-- Filters -->
      <div class="filters-row">
        <mat-form-field appearance="outline" class="days-filter">
          <mat-label>Last N Days</mat-label>
          <mat-select [(ngModel)]="selectedDays" (ngModelChange)="load()">
            <mat-option [value]="7">7 days</mat-option>
            <mat-option [value]="14">14 days</mat-option>
            <mat-option [value]="30">30 days</mat-option>
            <mat-option [value]="90">90 days</mat-option>
          </mat-select>
        </mat-form-field>
      </div>

      @if (error()) {
        <div class="error-banner">
          <mat-icon>error_outline</mat-icon>
          <span>{{ error() }}</span>
          <button mat-button (click)="load()">Retry</button>
        </div>
      }

      @if (!loading() && history().length === 0 && !error()) {
        <div class="empty-state">
          <mat-icon class="empty-icon">history</mat-icon>
          <h3>No history yet</h3>
          <p>Start taking medicines and marking doses to build your history.</p>
        </div>
      }

      @for (day of history(); track day.date) {
        <div class="day-group">
          <div class="day-header">
            <mat-icon>calendar_today</mat-icon>
            <span>{{ day.date | date:'fullDate' }}</span>
            <div class="day-stats">
              <span class="stat taken">{{ takenOnDay(day) }} taken</span>
              <span class="stat skipped">{{ skippedOnDay(day) }} skipped</span>
            </div>
          </div>

          <div class="reminders-list">
            @for (r of day.reminders; track r.id) {
              <mat-card class="history-card status-{{ r.status }}">
                <div class="history-row">
                  <mat-icon class="status-icon {{ r.status }}">
                    {{ r.status === 'taken' ? 'check_circle' : 'cancel' }}
                  </mat-icon>
                  <div class="med-info">
                    <div class="med-name">{{ r.medicine_name }}</div>
                    <div class="med-meta">{{ r.dosage ?? '' }} · {{ r.reminder_time | date:'shortTime' }}</div>
                  </div>
                  <div class="right-side">
                    <mat-chip [class]="'status-chip ' + r.status">{{ r.status }}</mat-chip>
                    @if (r.taken_at) {
                      <div class="taken-at">at {{ r.taken_at | date:'shortTime' }}</div>
                    }
                  </div>
                </div>
              </mat-card>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .spacer { flex: 1; }
    .toolbar-title { margin-left: 8px; font-size: 1.1rem; font-weight: 500; }
    .page-container { padding: 24px; max-width: 800px; margin: 0 auto; }

    .filters-row { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
    .days-filter { width: 160px; }

    .error-banner {
      display: flex; align-items: center; gap: 8px;
      background: #fdecea; color: #c62828; padding: 12px 16px;
      border-radius: 8px; margin-bottom: 20px;
    }

    .empty-state {
      text-align: center; padding: 60px 24px; color: #666;
      .empty-icon { font-size: 64px; width: 64px; height: 64px; color: #bbb; display: block; margin: 0 auto 16px; }
      h3 { font-size: 1.2rem; margin-bottom: 8px; }
    }

    .day-group { margin-bottom: 28px; }

    .day-header {
      display: flex; align-items: center; gap: 8px;
      font-size: 0.95rem; font-weight: 600; color: #444;
      margin-bottom: 10px;
      mat-icon { font-size: 18px; color: #777; }
    }
    .day-stats { margin-left: auto; display: flex; gap: 10px; }
    .stat { font-size: 0.8rem; font-weight: 500; padding: 2px 10px; border-radius: 12px;
      &.taken   { background: #e8f5e9; color: #2e7d32; }
      &.skipped { background: #fce4ec; color: #880e4f; }
    }

    .reminders-list { display: flex; flex-direction: column; gap: 8px; }

    .history-card {
      border-radius: 10px; border-left: 4px solid #e0e0e0;
      &.status-taken   { border-left-color: #2e7d32; }
      &.status-skipped { border-left-color: #c62828; }
    }

    .history-row {
      display: flex; align-items: center; gap: 12px; padding: 10px 14px;
    }

    .status-icon {
      &.taken   { color: #2e7d32; }
      &.skipped { color: #c62828; }
    }

    .med-info { flex: 1; }
    .med-name { font-weight: 500; font-size: 0.9rem; }
    .med-meta { font-size: 0.8rem; color: #888; }

    .right-side { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
    .taken-at { font-size: 0.75rem; color: #aaa; }

    .status-chip {
      font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; text-transform: capitalize;
      &.taken   { background: #e8f5e9; color: #1b5e20; }
      &.skipped { background: #fce4ec; color: #880e4f; }
    }
  `],
})
export class MedicineHistoryComponent implements OnInit {
  private readonly reminderSvc = inject(ReminderService);

  history      = signal<HistoryDay[]>([]);
  loading      = signal(false);
  error        = signal<string | null>(null);
  selectedDays = 7;

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.reminderSvc.getHistory(this.selectedDays).subscribe({
      next: res => {
        this.history.set(res.data ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load history.');
        this.loading.set(false);
      },
    });
  }

  takenOnDay(day: HistoryDay): number {
    return day.reminders.filter(r => r.status === 'taken').length;
  }

  skippedOnDay(day: HistoryDay): number {
    return day.reminders.filter(r => r.status === 'skipped').length;
  }
}

