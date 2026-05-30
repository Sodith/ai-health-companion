import { Injectable, inject } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig } from '@angular/material/snack-bar';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly snackBar = inject(MatSnackBar);

  private _show(message: string, panelClass: string, duration = 4000): void {
    const config: MatSnackBarConfig = {
      duration,
      horizontalPosition: 'right',
      verticalPosition: 'top',
      panelClass: [panelClass],
    };
    this.snackBar.open(message, '✕', config);
  }

  success(message: string): void {
    this._show(message, 'snack-success');
  }

  error(message: string): void {
    this._show(message, 'snack-error', 6000);
  }

  info(message: string): void {
    this._show(message, 'snack-info');
  }
}

