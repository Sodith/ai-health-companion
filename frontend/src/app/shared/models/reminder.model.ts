export interface MedicineSchedule {
  id: number;
  medicine_id: number | null;
  medicine_name: string;
  dosage: string | null;
  frequency: string | null;
  duration_days: number;
  notes: string | null;
  start_date: string;
  end_date: string;
  is_active: boolean;
  reminders_today?: Reminder[];
  created_at: string;
}

export interface Reminder {
  id: number;
  schedule_id: number;
  medicine_name: string;
  dosage: string | null;
  reminder_time: string;
  status: 'pending' | 'taken' | 'skipped';
  taken_at: string | null;
}

export interface HistoryDay {
  date: string;
  reminders: Reminder[];
}

