import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DatePipe, TitleCasePipe } from '@angular/common';

import { MatCardModule }            from '@angular/material/card';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatChipsModule }           from '@angular/material/chips';
import { MatDividerModule }         from '@angular/material/divider';
import { MatListModule }            from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule }         from '@angular/material/tooltip';
import { MatExpansionModule }       from '@angular/material/expansion';

import { AnalysisService }             from '../../../core/services/analysis.service';
import { NotificationService }         from '../../../core/services/notification.service';
import { SpinnerComponent }            from '../../../shared/components/spinner/spinner.component';
import { MedicalDisclaimerComponent }  from '../../../shared/components/medical-disclaimer/medical-disclaimer.component';
import { Analysis }                    from '../../../shared/models/analysis.model';

@Component({
  selector: 'app-details',
  standalone: true,
  imports: [
    RouterLink,
    DatePipe,
    TitleCasePipe,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatDividerModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatExpansionModule,
    SpinnerComponent,
    MedicalDisclaimerComponent,
  ],
  templateUrl: './details.component.html',
  styleUrl:    './details.component.scss',
})
export class DetailsComponent implements OnInit {
  private readonly route        = inject(ActivatedRoute);
  private readonly service      = inject(AnalysisService);
  private readonly notification = inject(NotificationService);

  loading           = signal(true);
  triggering        = signal(false);
  analysis          = signal<Analysis | null>(null);
  prescriptionId    = signal<number>(0);

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.prescriptionId.set(id);
    this.triggerAndLoad(id);
  }

  /** POST first (idempotent) — returns cached or freshly generated result */
  triggerAndLoad(id: number): void {
    this.triggering.set(true);
    this.loading.set(true);

    this.service.trigger(id).subscribe({
      next: res => {
        this.triggering.set(false);
        this.loading.set(false);
        if (res.success && res.data) {
          this.analysis.set(res.data);
        } else {
          this.notification.error(res.message || 'Analysis unavailable.');
        }
      },
      error: err => {
        this.triggering.set(false);
        this.loading.set(false);
        // 409 = still processing, fall back to GET
        if (err?.status === 409) {
          this.fetchExisting(id);
        } else {
          const msg = err?.error?.message || err?.error?.detail || 'Failed to load analysis.';
          this.notification.error(msg);
        }
      },
    });
  }

  /** GET — retrieve whatever is stored (no Gemini call) */
  fetchExisting(id: number): void {
    this.loading.set(true);
    this.service.getByPrescriptionId(id).subscribe({
      next: res => {
        this.loading.set(false);
        if (res.success && res.data) {
          this.analysis.set(res.data);
        } else {
          this.notification.error(res.message || 'Analysis not found.');
        }
      },
      error: err => {
        this.loading.set(false);
        const msg = err?.error?.message || 'Failed to retrieve analysis.';
        this.notification.error(msg);
      },
    });
  }

  retry(): void {
    this.analysis.set(null);
    this.triggerAndLoad(this.prescriptionId());
  }

  // ── Status helpers ───────────────────────────────────────────────────────
  statusIcon(status: string): string {
    const map: Record<string, string> = {
      completed:  'check_circle',
      processing: 'hourglass_top',
      pending:    'schedule',
      failed:     'error',
    };
    return map[status] ?? 'help_outline';
  }

  statusClass(status: string): string {
    return `status-${status}`;
  }
}


