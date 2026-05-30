/**
 * Standard API response envelope — mirrors the backend APIResponse[T] schema.
 * Every endpoint returns this wrapper.
 */
export interface ApiResponse<T = unknown> {
  success: boolean;
  status_code: number;
  message: string;
  data: T | null;
  error: string | null;
}

