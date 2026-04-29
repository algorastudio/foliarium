import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { PartiteService } from '../../core/services/partite.service';
import { Partita } from '../../core/models';

const COLUMNS = ['numero_partita', 'comune_nome', 'tipo', 'stato', 'data_impianto', 'actions'];

@Component({
  selector: 'app-ricerca-partite',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatTableModule, MatPaginatorModule,
    MatProgressSpinnerModule, MatChipsModule, MatTooltipModule,
  ],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Ricerca Partite</h2>
        <p class="page-sub">Cerca tra le partite catastali dell'archivio</p>
      </div>
    </div>

    <!-- Filtri -->
    <mat-card appearance="outlined" class="filter-card">
      <mat-card-content>
        <form [formGroup]="filterForm" (ngSubmit)="search()" class="filter-grid">
          <mat-form-field appearance="outline">
            <mat-label>Comune</mat-label>
            <mat-select formControlName="comune_id">
              <mat-option [value]="null">— Tutti —</mat-option>
              @for (c of comuni(); track c.id) {
                <mat-option [value]="c.id">{{ c.nome }} ({{ c.provincia }})</mat-option>
              }
            </mat-select>
            <mat-icon matPrefix>location_city</mat-icon>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>N° Partita</mat-label>
            <input matInput type="number" formControlName="numero_partita" placeholder="es. 1234" />
            <mat-icon matPrefix>tag</mat-icon>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Possessore</mat-label>
            <input matInput formControlName="possessore" placeholder="Cognome o nome…" />
            <mat-icon matPrefix>person</mat-icon>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Natura immobile</mat-label>
            <input matInput formControlName="immobile_natura" placeholder="es. Fabbricato" />
            <mat-icon matPrefix>home</mat-icon>
          </mat-form-field>

          <div class="filter-actions">
            <button mat-flat-button type="submit" [disabled]="loading()">
              <mat-icon>search</mat-icon> Cerca
            </button>
            <button mat-stroked-button type="button" (click)="clearFilters()">
              <mat-icon>clear</mat-icon> Pulisci
            </button>
          </div>
        </form>
      </mat-card-content>
    </mat-card>

    <!-- Risultati -->
    @if (loading()) {
      <div class="center-spinner"><mat-spinner diameter="40" /></div>
    }

    @if (!loading() && searched()) {
      <mat-card appearance="outlined" class="results-card">
        <mat-card-header>
          <mat-card-title>
            Risultati
            <mat-chip class="count-chip">{{ allRows().length }}</mat-chip>
          </mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @if (allRows().length === 0) {
            <div class="empty-state">
              <mat-icon>search_off</mat-icon>
              <p>Nessuna partita trovata con i criteri indicati.</p>
            </div>
          } @else {
            <table mat-table [dataSource]="pageRows()" class="results-table">
              <ng-container matColumnDef="numero_partita">
                <th mat-header-cell *matHeaderCellDef>N° Partita</th>
                <td mat-cell *matCellDef="let r">
                  <strong>{{ r.numero_partita }}</strong>
                  @if (r.suffisso_partita) {<span class="suffix">/{{ r.suffisso_partita }}</span>}
                </td>
              </ng-container>

              <ng-container matColumnDef="comune_nome">
                <th mat-header-cell *matHeaderCellDef>Comune</th>
                <td mat-cell *matCellDef="let r">{{ r.comune_nome }}</td>
              </ng-container>

              <ng-container matColumnDef="tipo">
                <th mat-header-cell *matHeaderCellDef>Tipo</th>
                <td mat-cell *matCellDef="let r">
                  <mat-chip [class]="'tipo-' + r.tipo?.toLowerCase()">{{ r.tipo }}</mat-chip>
                </td>
              </ng-container>

              <ng-container matColumnDef="stato">
                <th mat-header-cell *matHeaderCellDef>Stato</th>
                <td mat-cell *matCellDef="let r">
                  <mat-chip [class]="r.stato?.toLowerCase() === 'attiva' ? 'stato-attiva' : 'stato-chiusa'">
                    {{ r.stato }}
                  </mat-chip>
                </td>
              </ng-container>

              <ng-container matColumnDef="data_impianto">
                <th mat-header-cell *matHeaderCellDef>Data impianto</th>
                <td mat-cell *matCellDef="let r">{{ r.data_impianto ? r.data_impianto.slice(0,10) : '—' }}</td>
              </ng-container>

              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef></th>
                <td mat-cell *matCellDef="let r">
                  <button mat-icon-button (click)="openDetail(r)" matTooltip="Apri dettaglio">
                    <mat-icon>open_in_new</mat-icon>
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="columns"></tr>
              <tr mat-row *matRowDef="let r; columns: columns"
                  class="data-row" (click)="openDetail(r)"></tr>
            </table>

            <mat-paginator
              [length]="allRows().length"
              [pageSize]="pageSize"
              [pageSizeOptions]="[20, 50, 100]"
              (page)="onPage($event)"
              showFirstLastButtons />
          }
        </mat-card-content>
      </mat-card>
    }
  `,
  styles: [`
    .page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
    .page-title { margin: 0; font-size: 24px; font-weight: 600; }
    .page-sub { margin: 4px 0 0; color: var(--mat-sys-on-surface-variant); font-size: 14px; }

    .filter-card { margin-bottom: 20px; }
    .filter-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 8px 16px;
      align-items: center;
    }
    .filter-actions { display: flex; gap: 8px; align-items: center; padding-top: 4px; }

    .center-spinner { display: flex; justify-content: center; padding: 40px; }

    .results-card { }
    mat-card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; }
    .count-chip { font-size: 12px; }

    .results-table { width: 100%; }
    .data-row { cursor: pointer; }
    .data-row:hover { background: var(--mat-sys-surface-container-low); }

    .suffix { color: var(--mat-sys-on-surface-variant); font-weight: 400; }

    .stato-attiva { background: #e8f5e9 !important; color: #2e7d32 !important; }
    .stato-chiusa { background: #fafafa !important; color: #757575 !important; }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 40px;
      color: var(--mat-sys-on-surface-variant);
    }
    .empty-state mat-icon { font-size: 48px; width: 48px; height: 48px; }
  `]
})
export class RicercaPartiteComponent implements OnInit {
  private svc = inject(PartiteService);
  private router = inject(Router);

  columns = COLUMNS;
  loading = signal(false);
  searched = signal(false);
  allRows = signal<Partita[]>([]);
  pageRows = signal<Partita[]>([]);
  comuni = signal<{ id: number; nome: string; provincia: string }[]>([]);

  pageSize = 20;
  pageIndex = 0;

  filterForm = new FormGroup({
    comune_id: new FormControl<number | null>(null),
    numero_partita: new FormControl<number | null>(null),
    possessore: new FormControl(''),
    immobile_natura: new FormControl(''),
  });

  ngOnInit() {
    this.svc.getComuni().subscribe({ next: c => this.comuni.set(c), error: () => {} });
    this.search();
  }

  search() {
    const v = this.filterForm.value;
    this.loading.set(true);
    this.svc.search({
      comune_id: v.comune_id ?? undefined,
      numero_partita: v.numero_partita ?? undefined,
      possessore: v.possessore || undefined,
      immobile_natura: v.immobile_natura || undefined,
    }).subscribe({
      next: rows => {
        this.allRows.set(rows);
        this.pageIndex = 0;
        this.updatePage();
        this.loading.set(false);
        this.searched.set(true);
      },
      error: () => { this.loading.set(false); this.searched.set(true); }
    });
  }

  clearFilters() {
    this.filterForm.reset();
    this.searched.set(false);
    this.allRows.set([]);
  }

  onPage(e: PageEvent) {
    this.pageIndex = e.pageIndex;
    this.pageSize = e.pageSize;
    this.updatePage();
  }

  openDetail(r: Partita) {
    this.router.navigate(['/partite', r.id]);
  }

  private updatePage() {
    const start = this.pageIndex * this.pageSize;
    this.pageRows.set(this.allRows().slice(start, start + this.pageSize));
  }
}
