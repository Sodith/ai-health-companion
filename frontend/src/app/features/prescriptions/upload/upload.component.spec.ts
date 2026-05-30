import { TestBed }                from '@angular/core/testing';
import { ComponentFixture }       from '@angular/core/testing';
import { provideRouter, Router }  from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient }      from '@angular/common/http';
import { of, throwError }         from 'rxjs';

import { UploadComponent }     from './upload.component';
import { PrescriptionService } from '../../../core/services/prescription.service';
import { NotificationService } from '../../../core/services/notification.service';

const makeFile = (name: string, type: string, size = 1024) =>
  new File([new Blob(['x'.repeat(size)], { type })], name, { type });

describe('UploadComponent', () => {
  let fixture: ComponentFixture<UploadComponent>;
  let component: UploadComponent;
  let serviceSpy: Partial<PrescriptionService>;
  let notifySpy: Partial<NotificationService>;
  let router: Router;

  beforeEach(async () => {
    serviceSpy = { upload: vi.fn() };
    notifySpy  = { success: vi.fn(), error: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [UploadComponent],
      providers: [
        provideRouter([]), provideAnimationsAsync(), provideHttpClient(),
        { provide: PrescriptionService, useValue: serviceSpy },
        { provide: NotificationService, useValue: notifySpy  },
      ],
    }).compileComponents();

    fixture   = TestBed.createComponent(UploadComponent);
    component = fixture.componentInstance;
    router    = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => { expect(component).toBeTruthy(); });

  it('should reject unsupported file type', () => {
    (component as any)._processFile(makeFile('doc.txt', 'text/plain'));
    expect(component.fileError()).toContain('Invalid file type');
    expect(component.selectedFile()).toBeNull();
  });

  it('should reject files over 10 MB', () => {
    (component as any)._processFile(makeFile('big.pdf', 'application/pdf', 11 * 1024 * 1024));
    expect(component.fileError()).toContain('too large');
  });

  it('should accept a valid PDF file', () => {
    (component as any)._processFile(makeFile('rx.pdf', 'application/pdf', 512 * 1024));
    expect(component.fileError()).toBeNull();
    expect(component.selectedFile()).toBeTruthy();
  });

  it('should accept a valid PNG file', () => {
    (component as any)._processFile(makeFile('rx.png', 'image/png', 200 * 1024));
    expect(component.selectedFile()).toBeTruthy();
  });

  it('should clear file on removeFile()', () => {
    (component as any)._processFile(makeFile('rx.pdf', 'application/pdf'));
    component.removeFile();
    expect(component.selectedFile()).toBeNull();
    expect(component.fileError()).toBeNull();
  });

  it('fileSizeDisplay should return KB for small files', () => {
    component.selectedFile.set(makeFile('rx.pdf', 'application/pdf', 512 * 1024));
    expect(component.fileSizeDisplay).toContain('KB');
  });

  it('fileSizeDisplay should return MB for large files', () => {
    component.selectedFile.set(makeFile('rx.pdf', 'application/pdf', 2 * 1024 * 1024));
    expect(component.fileSizeDisplay).toContain('MB');
  });

  it('fileIconName should return "picture_as_pdf" for pdf', () => {
    component.selectedFile.set(makeFile('rx.pdf', 'application/pdf'));
    expect(component.fileIconName).toBe('picture_as_pdf');
  });

  it('fileIconName should return "image" for png', () => {
    component.selectedFile.set(makeFile('rx.png', 'image/png'));
    expect(component.fileIconName).toBe('image');
  });

  it('should not submit without a file', () => {
    component.onSubmit();
    expect(serviceSpy.upload).not.toHaveBeenCalled();
    expect(component.fileError()).toBeTruthy();
  });

  it('should call service.upload and navigate on success', async () => {
    (serviceSpy.upload as ReturnType<typeof vi.fn>).mockReturnValue(
      of({ success: true, status_code: 201, message: 'OK',
           data: { upload_id: 1, filename: 'f.pdf', status: 'uploaded' }, error: null })
    );
    const navSpy = vi.spyOn(router, 'navigate');
    const file = makeFile('rx.pdf', 'application/pdf');
    component.selectedFile.set(file);
    component.onSubmit();
    await Promise.resolve();
    expect(serviceSpy.upload).toHaveBeenCalledWith(file, null);
    expect(notifySpy.success).toHaveBeenCalled();
    expect(navSpy).toHaveBeenCalledWith(['/prescriptions']);
  });

  it('should show error notification on upload failure', async () => {
    (serviceSpy.upload as ReturnType<typeof vi.fn>).mockReturnValue(
      throwError(() => ({ error: { message: 'File too large' } }))
    );
    component.selectedFile.set(makeFile('rx.pdf', 'application/pdf'));
    component.onSubmit();
    await Promise.resolve();
    expect(notifySpy.error).toHaveBeenCalledWith('File too large');
    expect(component.loading()).toBe(false);
  });
});
