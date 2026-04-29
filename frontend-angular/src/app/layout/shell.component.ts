import { Component, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../core/auth.service';

const NAV = [
  { label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
  { label: 'Ricerca Partite', icon: 'search', route: '/partite' },
];

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    RouterOutlet, RouterLink, RouterLinkActive,
    MatSidenavModule, MatToolbarModule, MatListModule,
    MatIconModule, MatButtonModule, MatMenuModule, MatTooltipModule,
  ],
  template: `
    <mat-sidenav-container class="shell-container">
      <mat-sidenav mode="side" opened class="sidenav">
        <div class="brand">
          <mat-icon class="brand-icon">account_balance</mat-icon>
          <div>
            <div class="brand-name">Foliarium</div>
            <div class="brand-sub">Archivio Catastale</div>
          </div>
        </div>

        <mat-nav-list class="nav-list">
          @for (item of nav; track item.route) {
            <a mat-list-item
              [routerLink]="item.route"
              routerLinkActive="nav-active"
              [matTooltip]="item.label"
              matTooltipPosition="right">
              <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
              <span matListItemTitle>{{ item.label }}</span>
            </a>
          }
        </mat-nav-list>

        <div class="sidenav-footer">
          <div class="user-chip">
            <mat-icon>person</mat-icon>
            <div class="user-info">
              <span class="user-name">{{ auth.user()?.nome_completo }}</span>
              <span class="user-role">{{ auth.user()?.ruolo }}</span>
            </div>
          </div>
        </div>
      </mat-sidenav>

      <mat-sidenav-content class="main-area">
        <mat-toolbar class="topbar">
          <span class="topbar-spacer"></span>
          <button mat-icon-button [matMenuTriggerFor]="menu" matTooltip="Account">
            <mat-icon>account_circle</mat-icon>
          </button>
          <mat-menu #menu="matMenu">
            <button mat-menu-item (click)="auth.logout()">
              <mat-icon>logout</mat-icon>
              <span>Esci</span>
            </button>
          </mat-menu>
        </mat-toolbar>

        <div class="page-area">
          <router-outlet />
        </div>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .shell-container { height: 100vh; }

    .sidenav {
      width: 230px;
      border-right: 1px solid var(--mat-sys-outline-variant);
      display: flex;
      flex-direction: column;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 20px 16px 16px;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
    .brand-icon { color: var(--mat-sys-primary); font-size: 30px; width: 30px; height: 30px; }
    .brand-name { font-size: 17px; font-weight: 700; color: var(--mat-sys-on-surface); line-height: 1.2; }
    .brand-sub { font-size: 11px; color: var(--mat-sys-on-surface-variant); }

    .nav-list { flex: 1; padding-top: 8px; }

    ::ng-deep .nav-active {
      background: var(--mat-sys-primary-container) !important;
      color: var(--mat-sys-on-primary-container) !important;
      border-radius: 8px;
    }

    .sidenav-footer {
      padding: 12px 16px;
      border-top: 1px solid var(--mat-sys-outline-variant);
    }
    .user-chip { display: flex; align-items: center; gap: 10px; }
    .user-chip mat-icon { color: var(--mat-sys-on-surface-variant); font-size: 20px; }
    .user-info { display: flex; flex-direction: column; }
    .user-name { font-size: 13px; font-weight: 500; }
    .user-role { font-size: 11px; color: var(--mat-sys-on-surface-variant); text-transform: capitalize; }

    .main-area { display: flex; flex-direction: column; }

    .topbar {
      background: var(--mat-sys-surface);
      border-bottom: 1px solid var(--mat-sys-outline-variant);
      height: 52px;
      min-height: 52px;
    }
    .topbar-spacer { flex: 1; }

    .page-area {
      flex: 1;
      padding: 28px 32px;
      overflow: auto;
      background: var(--mat-sys-surface-dim);
    }
  `]
})
export class ShellComponent {
  auth = inject(AuthService);
  nav = NAV;
}
