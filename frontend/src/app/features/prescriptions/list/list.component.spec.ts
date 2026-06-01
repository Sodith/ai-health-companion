import { TestBed }                from '@angular/core/testing';
import { ComponentFixture }       from '@angular/core/testing';
import { provideRouter, Router }  from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient }      from '@angular/common/http';
import { of, throwError }         from 'rxjs';
import { ListComponent }        from './list.component';
import { PrescriptionService }  from '../../../core/services/prescription.service';
import { NotificationService }  from '../../../core/services/notification.service';
import { PrescriptionListItem } from '../../../shared/models/prescription.model';
const mockItems: PrescriptionListItem[] = [
  { id: 1, original_file_name: 'a.pdf', file_type: 'pdf', file_size: 1024, symptoms: 'cough', upload_status: 'processed',  analysis_status: 'completed', created_at: new Date().toISOString() },
  { id: 2, original_file_name: 'b.jpg', file_type: 'jpg', file_size: 2048, symptoms: null,    upload_status: 'processing', analysis_status: null,        created_at: new Date().toISOString() },
  { id: 3, original_file_name: 'c.png', file_type: 'png', file_size: 512,  symptoms: null,    upload_status: 'failed',     analysis_status: 'failed',    created_at: new Date().toISOString() },
];
describe('ListComponent', () => {
  let fixture: ComponentFixture<ListComponent>;
  let component: ListComponent;
  let serviceSpy: Partial<PrescriptionService>;
  let notifySpy: Partial<NotificationService>;
  let router: Router;
  beforeEach(async () => {
    serviceSpy = { getAll: vi.fn(() => of({ success: true, status_code: 200, message: 'OK', data: mockItems, error: null })) };
    notifySpy  = { error: vi.fn() };
    await TestBed.configureTestingModule({
      imports: [ListComponent],
      providers: [
        provideRouter([]), provideAnimationsAsync(), provideHttpClient(),
        { provide: PrescriptionService, useValue: serviceSpy },
        { provide: NotificationService, useValue: notifySpy  },
      ],
    }).compileComponents();
    fixture   = TestBed.createComponent(ListComponent);
    component = fixture.componentInstance;
    router    = TestBed.inject(Router);
    fixture.detectChanges();
  });
  it('should create', () => { expect(component).toBeTruthy(); });
  it('should load prescriptions on init', () => { expect(component.prescriptions().length).toBe(3); expect(component.loading()).toBe(false); });
  it('total() should equal number of prescriptions', () => { expect(component.total()).toBe(3); });
  it('processed() should count only status=processed', () => { expect(component.processed()).toBe(1); });
  it('pending() should count non-processed', () => { expect(component.pending()).toBe(2); });
  it('statusColor should return "accent" for processed', () => { expect(component.statusColor('processed')).toBe('accent'); });
  it('statusColor should return "warn" for failed', () => { expect(component.statusColor('failed')).toBe('warn'); });
  it('statusIcon should return check_circle for processed', () => { expect(component.statusIcon('processed')).toBe('check_circle'); });
  it('fileIcon should return picture_as_pdf for pdf', () => { expect(component.fileIcon('pdf')).toBe('picture_as_pdf'); });
  it('fileIcon should return image for png', () => { expect(component.fileIcon('png')).toBe('image'); });
  it('formatSize should display KB for small files', () => { expect(component.formatSize(512 * 1024)).toContain('KB'); });
  it('formatSize should display MB for large files', () => { expect(component.formatSize(2 * 1024 * 1024)).toContain('MB'); });
  it('viewAnalysis should navigate to /analysis/:id', () => {
    const navSpy = vi.spyOn(router, 'navigate');
    component.viewAnalysis(42);
    expect(navSpy).toHaveBeenCalledWith(['/analysis', 42]);
  });
  it('should show error notification when API fails', async () => {
    (serviceSpy.getAll as ReturnType<typeof vi.fn>).mockReturnValue(
      throwError(() => ({ error: { message: 'Server error' } }))
    );
    component.loadPrescriptions();
    await Promise.resolve();
    expect(notifySpy.error).toHaveBeenCalled();
    expect(component.loading()).toBe(false);
  });
});

