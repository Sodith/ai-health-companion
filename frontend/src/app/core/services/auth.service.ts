import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse } from '../../shared/interfaces/api-response.interface';
import { User } from '../../shared/models/user.model';

// ── Auth payload types ────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
}

export interface LoginData {
  access_token: string;
  token_type: string;
}

export interface SignupData {
  user: User;
  access_token: string;
  token_type: string;
}

// ── Token storage key ────────────────────────────────────────────────────────
const TOKEN_KEY = 'ahc_token';
const USER_KEY  = 'ahc_user';

// ── Service ──────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http   = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly base   = `${environment.apiUrl}/auth`;

  // ── Reactive state ──────────────────────────────────────────────────────
  private readonly _token        = signal<string | null>(this._loadToken());
  private readonly _currentUser  = signal<User | null>(this._loadUser());

  readonly token$       = this._token.asReadonly();
  readonly currentUser$ = this._currentUser.asReadonly();
  readonly isAuthenticated = computed(() => !!this._token());

  // ── Login ────────────────────────────────────────────────────────────────
  login(payload: LoginRequest): Observable<ApiResponse<LoginData>> {
    return this.http
      .post<ApiResponse<LoginData>>(`${this.base}/login`, payload)
      .pipe(
        tap(res => {
          if (res.success && res.data) {
            this._persist(res.data.access_token, null);
          }
        })
      );
  }

  // ── Signup ────────────────────────────────────────────────────────────────
  signup(payload: SignupRequest): Observable<ApiResponse<SignupData>> {
    return this.http
      .post<ApiResponse<SignupData>>(`${this.base}/signup`, payload)
      .pipe(
        tap(res => {
          if (res.success && res.data) {
            this._persist(res.data.access_token, res.data.user);
          }
        })
      );
  }

  // ── Logout ────────────────────────────────────────────────────────────────
  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    this._token.set(null);
    this._currentUser.set(null);
    this.router.navigate(['/auth/login']);
  }

  // ── Token accessor ────────────────────────────────────────────────────────
  getToken(): string | null {
    return this._token();
  }

  // ── Private helpers ──────────────────────────────────────────────────────
  private _persist(token: string, user: User | null): void {
    localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    this._token.set(token);
    this._currentUser.set(user);
  }

  private _loadToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  private _loadUser(): User | null {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  }
}

