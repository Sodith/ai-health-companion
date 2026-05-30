/** Mirrors backend PrescriptionUploadResponse */
export interface PrescriptionUploadResponse {
  upload_id: number;
  filename: string;
  status: string;
}

/** Mirrors backend PrescriptionListItem */
export interface PrescriptionListItem {
  id: number;
  original_file_name: string;
  file_type: string;
  file_size: number;
  symptoms: string | null;
  upload_status: string;
  created_at: string;
}

/** Mirrors backend PrescriptionDetail */
export interface PrescriptionDetail {
  id: number;
  user_id: string;
  original_file_name: string;
  stored_file_name: string;
  file_path: string;
  file_type: string;
  file_size: number;
  symptoms: string | null;
  upload_status: string;
  created_at: string;
  updated_at: string;
}

