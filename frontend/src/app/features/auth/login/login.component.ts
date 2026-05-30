import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

import { MatCardModule }          from '@angular/material/card';
import { MatFormFieldModule }     from '@angular/material/form-field';
import { MatInputModule }         from '@angular/material/input';
import { MatButtonModule }        from '@angular/material/button';
import { MatIconModule }          from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AuthService }        from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './login.component.html',
  styleUrl:    './login.component.scss',
})
export class LoginComponent {
  private readonly fb           = inject(FormBuilder);
  private readonly auth         = inject(AuthService);
  private readonly router       = inject(Router);
  private readonly notification = inject(NotificationService);

  loading      = signal(false);
  hidePassword = signal(true);

  form = this.fb.group({
    email:    ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  get email()    { return this.form.get('email')!;    }
  get password() { return this.form.get('password')!; }

  onSubmit(): void {
    if (this.form.invalid || this.loading()) return;

    this.loading.set(true);
    this.auth.login({ email: this.email.value!, password: this.password.value! })
      .subscribe({
        next: res => {
          this.loading.set(false);
          if (res.success) {
            this.notification.success('Welcome back! Logged in successfully.');
            this.router.navigate(['/dashboard']);
          } else {
            this.notification.error(res.message || 'Login failed. Please try again.');
          }
        },
        error: err => {
          this.loading.set(false);
          const msg = err?.error?.message || err?.error?.detail || 'Invalid email or password.';
          this.notification.error(msg);
        },
      });
  }
}


