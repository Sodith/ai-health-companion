import { TestBed }                from '@angular/core/testing';
import { ComponentFixture }       from '@angular/core/testing';
import { provideRouter, Router }  from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient }      from '@angular/common/http';
import { of, throwError }         from 'rxjs';

import { SignupComponent }     from './signup.component';
import { AuthService }         from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

const VALID_PW = 'Strong@1234';

describe('SignupComponent', () => {
  let fixture: ComponentFixture<SignupComponent>;
  let component: SignupComponent;
  let authSpy: Partial<AuthService>;
  let notifySpy: Partial<NotificationService>;
  let router: Router;

  beforeEach(async () => {
    authSpy   = { signup: vi.fn() };
    notifySpy = { success: vi.fn(), error: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [SignupComponent],
      providers: [
        provideRouter([]), provideAnimationsAsync(), provideHttpClient(),
        { provide: AuthService,         useValue: authSpy   },
        { provide: NotificationService, useValue: notifySpy },
      ],
    }).compileComponents();

    fixture   = TestBed.createComponent(SignupComponent);
    component = fixture.componentInstance;
    router    = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => { expect(component).toBeTruthy(); });

  it('should be invalid with weak password (no special char)', () => {
    component.form.setValue({ email: 'a@b.com', password: 'Weakpass1', confirmPassword: 'Weakpass1' });
    expect(component.password.hasError('pattern')).toBe(true);
  });

  it('should be invalid when passwords do not match', () => {
    component.form.setValue({ email: 'a@b.com', password: VALID_PW, confirmPassword: 'Different@1' });
    expect(component.form.hasError('passwordMismatch')).toBe(true);
  });

  it('should be valid with matching strong passwords', () => {
    component.form.setValue({ email: 'a@b.com', password: VALID_PW, confirmPassword: VALID_PW });
    expect(component.form.valid).toBe(true);
  });

  it('should return "Weak" for single-type password', () => {
    component.password.setValue('aaaaaaaa');
    expect(component.passwordStrengthHint).toBe('Weak');
  });

  it('should return "Strong" for fully complex password', () => {
    component.password.setValue(VALID_PW);
    expect(component.passwordStrengthHint).toBe('Strong');
  });

  it('should not submit when form is invalid', () => {
    component.onSubmit();
    expect(authSpy.signup).not.toHaveBeenCalled();
  });

  it('should call AuthService.signup and navigate on success', async () => {
    (authSpy.signup as ReturnType<typeof vi.fn>).mockReturnValue(
      of({ success: true, status_code: 201, message: 'Created.',
           data: { user: { id: '1', email: 'a@b.com', is_active: true, created_at: '' },
                   access_token: 'tok', token_type: 'bearer' }, error: null })
    );
    const navSpy = vi.spyOn(router, 'navigate');
    component.form.setValue({ email: 'a@b.com', password: VALID_PW, confirmPassword: VALID_PW });
    component.onSubmit();
    await Promise.resolve();
    expect(authSpy.signup).toHaveBeenCalledWith({ email: 'a@b.com', password: VALID_PW });
    expect(notifySpy.success).toHaveBeenCalled();
    expect(navSpy).toHaveBeenCalledWith(['/dashboard']);
  });

  it('should show error notification on API failure', async () => {
    (authSpy.signup as ReturnType<typeof vi.fn>).mockReturnValue(
      throwError(() => ({ error: { message: 'Email already exists' } }))
    );
    component.form.setValue({ email: 'a@b.com', password: VALID_PW, confirmPassword: VALID_PW });
    component.onSubmit();
    await Promise.resolve();
    expect(notifySpy.error).toHaveBeenCalledWith('Email already exists');
    expect(component.loading()).toBe(false);
  });
});
