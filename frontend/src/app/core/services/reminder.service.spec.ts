import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { ReminderService } from './reminder.service';
import { environment } from '../../../environments/environment';

describe('ReminderService', () => {
  let service: ReminderService;
  let http: HttpTestingController;

  const base = environment.apiUrl;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ReminderService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ReminderService);
    http    = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const ok = (data: unknown) => ({ success: true, status_code: 200, message: 'ok', data, error: null });

  it('GET /medicines returns schedule list', () => {
    service.getMedicines().subscribe(res => expect(res.data).toEqual([]));
    http.expectOne(`${base}/medicines`).flush(ok([]));
  });

  it('GET /medicines/:id returns single schedule', () => {
    service.getMedicineById(1).subscribe(res => expect(res.data).toBeTruthy());
    http.expectOne(`${base}/medicines/1`).flush(ok({ id: 1 }));
  });

  it('PATCH /medicines/:id/deactivate calls correct URL', () => {
    service.deactivateMedicine(5).subscribe();
    const req = http.expectOne(`${base}/medicines/5/deactivate`);
    expect(req.request.method).toBe('PATCH');
    req.flush(ok(null));
  });

  it('GET /medicines/history passes days param', () => {
    service.getHistory(14).subscribe();
    const req = http.expectOne(r => r.url.includes('/medicines/history'));
    expect(req.request.params.get('days')).toBe('14');
    req.flush(ok([]));
  });

  it('GET /reminders/today calls correct URL', () => {
    service.getTodayReminders().subscribe(res => expect(res.data).toEqual([]));
    http.expectOne(`${base}/reminders/today`).flush(ok([]));
  });

  it('GET /reminders without filters', () => {
    service.getReminders().subscribe();
    http.expectOne(`${base}/reminders`).flush(ok([]));
  });

  it('GET /reminders with status filter', () => {
    service.getReminders(undefined, 'pending').subscribe();
    const req = http.expectOne(r => r.url.includes('/reminders') && !r.url.includes('today'));
    expect(req.request.params.get('status')).toBe('pending');
    req.flush(ok([]));
  });

  it('PATCH /reminders/:id/taken calls correct URL', () => {
    service.markTaken(1).subscribe();
    const req = http.expectOne(`${base}/reminders/1/taken`);
    expect(req.request.method).toBe('PATCH');
    req.flush(ok({ id: 1, status: 'taken', taken_at: '' }));
  });

  it('PATCH /reminders/:id/skipped calls correct URL', () => {
    service.markSkipped(2).subscribe();
    const req = http.expectOne(`${base}/reminders/2/skipped`);
    expect(req.request.method).toBe('PATCH');
    req.flush(ok({ id: 2, status: 'skipped', taken_at: '' }));
  });
});


