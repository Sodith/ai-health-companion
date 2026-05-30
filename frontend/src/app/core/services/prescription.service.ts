import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse } from '../../shared/interfaces/api-response.interface';
import {
  PrescriptionDetail,
  PrescriptionListItem,
  PrescriptionUploadResponse,
} from '../../shared/models/prescription.model';

@Injectable({ providedIn: 'root' })
export class PrescriptionService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/prescriptions`;

  /**
   * Upload a prescription file with optional symptoms text.
   * Uses multipart/form-data — file field name must be "prescription_file".
   */
  upload(file: File, symptoms: string | null): Observable<ApiResponse<PrescriptionUploadResponse>> {
    const form = new FormData();
    form.append('prescription_file', file, file.name);
    if (symptoms?.trim()) {
      form.append('symptoms', symptoms.trim());
    }
    return this.http.post<ApiResponse<PrescriptionUploadResponse>>(`${this.base}/upload`, form);
  }

  /** List all prescriptions for the authenticated user */
  getAll(): Observable<ApiResponse<PrescriptionListItem[]>> {
    return this.http.get<ApiResponse<PrescriptionListItem[]>>(this.base);
  }

  /** Fetch a single prescription by ID */
  getById(id: number): Observable<ApiResponse<PrescriptionDetail>> {
    return this.http.get<ApiResponse<PrescriptionDetail>>(`${this.base}/${id}`);
  }
}

