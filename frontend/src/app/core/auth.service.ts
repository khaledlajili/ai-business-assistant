import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { tap, switchMap, Observable, firstValueFrom } from 'rxjs';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  workspace_id: string;
  workspace_name: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenKey = 'aba_token';
  currentUser = signal<User | null>(null);
  ready = signal(false);

  constructor(private http: HttpClient, private router: Router) {
    void this.init();
  }

  private async init() {
    const token = localStorage.getItem(this.tokenKey);
    if (!token) {
      this.ready.set(true);
      return;
    }
    try {
      const user = await firstValueFrom(this.loadMe());
      this.currentUser.set(user);
    } catch {
      localStorage.removeItem(this.tokenKey);
      this.currentUser.set(null);
    } finally {
      this.ready.set(true);
    }
  }

  login(email: string, password: string): Observable<User> {
    return this.http
      .post<{ access_token: string }>(`${environment.apiUrl}/auth/login`, { email, password })
      .pipe(
        tap((res) => localStorage.setItem(this.tokenKey, res.access_token)),
        switchMap(() => this.loadMe()),
        tap((user) => this.currentUser.set(user)),
      );
  }

  loadMe(): Observable<User> {
    return this.http.get<User>(`${environment.apiUrl}/auth/me`);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  logout(navigate = true) {
    localStorage.removeItem(this.tokenKey);
    this.currentUser.set(null);
    if (navigate) this.router.navigateByUrl('/login');
  }

  isLoggedIn(): boolean {
    return !!this.getToken() && !!this.currentUser();
  }
}
