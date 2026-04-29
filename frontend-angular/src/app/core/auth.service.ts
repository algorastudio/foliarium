import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs';
import { LoginResponse } from './models';

const TOKEN_KEY = 'foliarium_token';
const USER_KEY = 'foliarium_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  private _user = signal<LoginResponse | null>(this._loadUser());
  readonly user = this._user.asReadonly();
  readonly isLoggedIn = computed(() => !!this._user());

  login(username: string, password: string) {
    return this.http.post<LoginResponse>('/api/auth/login', { username, password }).pipe(
      tap(u => {
        this._user.set(u);
        localStorage.setItem(TOKEN_KEY, u.token);
        localStorage.setItem(USER_KEY, JSON.stringify(u));
      })
    );
  }

  logout() {
    this.http.post('/api/auth/logout', {}).subscribe({ error: () => {} });
    this._user.set(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  private _loadUser(): LoginResponse | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }
}
