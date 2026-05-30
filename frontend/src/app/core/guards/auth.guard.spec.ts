import { TestBed }       from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';
import { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';

import { authGuard, guestGuard } from './auth.guard';
import { AuthService }           from '../services/auth.service';

const mockRoute = {} as ActivatedRouteSnapshot;
const mockState = { url: '/dashboard' } as RouterStateSnapshot;

describe('authGuard', () => {
  let routerSpy: Partial<Router>;
  let authSpy: Partial<AuthService>;

  const setup = (authenticated: boolean) => {
    const fakeUrlTree = { toString: () => '/auth/login' } as UrlTree;
    authSpy  = { isAuthenticated: () => authenticated } as any;
    routerSpy = { createUrlTree: vi.fn(() => fakeUrlTree) } as any;

    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authSpy  },
        { provide: Router,      useValue: routerSpy },
      ],
    });
  };

  it('should return true when authenticated', () => {
    setup(true);
    const result = TestBed.runInInjectionContext(() =>
      authGuard(mockRoute, mockState)
    );
    expect(result).toBe(true);
  });

  it('should redirect to /auth/login when not authenticated', () => {
    setup(false);
    const result = TestBed.runInInjectionContext(() =>
      authGuard(mockRoute, mockState)
    ) as UrlTree;
    expect(routerSpy.createUrlTree).toHaveBeenCalledWith(['/auth/login']);
    expect(result.toString()).toBe('/auth/login');
  });
});

describe('guestGuard', () => {
  let routerSpy: Partial<Router>;
  let authSpy: Partial<AuthService>;

  const setup = (authenticated: boolean) => {
    const fakeUrlTree = { toString: () => '/dashboard' } as UrlTree;
    authSpy  = { isAuthenticated: () => authenticated } as any;
    routerSpy = { createUrlTree: vi.fn(() => fakeUrlTree) } as any;

    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authSpy  },
        { provide: Router,      useValue: routerSpy },
      ],
    });
  };

  it('should return true when NOT authenticated (guest)', () => {
    setup(false);
    const result = TestBed.runInInjectionContext(() =>
      guestGuard(mockRoute, mockState)
    );
    expect(result).toBe(true);
  });

  it('should redirect to /dashboard when already authenticated', () => {
    setup(true);
    const result = TestBed.runInInjectionContext(() =>
      guestGuard(mockRoute, mockState)
    ) as UrlTree;
    expect(routerSpy.createUrlTree).toHaveBeenCalledWith(['/dashboard']);
    expect(result.toString()).toBe('/dashboard');
  });
});

