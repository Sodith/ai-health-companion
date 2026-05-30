import { TestBed }                    from '@angular/core/testing';
import { ComponentFixture }           from '@angular/core/testing';
import { provideRouter, Router }      from '@angular/router';
import { provideAnimationsAsync }     from '@angular/platform-browser/animations/async';
import { provideHttpClient }          from '@angular/common/http';
import { of, throwError }             from 'rxjs';

import { LoginComponent }      from './login.component';
import { AuthService }         from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;
  let authSpy: Partial<AuthService>;
  let notifySpy: Partial<NotificationService>;
  let router: Router;

  beforeEach(async () => {
    authSpy   = { login: vi.fn() };
    notifySpy = { success: vi.fn(), error: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideRouter([]),
        provideAnimationsAsync(),
        provideHttpClient(),
        { provide: AuthService,         useValue: authSpy   },
        { provide: NotificationService, useValue: notifySpy },
      ],
    }).compileComponents();

    fixture   = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    router    = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should start with an invalid form', () => {
    expect(component.form.invalid).toBe(true);
  });

  it('should be invalid with a bad email', () => {
    component.form.setValue({ email: 'not-an-email', password: 'Pass@1234' });
    expect(component.form.invalid).toBe(true);
    expect(component.email.hasError('email')).toBe(true);
  });

  it('should be invalid with a short password', () => {
    component.form.setValue({ email: 'a@b.com', password: 'short' });
    expect(component.password.hasError('minlength')).toBe(true);
  });

  it('should be valid with correct credentials', () => {
    component.form.setValue({ email: 'test@test.com', password: 'Pass@1234' });
    expect(component.form.valid).toBe(true);
  });

  it('should not call AuthService when form is invalid', () => {
    component.onSubmit();
    expect(authSpy.login).not.toHaveBeenCalled();
  });

  it('should call AuthService.login and navigate on success', async () => {
    (authSpy.login as ReturnType<typeof vi.fn>).mockReturnValue(
      of({ success: true, data: { access_token: 'tok', token_type: 'bearer' },
           message: '', status_code: 200, error: null })
    );
    const navSpy = vi.spyOn(router, 'navigate');
    component.form.setValue({ email: 'a@b.com', password: 'Pass@1234' });
    component.onSubmit();
    await Promise.resolve();

    expect(authSpy.login).toHaveBeenCalledWith({ email: 'a@b.com', password: 'Pass@1234' });
    expect(notifySpy.success).toHaveBeenCalled();
    expect(navSpy).toHaveBeenCalledWith(['/dashboard']);
  });

  it('should show error notification on API failure', async () => {
    (authSpy.login as ReturnType<typeof vi.fn>).mockReturnValue(
      throwError(() => ({ error: { message: 'Invalid credentials' } }))
    );
    component.form.setValue({ email: 'a@b.com', password: 'Pass@1234' });
    component.onSubmit();
    await Promise.resolve();

    expect(notifySpy.error).toHaveBeenCalledWith('Invalid credentials');
    expect(component.loading()).toBe(false);
  });

  it('should toggle password visibility', () => {
    expect(component.hidePassword()).toBe(true);
    component.hidePassword.set(false);
    expect(component.hidePassword()).toBe(false);
  });
});
