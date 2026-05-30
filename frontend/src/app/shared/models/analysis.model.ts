/** Mirrors backend MedicineResponse */
export interface Medicine {
  id: number;
  medicine_name: string;
  dosage: string | null;
  frequency: string | null;
  duration: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/** Mirrors backend AnalysisResponse */
export interface Analysis {
  analysis_id: number;
  prescription_id: number;
  analysis_status: string;
  disease_detected: string | null;
  doctor_advice: string[];
  lifestyle_changes: string[];
  medicines: Medicine[];
  disclaimer: string;
  created_at: string;
  updated_at: string;
}

