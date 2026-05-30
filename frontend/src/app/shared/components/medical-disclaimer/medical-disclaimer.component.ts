import { Component, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-medical-disclaimer',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="medical-disclaimer">
      <mat-icon>warning_amber</mat-icon>
      <p>{{ message() }}</p>
    </div>
  `
})
export class MedicalDisclaimerComponent {
  message = input<string>(
    'This application does not provide medical advice. ' +
    'AI-generated analysis is NOT a substitute for professional medical advice. ' +
    'Always consult a qualified healthcare provider.'
  );
}

