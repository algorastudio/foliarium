import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule,
  ],
  template: `
    <div class="wrapper">
      <div class="hero-panel">
        <mat-icon class="hero-icon">account_balance</mat-icon>
        <h1>Foliarium</h1>
        <p>Archivio Catastale Storico<br>Archivio di Stato di Savona</p>
      </div>

      <mat-card class="login-card" appearance="outlined">
        <mat-card-header>
          <mat-card-title>Accedi</mat-card-title>
          <mat-card-subtitle>Inserisci le tue credenziali</mat-card-subtitle>
        </mat-card-header>

        <mat-card-content>
          <form [formGroup]="form" (ngSubmit)="submit()" class="login-form">
            <mat-form-field appearance="outline">
              <mat-label>Nome utente</mat-label>
              <input matInput formControlName="username" autocomplete="username" />
              <mat-icon matPrefix>person_outline</mat-icon>
              @if (form.controls.username.touched && form.controls.username.invalid) {
                <mat-error>Campo obbligatorio</mat-error>
              }
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Password</mat-label>
              <input matInput [type]="showPwd() ? 'text' : 'password'"
                     formControlName="password" autocomplete="current-password" />
              <mat-icon matPrefix>lock_outline</mat-icon>
              <button mat-icon-button matSuffix type="button"
                      (click)="showPwd.set(!showPwd())"
                      [attr.aria-label]="showPwd() ? 'Nascondi password' : 'Mostra password'">
                <mat-icon>{{ showPwd() ? 'visibility_off' : 'visibility' }}</mat-icon>
              </button>
              @if (form.controls.password.touched && form.controls.password.invalid) {
                <mat-error>Campo obbligatorio</mat-error>
              }
            </mat-form-field>

            @if (error()) {
              <div class="error-banner">
                <mat-icon>error_outline</mat-icon>
                <span>{{ error() }}</span>
              </div>
            }

            <button mat-flat-button class="submit-btn" type="submit"
                    [disabled]="form.invalid || loading()">
              @if (loading()) {
                <mat-spinner diameter="18" />
              } @else {
                Accedi
              }
            </button>
          </form>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100vh; }

    .wrapper {
      height: 100%;
      display: grid;
      grid-template-columns: 1fr 1fr;
    }

    .hero-panel {
      background: var(--mat-sys-primary);
      color: var(--mat-sys-on-primary);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      padding: 48px;
    }
    .hero-icon { font-size: 80px; width: 80px; height: 80px; opacity: 0.9; }
    .hero-panel h1 { font-size: 42px; font-weight: 700; margin: 0; }
    .hero-panel p { font-size: 16px; text-align: center; opacity: 0.85; margin: 0; line-height: 1.6; }

    .login-card {
      align-self: center;
      justify-self: center;
      width: 380px;
    }

    .login-form {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding-top: 8px;
    }
    mat-form-field { width: 100%; }

    .error-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: var(--mat-sys-error-container);
      color: var(--mat-sys-on-error-container);
      border-radius: 8px;
      font-size: 13px;
    }
    .error-banner mat-icon { font-size: 18px; width: 18px; height: 18px; }

    .submit-btn {
      height: 44px;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 4px;
    }

    @media (max-width: 640px) {
      .wrapper { grid-template-columns: 1fr; }
      .hero-panel { display: none; }
      .login-card { width: calc(100% - 48px); }
    }
  `]
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  showPwd = signal(false);
  loading = signal(false);
  error = signal('');

  form = new FormGroup({
    username: new FormControl('', Validators.required),
    password: new FormControl('', Validators.required),
  });

  submit() {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    const { username, password } = this.form.value;
    this.auth.login(username!, password!).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (e) => {
        this.error.set(e.error?.detail ?? 'Credenziali non valide');
        this.loading.set(false);
      },
    });
  }
}
