import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { NotificationService } from '../services/notification.service';

export const jwtInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const auth         = inject(AuthService);
  const notification = inject(NotificationService);
  const token        = auth.getToken();

  // Attach Bearer token if available
  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        // Token expired or invalid — force logout
        notification.error('Session expired. Please log in again.');
        auth.logout();
      } else if (error.status === 403) {
        notification.error('You do not have permission to perform this action.');
      } else if (error.status === 0) {
        notification.error('Unable to reach the server. Please check your connection.');
      }
      return throwError(() => error);
    })
  );
};

