import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: '',
    loadComponent: () => import('./layout/shell.component').then(m => m.ShellComponent),
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
      },
      {
        path: 'partite',
        loadComponent: () => import('./pages/ricerca-partite/ricerca-partite.component').then(m => m.RicercaPartiteComponent),
      },
      {
        path: 'partite/:id',
        loadComponent: () => import('./pages/partita-detail/partita-detail.component').then(m => m.PartitaDetailComponent),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
