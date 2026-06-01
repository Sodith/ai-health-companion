import { Component, inject, signal, computed, OnInit } from '@angular/core';
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
import { MatButtonToggleModule }    from '@angular/material/button-toggle';
import { FormsModule }              from '@angular/forms';

import { ReminderService }    from '../../../core/services/reminder.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SpinnerComponent }   from '../../../shared/components/spinner/spinner.component';
import { Reminder }           from '../../../shared/models/reminder.model';

@Component({
  selector: 'app-today-reminders',
  standalone: true,
  imports: [
    RouterLink, DatePipe, FormsModule,
    MatCardModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatToolbarModule, MatDividerModule, MatProgressSpinnerModule,
    MatTooltipModule, MatButtonToggleModule,
    SpinnerComponent,
  ],
  template: `
    <app-spinner [loading]="loading()" />

    <mat-toolbar color="primary">
      <button mat-icon-button routerLink="/medicines" matTooltip="Back">
        <mat-icon>arrow_back</mat-icon>
      </button>
      <span class="toolbar-title">Today's Reminders</span>
      <span class="spacer"></span>
      <button mat-icon-button (click)="load()" matTooltip="Refresh">
        <mat-icon>refresh</mat-icon>
      </button>
    </mat-toolbar>

    <div class="page-container">

      <!-- Summary chips -->
      <div class="summary-row">
        <div class="summary-chip total">
          <mat-icon>notifications</mat-icon>
          <span>{{ reminders().length }} Total</span>
        </div>
        <div class="summary-chip pending">
          <mat-icon>alarm</mat-icon>
          <span>{{ pendingCount() }} Pending</span>
        </div>
        <div class="summary-chip taken">
          <mat-icon>check_circle</mat-icon>
          <span>{{ takenCount() }} Taken</span>
        </div>
        <div class="summary-chip skipped">
          <mat-icon>cancel</mat-icon>
          <span>{{ skippedCount() }} Skipped</span>
        </div>
      </div>

      <!-- Filter toggle -->
      <div class="filter-row">
        <mat-button-toggle-group [ngModel]="statusFilter()" (ngModelChange)="statusFilter.set($event)" aria-label="Filter">
          <mat-button-toggle value="">All</mat-button-toggle>
          <mat-button-toggle value="pending">Pending</mat-button-toggle>
          <mat-button-toggle value="taken">Taken</mat-button-toggle>
          <mat-button-toggle value="skipped">Skipped</mat-button-toggle>
        </mat-button-toggle-group>
      </div>

      @if (error()) {
        <div class="error-banner">
          <mat-icon>error_outline</mat-icon>
          <span>{{ error() }}</span>
          <button mat-button (click)="load()">Retry</button>
        </div>
      }

      @if (!loading() && filtered().length === 0 && !error()) {
        <div class="empty-state">
          <mat-icon class="empty-icon">{{ statusFilter() ? 'filter_list_off' : 'check_circle_outline' }}</mat-icon>
          <h3>{{ statusFilter() ? 'No ' + statusFilter() + ' reminders' : 'All clear for today!' }}</h3>
          <p>{{ statusFilter() ? 'Try a different filter.' : 'No active medicine schedules or all doses are done.' }}</p>
        </div>
      }

      <div class="reminders-list">
        @for (r of filtered(); track r.id) {
          <mat-card class="reminder-card" [class]="'status-' + r.status">
            <div class="reminder-row">
              <div class="time-block">
                <mat-icon class="time-icon">access_time</mat-icon>
                <span class="time-text">{{ r.reminder_time | date:'shortTime' }}</span>
              </div>

              <div class="med-info">
                <div class="med-name">{{ r.medicine_name }}</div>
                <div class="med-dosage">{{ r.dosage ?? '' }}</div>
              </div>

              <mat-chip [class]="'status-chip ' + r.status">
                <mat-icon>{{ statusIcon(r.status) }}</mat-icon>
                {{ r.status }}
              </mat-chip>

              @if (r.status === 'pending') {
                <div class="actions">
                  <button mat-icon-button color="primary"
                    matTooltip="Mark Taken"
                    [disabled]="actioning() === r.id"
                    (click)="markTaken(r)">
                    <mat-icon>check_circle</mat-icon>
                  </button>
                  <button mat-icon-button color="warn"
                    matTooltip="Mark Skipped"
                    [disabled]="actioning() === r.id"
                    (click)="markSkipped(r)">
                    <mat-icon>cancel</mat-icon>
                  </button>
                </div>
              } @else {
                <div class="taken-at">
                  @if (r.taken_at) {
                    {{ r.taken_at | date:'shortTime' }}
                  }
                </div>
              }
            </div>
          </mat-card>
        }
      </div>
    </div>
  `,
  styles: [`
    .spacer { flex: 1; }
    .toolbar-title { margin-left: 8px; font-size: 1.1rem; font-weight: 500; }
    .page-container { padding: 24px; max-width: 800px; margin: 0 auto; }

    .summary-row {
      display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px;
    }
    .summary-chip {
      display: flex; align-items: center; gap: 6px;
      padding: 8px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 500;
      mat-icon { font-size: 18px; width: 18px; height: 18px; }
      &.total   { background: #e3f2fd; color: #0d47a1; }
      &.pending { background: #fff3e0; color: #e65100; }
      &.taken   { background: #e8f5e9; color: #1b5e20; }
      &.skipped { background: #fce4ec; color: #880e4f; }
    }

    .filter-row { margin-bottom: 20px; }

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

    .reminders-list { display: flex; flex-direction: column; gap: 12px; }

    .reminder-card {
      border-radius: 12px; border-left: 4px solid #e0e0e0;
      &.status-pending { border-left-color: #f57c00; }
      &.status-taken   { border-left-color: #2e7d32; }
      &.status-skipped { border-left-color: #c62828; }
    }

    .reminder-row {
      display: flex; align-items: center; gap: 16px; padding: 12px 16px;
    }

    .time-block {
      display: flex; flex-direction: column; align-items: center;
      min-width: 56px;
      .time-icon { color: #777; font-size: 18px; }
      .time-text { font-size: 0.85rem; font-weight: 600; color: #333; }
    }

    .med-info { flex: 1; }
    .med-name { font-weight: 500; font-size: 0.95rem; }
    .med-dosage { font-size: 0.82rem; color: #777; }

    .status-chip {
      font-size: 0.75rem; padding: 2px 10px; border-radius: 20px;
      display: flex; align-items: center; gap: 4px; text-transform: capitalize;
      mat-icon { font-size: 14px; width: 14px; height: 14px; }
      &.pending { background: #fff3e0; color: #e65100; }
      &.taken   { background: #e8f5e9; color: #1b5e20; }
      &.skipped { background: #fce4ec; color: #880e4f; }
    }

    .actions { display: flex; }
    .taken-at { font-size: 0.78rem; color: #888; min-width: 60px; text-align: right; }
  `],
})
export class TodayRemindersComponent implements OnInit {
  private readonly reminderSvc  = inject(ReminderService);
  private readonly notification = inject(NotificationService);

