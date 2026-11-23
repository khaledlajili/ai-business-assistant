import { Component, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-page">
      <div class="card">
        <h1>AI Business Assistant</h1>
        <p class="subtitle">Demo – synthetic data only</p>

        <div class="banner wake" *ngIf="waking()">
          <div class="spinner"></div>
          <div>
            <strong>Starting the demo…</strong>
            <p>Free hosting may take up to a minute on first request. Retrying automatically.</p>
          </div>
        </div>

        <div class="banner reduced" *ngIf="reducedMode()">
          Backend is in reduced mode or rate-limited. Read-only tools still work; draft actions may fail.
        </div>

        <form (ngSubmit)="onSubmit()">
          <label>Email</label>
          <input type="email" [(ngModel)]="email" name="email" required autocomplete="username" />

          <label>Password</label>
          <input type="password" [(ngModel)]="password" name="password" required autocomplete="current-password" />

          <button type="submit" [disabled]="loading() || waking()">
            {{ waking() ? 'Waiting for backend…' : (loading() ? 'Signing in…' : 'Login') }}
          </button>
        </form>

        <p class="error" *ngIf="error()">{{ error() }}</p>

        <div class="demo-accounts">
          <p>Demo accounts:</p>
          <button type="button" class="link" (click)="fill('manager@demo.local','manager123')" [disabled]="waking()">Manager</button>
          <button type="button" class="link" (click)="fill('sales@demo.local','sales123')" [disabled]="waking()">Sales Rep</button>
          <button type="button" class="link" (click)="fill('viewer@demo.local','viewer123')" [disabled]="waking()">Viewer</button>
        </div>
      </div>
    </div>
  `
})
export class LoginComponent implements OnDestroy {
  email = '';
  password = '';
  loading = signal(false);
  error = signal('');
  waking = signal(false);
  reducedMode = signal(false);

  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private retryCount = 0;
  private readonly maxRetries = 12;

  constructor(
    private auth: AuthService,
    private api: ApiService,
    private router: Router,
  ) {}

  ngOnDestroy() {
    this.clearRetry();
  }

  fill(email: string, password: string) {
    this.email = email;
    this.password = password;
  }

  onSubmit() {
    this.clearRetry();
    this.loading.set(true);
    this.error.set('');
    this.waking.set(false);
    this.retryCount = 0;
    this.attemptLogin();
  }

  private attemptLogin() {
    this.auth.login(this.email, this.password).subscribe({
      next: () => {
        this.loading.set(false);
        this.waking.set(false);
        this.router.navigateByUrl('/chat');
      },
      error: (err) => {
        if (err.status === 0 || err.status === 502 || err.status === 503 || err.status === 504) {
          this.waking.set(true);
          this.loading.set(false);
          this.error.set('');
          this.scheduleRetry();
          return;
        }
        this.loading.set(false);
        this.waking.set(false);
        this.error.set(err.error?.detail || 'Login failed');
      },
    });
  }

  private scheduleRetry() {
    if (this.retryCount >= this.maxRetries) {
      this.waking.set(false);
      this.error.set('Backend did not wake up in time. Check that the API is running, then try again.');
      return;
    }
    this.retryCount += 1;
    this.retryTimer = setTimeout(() => {
      this.api.health().subscribe({
        next: () => this.attemptLogin(),
        error: () => this.attemptLogin(),
      });
    }, 5000);
  }

  private clearRetry() {
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }
}
