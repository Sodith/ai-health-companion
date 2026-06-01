import { TestBed }                from '@angular/core/testing';
import { ComponentFixture }       from '@angular/core/testing';
import { provideRouter, Router }  from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient }      from '@angular/common/http';
import { signal }                 from '@angular/core';
import { of, throwError }         from 'rxjs';

import { DashboardComponent }   from './dashboard.component';
import { AuthService }          from '../../core/services/auth.service';
import { PrescriptionService }  from '../../core/services/prescription.service';
import { NotificationService }  from '../../core/services/notification.service';
import { PrescriptionListItem } from '../../shared/models/prescription.model';

const mockItems: PrescriptionListItem[] = [
  { id: 1, original_file_name: 'a.pdf', file_type: 'pdf', file_size: 1024, symptoms: null, upload_status: 'processed',  analysis_status: 'completed', created_at: '2026-01-03T10:00:00Z' },
  { id: 2, original_file_name: 'b.jpg', file_type: 'jpg', file_size: 2048, symptoms: null, upload_status: 'processing', analysis_status: 'processing', created_at: '2026-01-02T10:00:00Z' },
  { id: 3, original_file_name: 'c.png', file_type: 'png', file_size: 512,  symptoms: null, upload_status: 'failed',     analysis_status: 'failed',    created_at: '2026-01-01T10:00:00Z' },
];

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let authSpy: Partial<AuthService>;
  let serviceSpy: Partial<PrescriptionService>;
  let notifySpy: Partial<NotificationService>;
  let router: Router;

  beforeEach(async () => {
    const mockUser = { id: 'u1', email: 'jane@health.com', is_active: true, created_at: '' };
    authSpy    = { currentUser$: signal(mockUser) as any, logout: vi.fn() };
    serviceSpy = { getAll: vi.fn(() => of({ success: true, status_code: 200, message: 'OK', data: mockItems, error: null })) };
    notifySpy  = { error: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideRouter([]), provideAnimationsAsync(), provideHttpClient(),
        { provide: AuthService,         useValue: authSpy    },
        { provide: PrescriptionService, useValue: serviceSpy },
        { provide: NotificationService, useValue: notifySpy  },
      ],
    }).compileComponents();

    fixture   = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    router    = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => { expect(component).toBeTruthy(); });

  it('should load prescriptions on init', () => {
    expect(component.prescriptions().length).toBe(3);
    expect(component.loading()).toBe(false);
  });

  it('total() should equal number of prescriptions', () => { expect(component.total()).toBe(3); });
  it('processed() should count only processed', ()  => { expect(component.processed()).toBe(1); });
  it('processing() should count only processing', () => { expect(component.processing()).toBe(1); });
  it('failed() should count only failed', ()       => { expect(component.failed()).toBe(1); });

  it('recent() should return items sorted newest first', () => {
    expect(component.recent()[0].id).toBe(1);
  });

  it('userEmail() should return the current user email', () => {
    expect(component.userEmail()).toBe('jane@health.com');
  });

  it('userInitial() should return first letter uppercased', () => {
    expect(component.userInitial()).toBe('J');
  });

  it('greet() should return a greeting string', () => {
    expect(['Good morning', 'Good afternoon', 'Good evening']).toContain(component.greet());
  });

  it('fileIcon() should return picture_as_pdf for pdf', () => {
    expect(component.fileIcon('pdf')).toBe('picture_as_pdf');
  });

  it('fileIcon() should return image for jpg', () => {
    expect(component.fileIcon('jpg')).toBe('image');
  });

  it('statusIcon() should return check_circle for processed', () => {
    expect(component.statusIcon('processed')).toBe('check_circle');
  });

  it('formatSize() should show KB for small files', () => {
    expect(component.formatSize(512 * 1024)).toContain('KB');
  });

  it('viewAnalysis() should navigate to /analysis/:id', () => {
    const navSpy = vi.spyOn(router, 'navigate');
    component.viewAnalysis(7);
    expect(navSpy).toHaveBeenCalledWith(['/analysis', 7]);
  });

  it('logout() should call AuthService.logout', () => {
    component.logout();
    expect(authSpy.logout).toHaveBeenCalled();
  });

  it('should call notification.error when prescription load fails', async () => {
    // Override the spy to return an error, then re-trigger ngOnInit
    (serviceSpy.getAll as ReturnType<typeof vi.fn>).mockReturnValue(
      throwError(() => ({ error: { message: 'Server error' } }))
    );
    component.ngOnInit();
    await Promise.resolve();
    expect(notifySpy.error).toHaveBeenCalled();
  });
});


