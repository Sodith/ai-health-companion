import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse } from '../../shared/interfaces/api-response.interface';
import { HistoryDay, MedicineSchedule, Reminder } from '../../shared/models/reminder.model';

@Injectable({ providedIn: 'root' })
export class ReminderService {
  private readonly http = inject(HttpClient);
  private readonly medicineBase = `${environment.apiUrl}/medicines`;
  private readonly reminderBase = `${environment.apiUrl}/reminders`;

  // ── Medicine Schedules ───────────────────────────────────────────────────

  getMedicines(): Observable<ApiResponse<MedicineSchedule[]>> {
    return this.http.get<ApiResponse<MedicineSchedule[]>>(this.medicineBase);
  }

  getMedicineById(id: number): Observable<ApiResponse<MedicineSchedule>> {
    return this.http.get<ApiResponse<MedicineSchedule>>(`${this.medicineBase}/${id}`);
  }

  deactivateMedicine(id: number): Observable<ApiResponse<null>> {
    return this.http.patch<ApiResponse<null>>(`${this.medicineBase}/${id}/deactivate`, {});
  }

  getHistory(days = 7, medicineId?: number): Observable<ApiResponse<HistoryDay[]>> {
    let params = new HttpParams().set('days', days);
    if (medicineId) params = params.set('medicine_id', medicineId);
    return this.http.get<ApiResponse<HistoryDay[]>>(`${this.medicineBase}/history`, { params });
  }

  // ── Reminders ───────────────────────────────────────────────────────────

  getTodayReminders(): Observable<ApiResponse<Reminder[]>> {
    return this.http.get<ApiResponse<Reminder[]>>(`${this.reminderBase}/today`);
  }

  getReminders(date?: string, status?: string): Observable<ApiResponse<Reminder[]>> {
    let params = new HttpParams();
    if (date) params = params.set('date', date);
    if (status) params = params.set('status', status);
    return this.http.get<ApiResponse<Reminder[]>>(this.reminderBase, { params });
  }

  markTaken(reminderId: number): Observable<ApiResponse<Reminder>> {
    return this.http.patch<ApiResponse<Reminder>>(`${this.reminderBase}/${reminderId}/taken`, {});
  }

  markSkipped(reminderId: number): Observable<ApiResponse<Reminder>> {
    return this.http.patch<ApiResponse<Reminder>>(`${this.reminderBase}/${reminderId}/skipped`, {});
  }
}

