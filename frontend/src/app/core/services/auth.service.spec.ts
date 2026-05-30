import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter }     from '@angular/router';
import { Component }         from '@angular/core';
import { AuthService }   from './auth.service';
import { environment }   from '../../../environments/environment';

@Component({ standalone: true, template: '' })
class StubComponent {}

const BASE = `${environment.apiUrl}/auth`;
const mockLoginResponse = { success: true, status_code: 200, message: 'Login successful.', data: { access_token: 'test-jwt-token', token_type: 'bearer' }, error: null };
const mockSignupResponse = { success: true, status_code: 201, message: 'Account created.', data: { user: { id: 'uuid-1', email: 'test@test.com', is_active: true, created_at: new Date().toISOString() }, access_token: 'signup-jwt-token', token_type: 'bearer' }, error: null };
describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [AuthService, provideHttpClient(), provideHttpClientTesting(),
      provideRouter([{ path: '**', component: StubComponent }])] });
    service  = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });
  afterEach(() => { httpMock.verify(); localStorage.clear(); });
  it('should be created', () => { expect(service).toBeTruthy(); });
  it('should start unauthenticated when localStorage is empty', () => {
    expect(service.isAuthenticated()).toBe(false);
    expect(service.getToken()).toBeNull();
    expect(service.currentUser$()).toBeNull();
  });
  it('should restore token from localStorage on init', () => {
    localStorage.setItem('ahc_token', 'persisted-token');
    const fresh = TestBed.runInInjectionContext(() => new AuthService());
    expect(fresh.isAuthenticated()).toBe(true);
    expect(fresh.getToken()).toBe('persisted-token');
  });
  it('should POST to /auth/login and store token on success', () => {
    let result: any;
    service.login({ email: 'test@test.com', password: 'Pass@1234' }).subscribe(r => (result = r));
    const req = httpMock.expectOne(`${BASE}/login`);
    expect(req.request.method).toBe('POST');
    req.flush(mockLoginResponse);
    expect(result.success).toBe(true);
    expect(service.getToken()).toBe('test-jwt-token');
    expect(service.isAuthenticated()).toBe(true);
    expect(localStorage.getItem('ahc_token')).toBe('test-jwt-token');
  });
  it('should POST to /auth/signup and store token + user on success', () => {
    let result: any;
    service.signup({ email: 'test@test.com', password: 'Pass@1234' }).subscribe(r => (result = r));
    const req = httpMock.expectOne(`${BASE}/signup`);
    expect(req.request.method).toBe('POST');
    req.flush(mockSignupResponse);
    expect(result.success).toBe(true);
    expect(service.getToken()).toBe('signup-jwt-token');
    expect(service.currentUser$()?.email).toBe('test@test.com');
  });
  it('should clear token and user on logout', () => {
    service.login({ email: 'a@b.com', password: 'P@ss1234' }).subscribe();
    httpMock.expectOne(`${BASE}/login`).flush(mockLoginResponse);
    service.logout();
    expect(service.isAuthenticated()).toBe(false);
    expect(service.getToken()).toBeNull();
    expect(localStorage.getItem('ahc_token')).toBeNull();
  });
});


