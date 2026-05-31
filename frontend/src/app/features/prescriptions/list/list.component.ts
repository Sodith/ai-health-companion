import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { DatePipe, TitleCasePipe } from '@angular/common';

import { MatCardModule }            from '@angular/material/card';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatTableModule }           from '@angular/material/table';
import { MatChipsModule }           from '@angular/material/chips';
import { MatTooltipModule }         from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatBadgeModule }           from '@angular/material/badge';
import { MatDividerModule }         from '@angular/material/divider';

import { PrescriptionService }  from '../../../core/services/prescription.service';
import { NotificationService }  from '../../../core/services/notification.service';
import { SpinnerComponent }     from '../../../shared/components/spinner/spinner.component';
import { PrescriptionListItem } from '../../../shared/models/prescription.model';

@Component({
  selector: 'app-list',
  standalone: true,
  imports: [
    RouterLink,
    DatePipe,
    TitleCasePipe,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatBadgeModule,
    MatDividerModule,
    SpinnerComponent,
  ],
  templateUrl: './list.component.html',
  styleUrl:    './list.component.scss',
})
export class ListComponent implements OnInit {
  private readonly service      = inject(PrescriptionService);
  private readonly notification = inject(NotificationService);
  private readonly router       = inject(Router);

  loading      = signal(true);
  prescriptions = signal<PrescriptionListItem[]>([]);

  displayedColumns = ['icon', 'name', 'type', 'size', 'status', 'date', 'actions'];

  total     = computed(() => this.prescriptions().length);
  processed = computed(() => this.prescriptions().filter(p => p.analysis_status === 'completed').length);
  pending   = computed(() => this.prescriptions().filter(p => p.analysis_status !== 'completed').length);

  ngOnInit(): void {
    this.loadPrescriptions();
  }

  loadPrescriptions(): void {
    this.loading.set(true);
    this.service.getAll().subscribe({
      next: res => {
        this.loading.set(false);
        if (res.success && res.data) {
          this.prescriptions.set(res.data);
        } else {
          this.notification.error(res.message || 'Failed to load prescriptions.');
        }
      },
      error: err => {
        this.loading.set(false);
        const msg = err?.error?.message || 'Failed to load prescriptions.';
        this.notification.error(msg);
      },
    });
  }

  viewAnalysis(id: number): void {
    this.router.navigate(['/analysis', id]);
  }

  // ── Helpers ─────────────────────────────────────────────────────────────

  statusColor(status: string): 'primary' | 'accent' | 'warn' {
    switch (status) {
      case 'processed':   return 'accent';
      case 'processing':  return 'primary';
      case 'failed':      return 'warn';
      default:            return 'primary';
    }
  }

  statusIcon(status: string): string {
    switch (status) {
      case 'processed':   return 'check_circle';
      case 'processing':  return 'hourglass_top';
      case 'failed':      return 'error';
      default:            return 'cloud_upload';
    }
  }

  fileIcon(type: string): string {
    return type === 'pdf' ? 'picture_as_pdf' : 'image';
  }

  formatSize(bytes: number): string {
    const kb = bytes / 1024;
    return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(0)} KB`;
  }
}


