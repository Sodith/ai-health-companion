import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { DatePipe }           from '@angular/common';

import { MatCardModule }            from '@angular/material/card';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatToolbarModule }         from '@angular/material/toolbar';
import { MatDividerModule }         from '@angular/material/divider';
import { MatChipsModule }           from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule }         from '@angular/material/tooltip';
import { MatMenuModule }            from '@angular/material/menu';

import { AuthService }          from '../../core/services/auth.service';
import { PrescriptionService }  from '../../core/services/prescription.service';
import { NotificationService }  from '../../core/services/notification.service';
import { SpinnerComponent }     from '../../shared/components/spinner/spinner.component';
import { PrescriptionListItem } from '../../shared/models/prescription.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    RouterLink,
    DatePipe,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatToolbarModule,
    MatDividerModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatMenuModule,
    SpinnerComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl:    './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  private readonly auth         = inject(AuthService);
  private readonly service      = inject(PrescriptionService);
  private readonly notification = inject(NotificationService);
  private readonly router       = inject(Router);

  // ── State ──────────────────────────────────────────────────────────────
  loading       = signal(true);
  prescriptions = signal<PrescriptionListItem[]>([]);

  // ── Auth ───────────────────────────────────────────────────────────────
  currentUser   = this.auth.currentUser$;
  userEmail     = computed(() => this.currentUser()?.email ?? '');
  userInitial   = computed(() => this.userEmail().charAt(0).toUpperCase());

  // ── Stats (computed from prescriptions signal) ─────────────────────────
  total      = computed(() => this.prescriptions().length);
  processed  = computed(() => this.prescriptions().filter(p => p.analysis_status === 'completed').length);
  processing = computed(() => this.prescriptions().filter(p => p.analysis_status === 'processing').length);
  failed     = computed(() => this.prescriptions().filter(p => p.analysis_status === 'failed').length);

  // ── Recent (latest 5) ──────────────────────────────────────────────────
  recent = computed(() =>
    [...this.prescriptions()]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5)
  );

  ngOnInit(): void {
    this.service.getAll().subscribe({
      next: res => {
        this.loading.set(false);
        if (res.success && res.data) this.prescriptions.set(res.data);
      },
      error: () => {
        this.loading.set(false);
        this.notification.error('Could not load prescription data.');
      },
    });
  }

  logout(): void {
    this.auth.logout();
  }

  viewAnalysis(id: number): void {
    this.router.navigate(['/analysis', id]);
  }

  // ── Helpers ─────────────────────────────────────────────────────────────
  statusIcon(status: string): string {
    const map: Record<string, string> = {
      processed: 'check_circle', processing: 'hourglass_top',
      uploaded: 'cloud_done', failed: 'error',
    };
    return map[status] ?? 'help_outline';
  }

  fileIcon(type: string): string {
    return type === 'pdf' ? 'picture_as_pdf' : 'image';
  }

  formatSize(bytes: number): string {
    const kb = bytes / 1024;
    return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(0)} KB`;
  }

  greet(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }
}


