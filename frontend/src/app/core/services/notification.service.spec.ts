import { TestBed }        from '@angular/core/testing';
import { MatSnackBar }    from '@angular/material/snack-bar';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { NotificationService } from './notification.service';

describe('NotificationService', () => {
  let service: NotificationService;
  let snackSpy: { open: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    snackSpy = { open: vi.fn() };

    TestBed.configureTestingModule({
      providers: [
        NotificationService,
        provideAnimationsAsync(),
        { provide: MatSnackBar, useValue: snackSpy },
      ],
    });
    service = TestBed.inject(NotificationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('success() should call snackBar.open with snack-success panel class', () => {
    service.success('Great!');
    expect(snackSpy.open).toHaveBeenCalledWith(
      'Great!', '✕',
      expect.objectContaining({ panelClass: ['snack-success'] })
    );
  });

  it('error() should call snackBar.open with snack-error panel class', () => {
    service.error('Oops!');
    expect(snackSpy.open).toHaveBeenCalledWith(
      'Oops!', '✕',
      expect.objectContaining({ panelClass: ['snack-error'] })
    );
  });

  it('info() should call snackBar.open with snack-info panel class', () => {
    service.info('FYI');
    expect(snackSpy.open).toHaveBeenCalledWith(
      'FYI', '✕',
      expect.objectContaining({ panelClass: ['snack-info'] })
    );
  });

  it('error() should use longer duration (6000ms)', () => {
    service.error('Bad');
    expect(snackSpy.open).toHaveBeenCalledWith(
      'Bad', '✕',
      expect.objectContaining({ duration: 6000 })
    );
  });
});

