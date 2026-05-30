import { Component, inject, signal, ElementRef, viewChild } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

import { MatCardModule }            from '@angular/material/card';
import { MatFormFieldModule }       from '@angular/material/form-field';
import { MatInputModule }           from '@angular/material/input';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatProgressBarModule }     from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule }         from '@angular/material/tooltip';
import { MatChipsModule }           from '@angular/material/chips';

import { PrescriptionService }  from '../../../core/services/prescription.service';
import { NotificationService }  from '../../../core/services/notification.service';
import { SpinnerComponent }     from '../../../shared/components/spinner/spinner.component';

// ── Constants (must match backend) ───────────────────────────────────────────
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_EXTENSIONS  = ['pdf', 'jpg', 'jpeg', 'png'];
const ALLOWED_MIME_TYPES  = ['application/pdf', 'image/jpeg', 'image/png'];

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatChipsModule,
    SpinnerComponent,
  ],
  templateUrl: './upload.component.html',
  styleUrl:    './upload.component.scss',
})
export class UploadComponent {
  private readonly fb           = inject(FormBuilder);
  private readonly service      = inject(PrescriptionService);
  private readonly notification = inject(NotificationService);
  private readonly router       = inject(Router);

  fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  // ── State ──────────────────────────────────────────────────────────────
  loading        = signal(false);
  selectedFile   = signal<File | null>(null);
  fileError      = signal<string | null>(null);
  dragOver       = signal(false);

  form = this.fb.group({
    symptoms: ['', [Validators.maxLength(2000)]],
  });

  get symptoms() { return this.form.get('symptoms')!; }

  // ── File helpers ────────────────────────────────────────────────────────
  get fileSizeDisplay(): string {
    const f = this.selectedFile();
    if (!f) return '';
    const kb = f.size / 1024;
    return kb >= 1024
      ? `${(kb / 1024).toFixed(1)} MB`
      : `${kb.toFixed(0)} KB`;
  }

  get fileIconName(): string {
    const ext = this.selectedFile()?.name.split('.').pop()?.toLowerCase() ?? '';
    return ext === 'pdf' ? 'picture_as_pdf' : 'image';
  }

  // ── Drag & Drop ─────────────────────────────────────────────────────────
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(true);
  }

  onDragLeave(): void {
    this.dragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
    const file = event.dataTransfer?.files[0];
    if (file) this._processFile(file);
  }

  // ── Browse button ────────────────────────────────────────────────────────
  openFilePicker(): void {
    this.fileInput()?.nativeElement.click();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file  = input.files?.[0];
    if (file) this._processFile(file);
    input.value = ''; // reset so same file can be re-selected
  }

  removeFile(): void {
    this.selectedFile.set(null);
    this.fileError.set(null);
  }

  // ── Validation ───────────────────────────────────────────────────────────
  private _processFile(file: File): void {
    this.fileError.set(null);

    // Extension check
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      this.fileError.set(`Invalid file type ".${ext}". Allowed: PDF, JPG, JPEG, PNG.`);
      return;
    }

    // MIME check
    if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
      this.fileError.set(`Unsupported MIME type "${file.type}".`);
      return;
    }

    // Size check
    if (file.size > MAX_FILE_SIZE_BYTES) {
      this.fileError.set(`File is too large (${(file.size / 1048576).toFixed(1)} MB). Maximum allowed: 10 MB.`);
      return;
    }

    this.selectedFile.set(file);
  }

  // ── Submit ───────────────────────────────────────────────────────────────
  onSubmit(): void {
    if (!this.selectedFile()) {
      this.fileError.set('Please select a prescription file.');
      return;
    }
    if (this.form.invalid || this.loading()) return;

    this.loading.set(true);
    const symptoms = this.symptoms.value?.trim() || null;

    this.service.upload(this.selectedFile()!, symptoms).subscribe({
      next: res => {
        this.loading.set(false);
        if (res.success && res.data) {
          this.notification.success('Prescription uploaded successfully!');
          this.router.navigate(['/prescriptions']);
        } else {
          this.notification.error(res.message || 'Upload failed.');
        }
      },
      error: err => {
        this.loading.set(false);
        const msg =
          err?.error?.message ||
          err?.error?.detail  ||
          'Upload failed. Please try again.';
        this.notification.error(msg);
      },
    });
  }
}


