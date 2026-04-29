import {
  Component, OnInit, OnDestroy, inject, signal, ElementRef, viewChild
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDividerModule } from '@angular/material/divider';
import { Chart, registerables } from 'chart.js';
import { DashboardService } from '../../core/services/dashboard.service';
import { DashboardStats, AnalyticsData } from '../../core/models';

Chart.register(...registerables);

interface KpiCard {
  label: string;
  value: number;
  icon: string;
  color: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule, RouterLink,
    MatCardModule, MatIconModule, MatButtonModule,
    MatProgressSpinnerModule, MatProgressBarModule, MatDividerModule,
  ],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Dashboard</h2>
        <p class="page-sub">Statistiche archivio catastale</p>
      </div>
      <button mat-stroked-button (click)="reload()">
        <mat-icon>refresh</mat-icon> Aggiorna
      </button>
    </div>

    @if (loading()) {
      <div class="center-spinner">
        <mat-spinner diameter="48" />
      </div>
    } @else if (error()) {
      <mat-card appearance="outlined" class="error-card">
        <mat-card-content>
          <div class="error-row">
            <mat-icon>warning</mat-icon>
            <span>{{ error() }}</span>
          </div>
        </mat-card-content>
      </mat-card>
    } @else {
      <!-- KPI cards -->
      <div class="kpi-grid">
        @for (card of kpiCards(); track card.label) {
          <mat-card class="kpi-card" appearance="outlined">
            <mat-card-content>
              <div class="kpi-body">
                <div class="kpi-icon" [style.background]="card.color + '20'" [style.color]="card.color">
                  <mat-icon>{{ card.icon }}</mat-icon>
                </div>
                <div>
                  <div class="kpi-value">{{ card.value | number }}</div>
                  <div class="kpi-label">{{ card.label }}</div>
                </div>
              </div>
            </mat-card-content>
          </mat-card>
        }
      </div>

      <!-- Charts row -->
      <div class="charts-row">
        <!-- Bar chart: top comuni -->
        <mat-card appearance="outlined" class="chart-card">
          <mat-card-header>
            <mat-card-title>Top 10 comuni per partite</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <canvas #barCanvas class="chart-canvas"></canvas>
          </mat-card-content>
        </mat-card>

        <!-- Distribuzione documenti -->
        <mat-card appearance="outlined" class="chart-card">
          <mat-card-header>
            <mat-card-title>Distribuzione documenti</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            @if (analytics()?.distribuzione_documenti?.length) {
              <div class="dist-list">
                @for (d of analytics()!.distribuzione_documenti; track d.label) {
                  <div class="dist-item">
                    <div class="dist-header">
                      <span class="dist-label">{{ d.label }}</span>
                      <span class="dist-value">{{ d.value | number }} ({{ d.pct }}%)</span>
                    </div>
                    <mat-progress-bar mode="determinate" [value]="d.pct" />
                  </div>
                }
              </div>
            }
            @if (analytics()?.qualita_dati) {
              <mat-divider style="margin: 16px 0" />
              <div class="quality-section">
                <div class="quality-title">Qualità dati</div>
                <div class="quality-item">
                  <span>Completezza</span>
                  <span class="quality-pct ok">{{ analytics()!.qualita_dati.completezza_pct }}%</span>
                </div>
                <div class="quality-item">
                  <span>Potenziali duplicati</span>
                  <span class="quality-pct warn">{{ analytics()!.qualita_dati.duplicati_pct }}%</span>
                </div>
              </div>
            }
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Quick links -->
      <div class="quick-links">
        <a mat-flat-button routerLink="/partite">
          <mat-icon>search</mat-icon> Cerca Partite
        </a>
      </div>
    }
  `,
  styles: [`
    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 24px;
    }
    .page-title { margin: 0; font-size: 24px; font-weight: 600; }
    .page-sub { margin: 4px 0 0; color: var(--mat-sys-on-surface-variant); font-size: 14px; }

    .center-spinner { display: flex; justify-content: center; padding: 60px; }

    .error-card { margin-bottom: 16px; }
    .error-row { display: flex; align-items: center; gap: 8px; color: var(--mat-sys-error); }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .kpi-card { cursor: default; }
    .kpi-body { display: flex; align-items: center; gap: 16px; padding: 4px 0; }
    .kpi-icon {
      width: 48px; height: 48px;
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .kpi-icon mat-icon { font-size: 24px; }
    .kpi-value { font-size: 28px; font-weight: 700; line-height: 1; }
    .kpi-label { font-size: 13px; color: var(--mat-sys-on-surface-variant); margin-top: 4px; }

    .charts-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 24px;
    }
    @media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }

    .chart-card mat-card-content { padding-top: 12px; }
    .chart-canvas { max-height: 260px; width: 100% !important; }

    .dist-list { display: flex; flex-direction: column; gap: 14px; padding: 4px 0; }
    .dist-item { display: flex; flex-direction: column; gap: 4px; }
    .dist-header { display: flex; justify-content: space-between; font-size: 13px; }
    .dist-label { font-weight: 500; }
    .dist-value { color: var(--mat-sys-on-surface-variant); }

    .quality-section { padding: 4px 0; }
    .quality-title { font-size: 13px; font-weight: 600; margin-bottom: 10px; }
    .quality-item { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }
    .quality-pct { font-weight: 600; }
    .quality-pct.ok { color: var(--mat-sys-primary); }
    .quality-pct.warn { color: var(--mat-sys-error); }

    .quick-links { display: flex; gap: 12px; }
  `]
})
export class DashboardComponent implements OnInit, OnDestroy {
  private svc = inject(DashboardService);

  loading = signal(true);
  error = signal('');
  stats = signal<DashboardStats | null>(null);
  analytics = signal<AnalyticsData | null>(null);
  kpiCards = signal<KpiCard[]>([]);

  private barCanvas = viewChild<ElementRef<HTMLCanvasElement>>('barCanvas');
  private chart: Chart | null = null;

  ngOnInit() { this.reload(); }

  ngOnDestroy() { this.chart?.destroy(); }

  reload() {
    this.loading.set(true);
    this.error.set('');

    this.svc.getStats().subscribe({
      next: s => {
        this.stats.set(s);
        this.kpiCards.set([
          { label: 'Partite', value: s.totale_partite, icon: 'folder', color: '#1976d2' },
          { label: 'Comuni', value: s.totale_comuni, icon: 'location_city', color: '#388e3c' },
          { label: 'Possessori', value: s.totale_possessori, icon: 'people', color: '#7b1fa2' },
          { label: 'Immobili', value: s.totale_immobili, icon: 'home', color: '#f57c00' },
        ]);
        this.loading.set(false);
        setTimeout(() => this.buildBarChart(s.per_comune), 50);
      },
      error: e => {
        this.error.set(e.error?.detail ?? 'Errore caricamento statistiche');
        this.loading.set(false);
      }
    });

    this.svc.getAnalytics().subscribe({
      next: a => this.analytics.set(a),
      error: () => {}
    });
  }

  private buildBarChart(perComune: DashboardStats['per_comune']) {
    const canvas = this.barCanvas()?.nativeElement;
    if (!canvas) return;
    this.chart?.destroy();

    const labels = perComune.map(r => r.comune_nome ?? r.comune ?? r.nome ?? '?');
    const values = perComune.map(r => r.num_partite);

    this.chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Partite',
          data: values,
          backgroundColor: 'rgba(25, 118, 210, 0.7)',
          borderColor: 'rgba(25, 118, 210, 1)',
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
          x: { ticks: { maxRotation: 45 } }
        }
      }
    });
  }
}
