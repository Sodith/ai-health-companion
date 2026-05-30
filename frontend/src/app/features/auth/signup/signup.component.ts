import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import {
  ReactiveFormsModule,
  FormBuilder,
  Validators,
  AbstractControl,
  ValidationErrors,
} from '@angular/forms';

import { MatCardModule }            from '@angular/material/card';
import { MatFormFieldModule }       from '@angular/material/form-field';
import { MatInputModule }           from '@angular/material/input';
import { MatButtonModule }          from '@angular/material/button';
import { MatIconModule }            from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AuthService }         from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

/** Cross-field validator: password === confirmPassword */
function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const pw  = control.get('password')?.value;
  const cpw = control.get('confirmPassword')?.value;
  return pw && cpw && pw !== cpw ? { passwordMismatch: true } : null;
}

@Component({
  selector: 'app-signup',
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
  templateUrl: './signup.component.html',
  styleUrl:    './signup.component.scss',
})
export class SignupComponent {
  private readonly fb           = inject(FormBuilder);
  private readonly auth         = inject(AuthService);
  private readonly router       = inject(Router);
  private readonly notification = inject(NotificationService);

  loading          = signal(false);
  hidePassword     = signal(true);
  hideConfirmPw    = signal(true);

  form = this.fb.group(
    {
      email:          ['', [Validators.required, Validators.email]],
      password:       ['', [
        Validators.required,
        Validators.minLength(8),
        Validators.maxLength(64),
        Validators.pattern(/^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$/),
      ]],
      confirmPassword: ['', Validators.required],
    },
    { validators: passwordMatchValidator }
  );

  get email()          { return this.form.get('email')!; }
  get password()       { return this.form.get('password')!; }
  get confirmPassword(){ return this.form.get('confirmPassword')!; }

  get passwordStrengthHint(): string {
    const v = this.password.value ?? '';
    if (!v) return '';
    const checks = [/[A-Z]/, /[a-z]/, /\d/, /[^A-Za-z0-9]/];
    const score = checks.filter(r => r.test(v)).length;
    if (score <= 1) return 'Weak';
    if (score === 2) return 'Fair';
    if (score === 3) return 'Good';
    return 'Strong';
  }

  get strengthClass(): string {
    return this.passwordStrengthHint.toLowerCase();
  }

  onSubmit(): void {
    if (this.form.invalid || this.loading()) return;

    this.loading.set(true);
    this.auth.signup({ email: this.email.value!, password: this.password.value! })
      .subscribe({
        next: res => {
          this.loading.set(false);
          if (res.success) {
            this.notification.success('Account created! Welcome to AI Health Companion.');
            this.router.navigate(['/dashboard']);
          } else {
            this.notification.error(res.message || 'Signup failed. Please try again.');
          }
        },
        error: err => {
          this.loading.set(false);
          const msg =
            err?.error?.message ||
            err?.error?.detail  ||
            'Could not create account. Please try again.';
          this.notification.error(msg);
        },
      });
  }
}


