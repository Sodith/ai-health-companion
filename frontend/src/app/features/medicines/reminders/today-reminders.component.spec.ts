import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { vi } from 'vitest';
import { TodayRemindersComponent } from './today-reminders.component';
import { ReminderService } from '../../../core/services/reminder.service';
import { NotificationService } from '../../../core/services/notification.service';
import { Reminder } from '../../../shared/models/reminder.model';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

const mockReminders: Reminder[] = [
  { id: 1, schedule_id: 1, medicine_name: 'Metformin', dosage: '500mg', reminder_time: new Date().toISOString(), status: 'pending', taken_at: null },
  { id: 2, schedule_id: 1, medicine_name: 'Metformin', dosage: '500mg', reminder_time: new Date().toISOString(), status: 'taken',   taken_at: new Date().toISOString() },
];

const mockApiResponse = (data: unknown) => ({
  success: true, status_code: 200, message: 'ok', data, error: null,
});

describe('TodayRemindersComponent', () => {
  let fixture: ComponentFixture<TodayRemindersComponent>;
  let component: TodayRemindersComponent;
  let reminderSvc: { getTodayReminders: ReturnType<typeof vi.fn>; markTaken: ReturnType<typeof vi.fn>; markSkipped: ReturnType<typeof vi.fn> };
  let notifSvc: { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    reminderSvc = {
      getTodayReminders: vi.fn(() => of(mockApiResponse(mockReminders))),
      markTaken:         vi.fn(),
      markSkipped:       vi.fn(),
    };
    notifSvc = { success: vi.fn(), error: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [TodayRemindersComponent],
      providers: [
        provideRouter([]),
        provideAnimationsAsync(),
        { provide: ReminderService,    useValue: reminderSvc },
        { provide: NotificationService, useValue: notifSvc },
      ],
    }).compileComponents();

    fixture   = TestBed.createComponent(TodayRemindersComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());

  it('should load reminders on init', () => {
    expect(reminderSvc.getTodayReminders).toHaveBeenCalledOnce();
    expect(component.reminders().length).toBe(2);
  });

  it('should compute pendingCount correctly', () => {
    expect(component.pendingCount()).toBe(1);
  });

  it('should compute takenCount correctly', () => {
    expect(component.takenCount()).toBe(1);
  });

  it('should filter by status', () => {
    component.statusFilter.set('pending');
    expect(component.filtered().length).toBe(1);
    expect(component.filtered()[0].status).toBe('pending');
  });

  it('should show all when filter is empty', () => {
    component.statusFilter.set('');
    expect(component.filtered().length).toBe(2);
  });

  it('should mark reminder as taken', () => {
    const updated = { ...mockReminders[0], status: 'taken' as const, taken_at: new Date().toISOString() };
    reminderSvc.markTaken.mockReturnValue(of(mockApiResponse(updated)));
    component.markTaken(mockReminders[0]);
    expect(reminderSvc.markTaken).toHaveBeenCalledWith(1);
    expect(notifSvc.success).toHaveBeenCalled();
  });

  it('should call error notification when markTaken fails', () => {
    reminderSvc.markTaken.mockReturnValue(throwError(() => new Error('fail')));
    component.markTaken(mockReminders[0]);
    expect(notifSvc.error).toHaveBeenCalled();
  });

  it('should mark reminder as skipped', () => {
    const updated = { ...mockReminders[0], status: 'skipped' as const, taken_at: new Date().toISOString() };
    reminderSvc.markSkipped.mockReturnValue(of(mockApiResponse(updated)));
    component.markSkipped(mockReminders[0]);
    expect(reminderSvc.markSkipped).toHaveBeenCalledWith(1);
  });

  it('should set error signal when load fails', () => {
    reminderSvc.getTodayReminders.mockReturnValue(throwError(() => new Error('fail')));
    component.load();
    expect(component.error()).toBeTruthy();
  });

  it('statusIcon returns correct icons', () => {
    expect(component.statusIcon('taken')).toBe('check_circle');
    expect(component.statusIcon('skipped')).toBe('cancel');
    expect(component.statusIcon('pending')).toBe('alarm');
  });
});



