import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { jwtInterceptor }      from './jwt.interceptor';
import { AuthService }         from '../services/auth.service';
import { NotificationService } from '../services/notification.service';

describe('jwtInterceptor', () => {
  let httpMock: HttpTestingController;
  let http: HttpClient;
  let authSpy: Partial<AuthService>;
  let notifySpy: Partial<NotificationService>;

  const setup = (token: string | null) => {
    authSpy   = { getToken: vi.fn(() => token), logout: vi.fn() };
    notifySpy = { error: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([jwtInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService,         useValue: authSpy   },
        { provide: NotificationService, useValue: notifySpy },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
    http     = TestBed.inject(HttpClient);
  };

  afterEach(() => httpMock.verify());

  it('should attach Authorization header when token exists', () => {
    setup('my-token');
    http.get('/api/test').subscribe();
    const req = httpMock.expectOne('/api/test');
    expect(req.request.headers.get('Authorization')).toBe('Bearer my-token');
    req.flush({});
  });

  it('should NOT attach Authorization header when no token', () => {
    setup(null);
    http.get('/api/test').subscribe();
    const req = httpMock.expectOne('/api/test');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('should call logout and show error on 401', () => {
    setup('expired-token');
    http.get('/api/secure').subscribe({ error: () => {} });
    httpMock.expectOne('/api/secure').flush({}, { status: 401, statusText: 'Unauthorised' });
    expect(authSpy.logout).toHaveBeenCalled();
    expect(notifySpy.error).toHaveBeenCalledWith(expect.stringContaining('Session expired'));
  });

  it('should show permission error on 403', () => {
    setup('valid-token');
    http.get('/api/admin').subscribe({ error: () => {} });
    httpMock.expectOne('/api/admin').flush({}, { status: 403, statusText: 'Forbidden' });
    expect(notifySpy.error).toHaveBeenCalledWith(expect.stringContaining('permission'));
    expect(authSpy.logout).not.toHaveBeenCalled();
  });

  it('should show network error on status 0', () => {
    setup('valid-token');
    http.get('/api/data').subscribe({ error: () => {} });
    httpMock.expectOne('/api/data').error(new ProgressEvent('error'));
    expect(notifySpy.error).toHaveBeenCalledWith(expect.stringContaining('server'));
  });
});
