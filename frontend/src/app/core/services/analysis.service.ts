import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse } from '../../shared/interfaces/api-response.interface';
import { Analysis } from '../../shared/models/analysis.model';

@Injectable({ providedIn: 'root' })
export class AnalysisService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/analysis`;

  /**
   * Trigger AI analysis for a prescription.
   * Idempotent — returns cached result if already completed.
   */
  trigger(prescriptionId: number): Observable<ApiResponse<Analysis>> {
    return this.http.post<ApiResponse<Analysis>>(`${this.base}/${prescriptionId}`, {});
  }

  /** Retrieve stored analysis result for a prescription */
  getByPrescriptionId(prescriptionId: number): Observable<ApiResponse<Analysis>> {
    return this.http.get<ApiResponse<Analysis>>(`${this.base}/${prescriptionId}`);
  }
}

