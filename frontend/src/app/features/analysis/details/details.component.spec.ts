import { TestBed }                from '@angular/core/testing';
import { ComponentFixture }       from '@angular/core/testing';
import { provideRouter }          from '@angular/router';
import { ActivatedRoute }         from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient }      from '@angular/common/http';
import { of, throwError }         from 'rxjs';
import { DetailsComponent }    from './details.component';
import { AnalysisService }     from '../../../core/services/analysis.service';
import { NotificationService } from '../../../core/services/notification.service';
import { Analysis }            from '../../../shared/models/analysis.model';
const mockAnalysis: Analysis = {
  analysis_id: 10, prescription_id: 1, analysis_status: 'completed',
  disease_detected: 'Hypertension',
  doctor_advice: ['Reduce salt', 'Avoid stress'],
  lifestyle_changes: ['Exercise 30 min daily'],
  medicines: [{ id: 1, medicine_name: 'Amlodipine', dosage: '5mg', frequency: 'Once daily', duration: '30 days', notes: null, created_at: '', updated_at: '' }],
  disclaimer: 'AI is not a substitute for medical advice.',
  created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
};
const mockResponse = { success: true, status_code: 201, message: 'OK', data: mockAnalysis, error: null };
describe('DetailsComponent', () => {
  let fixture: ComponentFixture<DetailsComponent>;
  let component: DetailsComponent;
  let serviceSpy: Partial<AnalysisService>;
  let notifySpy: Partial<NotificationService>;
  const setup = (triggerFn: () => any) => {
    serviceSpy = { trigger: vi.fn(triggerFn), getByPrescriptionId: vi.fn(() => of(mockResponse)) };
    notifySpy  = { error: vi.fn() };
  };
  const build = async () => {
    await TestBed.configureTestingModule({
      imports: [DetailsComponent],
      providers: [
        provideRouter([]), provideAnimationsAsync(), provideHttpClient(),
        { provide: ActivatedRoute,      useValue: { snapshot: { paramMap: { get: () => '1' } } } },
        { provide: AnalysisService,     useValue: serviceSpy },
        { provide: NotificationService, useValue: notifySpy  },
      ],
    }).compileComponents();
    fixture   = TestBed.createComponent(DetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await Promise.resolve();
  };
  it('should create', async () => { setup(() => of(mockResponse)); await build(); expect(component).toBeTruthy(); });
  it('should set prescriptionId from route param', async () => { setup(() => of(mockResponse)); await build(); expect(component.prescriptionId()).toBe(1); });
  it('should load analysis on init via trigger()', async () => {
    setup(() => of(mockResponse)); await build();
    expect(serviceSpy.trigger).toHaveBeenCalledWith(1);
    expect(component.analysis()?.disease_detected).toBe('Hypertension');
    expect(component.loading()).toBe(false);
  });
  it('should fall back to getByPrescriptionId on 409', async () => {
    setup(() => throwError(() => ({ status: 409 }))); await build();
    await Promise.resolve();
    expect(serviceSpy.getByPrescriptionId).toHaveBeenCalledWith(1);
    expect(component.analysis()).toBeTruthy();
  });
  it('should show error notification on non-409 failure', async () => {
    setup(() => throwError(() => ({ status: 500, error: { message: 'Server error' } }))); await build();
    expect(notifySpy.error).toHaveBeenCalled();
    expect(component.analysis()).toBeNull();
  });
  it('statusIcon should return check_circle for completed', async () => { setup(() => of(mockResponse)); await build(); expect(component.statusIcon('completed')).toBe('check_circle'); });
  it('statusIcon should return error for failed', async () => { setup(() => of(mockResponse)); await build(); expect(component.statusIcon('failed')).toBe('error'); });
  it('statusClass should return "status-completed" for completed', async () => { setup(() => of(mockResponse)); await build(); expect(component.statusClass('completed')).toBe('status-completed'); });
  it('retry() should clear analysis and re-trigger', async () => {
    setup(() => of(mockResponse)); await build();
    component.retry();
    await Promise.resolve();
    expect(serviceSpy.trigger).toHaveBeenCalledTimes(2);
  });
});
