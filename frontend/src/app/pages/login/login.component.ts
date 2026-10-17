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
          <button type="button" class="link" (click)="fill('viewer@demo.local','viewer123')" [disabled]="waking()">Viewer</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-page {
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      background: #0f172a; padding: 1rem;
    }
    .card {
      background: #1e293b; color: #e2e8f0; padding: 2rem; border-radius: 12px;
      width: 100%; max-width: 380px; box-shadow: 0 10px 40px rgba(0,0,0,.4);
    }
    h1 { margin: 0 0 .25rem; font-size: 1.4rem; }
    .subtitle { color: #94a3b8; margin-bottom: 1.25rem; font-size: .9rem; }
    label { display: block; margin: .75rem 0 .25rem; font-size: .85rem; color: #94a3b8; }
    input {
      width: 100%; padding: .6rem .75rem; border-radius: 6px; border: 1px solid #334155;
      background: #0f172a; color: #e2e8f0; box-sizing: border-box;
    }
    button[type=submit] {
      width: 100%; margin-top: 1.25rem; padding: .7rem; border: none; border-radius: 6px;
      background: #3b82f6; color: white; font-weight: 600; cursor: pointer;
    }
    button[type=submit]:disabled { opacity: .65; cursor: not-allowed; }
    .error { color: #f87171; margin-top: 1rem; font-size: .9rem; }
    .banner {
      display: flex; gap: .75rem; align-items: flex-start;
      padding: .75rem; border-radius: 8px; margin-bottom: 1rem; font-size: .85rem; line-height: 1.35;
    }
    .banner.wake { background: #1e3a5f; border: 1px solid #3b82f6; color: #bfdbfe; }
    .banner.wake p { margin: .25rem 0 0; color: #93c5fd; font-size: .8rem; }
    .banner.reduced { background: #422006; border: 1px solid #f59e0b; color: #fde68a; }
    .spinner {
      width: 18px; height: 18px; border: 2px solid #60a5fa; border-top-color: transparent;
      border-radius: 50%; flex-shrink: 0; margin-top: 2px;
      animation: spin .8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .demo-accounts { margin-top: 1.5rem; font-size: .85rem; color: #94a3b8; }
    .link {
      background: none; border: none; color: #60a5fa; cursor: pointer;
      margin-right: .75rem; padding: 0;
    }
    .link:disabled { opacity: .5; cursor: not-allowed; }
  `]
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
  private readonly maxRetries = 12; // ~60s if every 5s

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
        // Network / cold start
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
      // Ping health first; if up, retry login
      this.api.health().subscribe({
        next: () => this.attemptLogin(),
        error: () => this.attemptLogin(), // still try login
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