  reminders    = signal<Reminder[]>([]);
  loading      = signal(false);
  actioning    = signal<number | null>(null);
  error        = signal<string | null>(null);
  statusFilter = signal('');

  pendingCount  = computed(() => this.reminders().filter(r => r.status === 'pending').length);
  takenCount    = computed(() => this.reminders().filter(r => r.status === 'taken').length);
  skippedCount  = computed(() => this.reminders().filter(r => r.status === 'skipped').length);

  filtered = computed(() =>
    this.statusFilter()
      ? this.reminders().filter(r => r.status === this.statusFilter())
      : this.reminders()
  );

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.reminderSvc.getTodayReminders().subscribe({
      next: res => {
        this.reminders.set(res.data ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load reminders.');
        this.loading.set(false);
      },
    });
  }

  statusIcon(status: string): string {
    return status === 'taken' ? 'check_circle' : status === 'skipped' ? 'cancel' : 'alarm';
  }

  markTaken(r: Reminder): void {
    this.actioning.set(r.id);
    this.reminderSvc.markTaken(r.id).subscribe({
      next: () => {
        this.notification.success(`${r.medicine_name} marked as taken`);
        this.reminders.update(list =>
          list.map(x => x.id === r.id ? { ...x, status: 'taken' as const } : x)
        );
        this.actioning.set(null);
      },
      error: () => {
        this.notification.error('Action failed');
        this.actioning.set(null);
      },
    });
  }

  markSkipped(r: Reminder): void {
    this.actioning.set(r.id);
    this.reminderSvc.markSkipped(r.id).subscribe({
      next: () => {
        this.notification.success(`${r.medicine_name} skipped`);
        this.reminders.update(list =>
          list.map(x => x.id === r.id ? { ...x, status: 'skipped' as const } : x)
        );
        this.actioning.set(null);
      },
      error: () => {
        this.notification.error('Action failed');
        this.actioning.set(null);
      },
    });
  }
}

