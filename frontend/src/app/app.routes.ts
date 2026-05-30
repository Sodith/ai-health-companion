import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  // ── Default redirect ────────────────────────────────────────────────────
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },

  // ── Auth routes (public — redirect to dashboard if already logged in) ───
  {
    path: 'auth',
    canActivate: [guestGuard],
    children: [
      {
        path: 'login',
        loadComponent: () =>
          import('./features/auth/login/login.component').then(m => m.LoginComponent),
        title: 'Login — AI Health Companion',
      },
      {
        path: 'signup',
        loadComponent: () =>
          import('./features/auth/signup/signup.component').then(m => m.SignupComponent),
        title: 'Sign Up — AI Health Companion',
      },
      {
        path: '',
        redirectTo: 'login',
        pathMatch: 'full',
      },
    ],
  },

  // ── Protected routes (require valid JWT) ────────────────────────────────
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
    title: 'Dashboard — AI Health Companion',
  },
  {
    path: 'prescriptions',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/prescriptions/list/list.component').then(m => m.ListComponent),
        title: 'My Prescriptions — AI Health Companion',
      },
      {
        path: 'upload',
        loadComponent: () =>
          import('./features/prescriptions/upload/upload.component').then(m => m.UploadComponent),
        title: 'Upload Prescription — AI Health Companion',
      },
    ],
  },
  {
    path: 'analysis/:id',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/analysis/details/details.component').then(m => m.DetailsComponent),
    title: 'Analysis Results — AI Health Companion',
  },

  // ── Wildcard fallback ────────────────────────────────────────────────────
  {
    path: '**',
    redirectTo: 'dashboard',
  },
];
