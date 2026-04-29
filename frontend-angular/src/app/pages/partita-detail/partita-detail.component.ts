import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormControl, FormGroup, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { PartiteService } from '../../core/services/partite.service';
import { PartitaDetail, Immobile, Variazione, PossessorePartita, Possessore } from '../../core/models';

const TIPI_VARIAZIONE = ['Vendita', 'Acquisto', 'Successione', 'Variazione',
  'Frazionamento', 'Divisione', 'Trasferimento', 'Altro'];

@Component({
  selector: 'app-partita-detail',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatCardModule, MatTabsModule, MatTableModule, MatButtonModule,
    MatIconModule, MatChipsModule, MatProgressSpinnerModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatDialogModule, MatDividerModule, MatTooltipModule,
  ],
  template: `
    @if (loading()) {
      <div class="center-spinner"><mat-spinner diameter="48" /></div>
    } @else if (error()) {
      <mat-card appearance="outlined">
        <mat-card-content>
          <div class="error-row"><mat-icon>error_outline</mat-icon> {{ error() }}</div>
        </mat-card-content>
      </mat-card>
    } @else if (partita()) {
      <div class="detail-layout">

        <!-- Breadcrumb -->
        <nav class="breadcrumb">
          <a routerLink="/partite" class="bc-link">
            <mat-icon>arrow_back</mat-icon> Archivio
          </a>
          <span class="bc-sep">/</span>
          <span>Partita {{ partita()!.numero_partita }}
            @if (partita()!.suffisso_partita) { /{{ partita()!.suffisso_partita }} }
          </span>
        </nav>

        <!-- Header card -->
        <mat-card appearance="outlined" class="header-card">
          <mat-card-content>
            <div class="header-top">
              <div>
                <div class="header-title">
                  Partita {{ partita()!.numero_partita }}
                  @if (partita()!.suffisso_partita) { /{{ partita()!.suffisso_partita }} }
                  <mat-chip [class]="partita()!.stato === 'attiva' ? 'stato-attiva' : 'stato-chiusa'">
                    {{ partita()!.stato }}
                  </mat-chip>
                  <mat-chip class="tipo-chip">{{ partita()!.tipo }}</mat-chip>
                </div>
                <div class="header-sub">
                  <mat-icon>location_city</mat-icon>
                  {{ partita()!.comune_nome }}
                  @if (partita()!.data_impianto) {
                    · Impianto: {{ partita()!.data_impianto!.slice(0,10) }}
                  }
                  @if (partita()!.data_chiusura) {
                    · Chiusura: {{ partita()!.data_chiusura!.slice(0,10) }}
                  }
                  @if (partita()!.numero_provenienza) {
                    · Provenienza: {{ partita()!.numero_provenienza }}
                  }
                </div>
              </div>
              <div class="header-actions">
                <button mat-stroked-button (click)="toggleModifica()">
                  <mat-icon>edit</mat-icon> Modifica
                </button>
              </div>
            </div>

            <mat-divider style="margin: 16px 0" />

            <div class="counters">
              <div class="counter">
                <span class="counter-n">{{ partita()!.possessori.length }}</span>
                <span class="counter-l">Possessori</span>
              </div>
              <div class="counter">
                <span class="counter-n">{{ partita()!.immobili.length }}</span>
                <span class="counter-l">Immobili</span>
              </div>
              <div class="counter">
                <span class="counter-n">{{ partita()!.variazioni.length }}</span>
                <span class="counter-l">Variazioni</span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Modifica form (inline) -->
        @if (showModifica()) {
          <mat-card appearance="outlined" class="modifica-card">
            <mat-card-header>
              <mat-card-title>Modifica partita</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <form [formGroup]="modificaForm" (ngSubmit)="salvaModifica()" class="modifica-grid">
                <mat-form-field appearance="outline">
                  <mat-label>Stato</mat-label>
                  <mat-select formControlName="stato">
                    <mat-option value="attiva">Attiva</mat-option>
                    <mat-option value="chiusa">Chiusa</mat-option>
                  </mat-select>
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Data chiusura</mat-label>
                  <input matInput type="date" formControlName="data_chiusura" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Suffisso</mat-label>
                  <input matInput formControlName="suffisso_partita" placeholder="es. A" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>N° provenienza</mat-label>
                  <input matInput type="number" formControlName="numero_provenienza" />
                </mat-form-field>
                <div class="modifica-actions">
                  <button mat-flat-button type="submit" [disabled]="saving()">
                    @if (saving()) { <mat-spinner diameter="16" /> }
                    @else { Salva }
                  </button>
                  <button mat-stroked-button type="button" (click)="toggleModifica()">Annulla</button>
                </div>
              </form>
              @if (saveError()) {
                <div class="error-row" style="margin-top:8px"><mat-icon>error_outline</mat-icon> {{ saveError() }}</div>
              }
            </mat-card-content>
          </mat-card>
        }

        <!-- Tabs -->
        <mat-tab-group class="detail-tabs">
          <!-- Possessori -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>people</mat-icon>&nbsp;Possessori ({{ partita()!.possessori.length }})
            </ng-template>
            <div class="tab-content">
              @if (partita()!.possessori.length === 0) {
                <div class="empty-tab">Nessun possessore associato.</div>
              } @else {
                <table mat-table [dataSource]="partita()!.possessori" class="detail-table">
                  <ng-container matColumnDef="nome_completo">
                    <th mat-header-cell *matHeaderCellDef>Nome completo</th>
                    <td mat-cell *matCellDef="let r"><strong>{{ r.nome_completo }}</strong></td>
                  </ng-container>
                  <ng-container matColumnDef="titolo">
                    <th mat-header-cell *matHeaderCellDef>Titolo</th>
                    <td mat-cell *matCellDef="let r">{{ r.titolo ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="quota">
                    <th mat-header-cell *matHeaderCellDef>Quota</th>
                    <td mat-cell *matCellDef="let r">{{ r.quota ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="actions_p">
                    <th mat-header-cell *matHeaderCellDef></th>
                    <td mat-cell *matCellDef="let r">
                      <button mat-icon-button color="warn"
                              (click)="removePossessore(r)"
                              matTooltip="Rimuovi possessore">
                        <mat-icon>person_remove</mat-icon>
                      </button>
                    </td>
                  </ng-container>
                  <tr mat-header-row *matHeaderRowDef="possessoriCols"></tr>
                  <tr mat-row *matRowDef="let r; columns: possessoriCols;"></tr>
                </table>
              }

              <!-- Aggiungi possessore -->
              @if (!showAddPossessore()) {
                <button mat-stroked-button style="margin-top:12px" (click)="showAddPossessore.set(true)">
                  <mat-icon>person_add</mat-icon> Aggiungi possessore
                </button>
              } @else {
                <div class="add-form">
                  <mat-form-field appearance="outline" style="width:100%">
                    <mat-label>Cerca possessore (min 2 caratteri)</mat-label>
                    <input matInput [formControl]="possessoreSearch" />
                    <mat-icon matPrefix>search</mat-icon>
                  </mat-form-field>
                  @if (possessoriResults().length > 0) {
                    <div class="search-results">
                      @for (p of possessoriResults(); track p.id) {
                        <div class="search-result-item" (click)="selectPossessore(p)">
                          <strong>{{ p.nome_completo }}</strong>
                          @if (p.paternita) { <span class="pater">fu {{ p.paternita }}</span> }
                        </div>
                      }
                    </div>
                  }
                  @if (selectedPossessore()) {
                    <div class="selected-p">
                      <mat-icon>check_circle</mat-icon>
                      {{ selectedPossessore()!.nome_completo }}
                      <button mat-icon-button (click)="selectedPossessore.set(null)">
                        <mat-icon>close</mat-icon>
                      </button>
                    </div>
                    <div class="add-form-row">
                      <mat-form-field appearance="outline">
                        <mat-label>Titolo</mat-label>
                        <input matInput [formControl]="titoloCtrl" />
                      </mat-form-field>
                      <mat-form-field appearance="outline">
                        <mat-label>Quota</mat-label>
                        <input matInput [formControl]="quotaCtrl" placeholder="es. 1/2" />
                      </mat-form-field>
                    </div>
                    <div class="add-form-actions">
                      <button mat-flat-button (click)="addPossessore()" [disabled]="saving()">
                        Associa
                      </button>
                      <button mat-stroked-button (click)="cancelAddPossessore()">Annulla</button>
                    </div>
                  } @else {
                    <button mat-stroked-button (click)="cancelAddPossessore()">Annulla</button>
                  }
                </div>
              }
            </div>
          </mat-tab>

          <!-- Immobili -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>home</mat-icon>&nbsp;Immobili ({{ partita()!.immobili.length }})
            </ng-template>
            <div class="tab-content">
              @if (partita()!.immobili.length === 0) {
                <div class="empty-tab">Nessun immobile registrato.</div>
              } @else {
                <table mat-table [dataSource]="partita()!.immobili" class="detail-table">
                  <ng-container matColumnDef="localita_nome">
                    <th mat-header-cell *matHeaderCellDef>Località</th>
                    <td mat-cell *matCellDef="let r">{{ r.localita_nome }}</td>
                  </ng-container>
                  <ng-container matColumnDef="natura">
                    <th mat-header-cell *matHeaderCellDef>Natura</th>
                    <td mat-cell *matCellDef="let r"><strong>{{ r.natura }}</strong></td>
                  </ng-container>
                  <ng-container matColumnDef="piani">
                    <th mat-header-cell *matHeaderCellDef>Piani</th>
                    <td mat-cell *matCellDef="let r">{{ r.numero_piani ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="vani">
                    <th mat-header-cell *matHeaderCellDef>Vani</th>
                    <td mat-cell *matCellDef="let r">{{ r.numero_vani ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="consistenza">
                    <th mat-header-cell *matHeaderCellDef>Consistenza</th>
                    <td mat-cell *matCellDef="let r">{{ r.consistenza ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="classificazione">
                    <th mat-header-cell *matHeaderCellDef>Classe</th>
                    <td mat-cell *matCellDef="let r">{{ r.classificazione ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="actions_i">
                    <th mat-header-cell *matHeaderCellDef></th>
                    <td mat-cell *matCellDef="let r">
                      <button mat-icon-button color="warn"
                              (click)="removeImmobile(r)"
                              matTooltip="Rimuovi immobile">
                        <mat-icon>delete</mat-icon>
                      </button>
                    </td>
                  </ng-container>
                  <tr mat-header-row *matHeaderRowDef="immobiliCols"></tr>
                  <tr mat-row *matRowDef="let r; columns: immobiliCols;"></tr>
                </table>
              }
            </div>
          </mat-tab>

          <!-- Variazioni -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>swap_horiz</mat-icon>&nbsp;Variazioni ({{ partita()!.variazioni.length }})
            </ng-template>
            <div class="tab-content">
              @if (partita()!.variazioni.length === 0) {
                <div class="empty-tab">Nessuna variazione registrata.</div>
              } @else {
                <table mat-table [dataSource]="partita()!.variazioni" class="detail-table">
                  <ng-container matColumnDef="data_variazione">
                    <th mat-header-cell *matHeaderCellDef>Data</th>
                    <td mat-cell *matCellDef="let r">{{ r.data_variazione ? r.data_variazione.slice(0,10) : '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="tipo">
                    <th mat-header-cell *matHeaderCellDef>Tipo</th>
                    <td mat-cell *matCellDef="let r"><strong>{{ r.tipo }}</strong></td>
                  </ng-container>
                  <ng-container matColumnDef="numero_riferimento">
                    <th mat-header-cell *matHeaderCellDef>Riferimento</th>
                    <td mat-cell *matCellDef="let r">{{ r.numero_riferimento ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="notaio">
                    <th mat-header-cell *matHeaderCellDef>Notaio</th>
                    <td mat-cell *matCellDef="let r">{{ r.notaio ?? '—' }}</td>
                  </ng-container>
                  <ng-container matColumnDef="origine">
                    <th mat-header-cell *matHeaderCellDef>Da partita</th>
                    <td mat-cell *matCellDef="let r">
                      @if (r.partita_origine_id) {
                        @if (r.partita_origine_id !== partita()!.id) {
                          <a class="link-p" [routerLink]="['/partite', r.partita_origine_id]">
                            {{ r.origine_numero_partita ?? r.partita_origine_id }}
                            @if (r.origine_comune_nome) { — {{ r.origine_comune_nome }} }
                          </a>
                        } @else {
                          <span class="self-ref">questa</span>
                        }
                      } @else { — }
                    </td>
                  </ng-container>
                  <ng-container matColumnDef="destinazione">
                    <th mat-header-cell *matHeaderCellDef>A partita</th>
                    <td mat-cell *matCellDef="let r">
                      @if (r.partita_destinazione_id) {
                        @if (r.partita_destinazione_id !== partita()!.id) {
                          <a class="link-p" [routerLink]="['/partite', r.partita_destinazione_id]">
                            {{ r.destinazione_numero_partita ?? r.partita_destinazione_id }}
                            @if (r.destinazione_comune_nome) { — {{ r.destinazione_comune_nome }} }
                          </a>
                        } @else {
                          <span class="self-ref">questa</span>
                        }
                      } @else { — }
                    </td>
                  </ng-container>
                  <ng-container matColumnDef="actions_v">
                    <th mat-header-cell *matHeaderCellDef></th>
                    <td mat-cell *matCellDef="let r">
                      <button mat-icon-button color="warn"
                              (click)="removeVariazione(r)"
                              matTooltip="Elimina variazione">
                        <mat-icon>delete</mat-icon>
                      </button>
                    </td>
                  </ng-container>
                  <tr mat-header-row *matHeaderRowDef="variazioniCols"></tr>
                  <tr mat-row *matRowDef="let r; columns: variazioniCols;"></tr>
                </table>
              }
            </div>
          </mat-tab>
        </mat-tab-group>
      </div>
    }
  `,
  styles: [`
    .center-spinner { display: flex; justify-content: center; padding: 60px; }
    .error-row { display: flex; align-items: center; gap: 8px; color: var(--mat-sys-error); }

    .detail-layout { display: flex; flex-direction: column; gap: 16px; }

    .breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--mat-sys-on-surface-variant); }
    .bc-link { display: flex; align-items: center; gap: 4px; color: var(--mat-sys-primary); text-decoration: none; cursor: pointer; }
    .bc-link mat-icon { font-size: 16px; width: 16px; height: 16px; }
    .bc-sep { opacity: 0.5; }

    .header-card { }
    .header-top { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
    .header-title { font-size: 22px; font-weight: 600; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .header-sub { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--mat-sys-on-surface-variant); margin-top: 6px; }
    .header-sub mat-icon { font-size: 16px; width: 16px; height: 16px; }
    .header-actions { display: flex; gap: 8px; }

    .stato-attiva { background: #e8f5e9 !important; color: #2e7d32 !important; }
    .stato-chiusa { background: #fafafa !important; color: #757575 !important; }
    .tipo-chip { background: var(--mat-sys-secondary-container) !important; }

    .counters { display: flex; gap: 28px; }
    .counter { display: flex; flex-direction: column; }
    .counter-n { font-size: 26px; font-weight: 700; }
    .counter-l { font-size: 12px; color: var(--mat-sys-on-surface-variant); }

    .modifica-card { border-left: 3px solid var(--mat-sys-primary); }
    .modifica-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 8px 16px;
      align-items: center;
    }
    .modifica-actions { display: flex; gap: 8px; align-items: center; padding-top: 4px; }

    .detail-tabs { background: var(--mat-sys-surface); border-radius: 12px; }
    .tab-content { padding: 16px; }
    .detail-table { width: 100%; }

    .empty-tab { padding: 24px 0; color: var(--mat-sys-on-surface-variant); font-size: 14px; }

    .add-form { margin-top: 16px; padding: 16px; background: var(--mat-sys-surface-container-low); border-radius: 8px; }
    .add-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
    .add-form-actions { display: flex; gap: 8px; margin-top: 8px; }

    .search-results { background: var(--mat-sys-surface); border: 1px solid var(--mat-sys-outline-variant); border-radius: 8px; margin-bottom: 12px; max-height: 200px; overflow-y: auto; }
    .search-result-item { padding: 10px 14px; cursor: pointer; font-size: 13px; border-bottom: 1px solid var(--mat-sys-outline-variant); }
    .search-result-item:hover { background: var(--mat-sys-surface-container-low); }
    .search-result-item:last-child { border-bottom: none; }
    .pater { font-size: 11px; color: var(--mat-sys-on-surface-variant); margin-left: 8px; }

    .selected-p { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--mat-sys-primary-container); border-radius: 8px; margin-bottom: 12px; }
    .selected-p mat-icon { color: var(--mat-sys-primary); }

    .link-p { color: var(--mat-sys-primary); text-decoration: underline; cursor: pointer; }
    .self-ref { color: var(--mat-sys-on-surface-variant); font-style: italic; }
  `]
})
export class PartitaDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private svc = inject(PartiteService);

  possessoriCols = ['nome_completo', 'titolo', 'quota', 'actions_p'];
  immobiliCols = ['localita_nome', 'natura', 'piani', 'vani', 'consistenza', 'classificazione', 'actions_i'];
  variazioniCols = ['data_variazione', 'tipo', 'numero_riferimento', 'notaio', 'origine', 'destinazione', 'actions_v'];

  loading = signal(true);
  error = signal('');
  saving = signal(false);
  saveError = signal('');
  partita = signal<PartitaDetail | null>(null);
  showModifica = signal(false);
  showAddPossessore = signal(false);
  possessoriResults = signal<Possessore[]>([]);
  selectedPossessore = signal<Possessore | null>(null);

  modificaForm = new FormGroup({
    stato: new FormControl(''),
    data_chiusura: new FormControl<string | null>(null),
    suffisso_partita: new FormControl<string | null>(null),
    numero_provenienza: new FormControl<number | null>(null),
  });

  possessoreSearch = new FormControl('');
  titoloCtrl = new FormControl('proprietà esclusiva');
  quotaCtrl = new FormControl('');

  private searchTimer: any;

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.load(id);

    this.possessoreSearch.valueChanges.subscribe(q => {
      clearTimeout(this.searchTimer);
      if ((q?.length ?? 0) < 2) { this.possessoriResults.set([]); return; }
      this.searchTimer = setTimeout(() => {
        this.svc.searchPossessori(q!).subscribe({
          next: r => this.possessoriResults.set(r),
          error: () => {}
        });
      }, 300);
    });
  }

  private load(id: number) {
    this.loading.set(true);
    this.svc.getDetail(id).subscribe({
      next: p => { this.partita.set(p); this.loading.set(false); },
      error: e => { this.error.set(e.error?.detail ?? 'Partita non trovata'); this.loading.set(false); }
    });
  }

  private reload() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.svc.getDetail(id).subscribe({ next: p => this.partita.set(p), error: () => {} });
  }

  toggleModifica() {
    const p = this.partita();
    if (!p) return;
    this.showModifica.update(v => !v);
    if (this.showModifica()) {
      this.modificaForm.patchValue({
        stato: p.stato,
        data_chiusura: p.data_chiusura?.slice(0, 10) ?? null,
        suffisso_partita: p.suffisso_partita ?? null,
        numero_provenienza: p.numero_provenienza ?? null,
      });
    }
  }

  salvaModifica() {
    const p = this.partita();
    if (!p) return;
    this.saving.set(true);
    this.saveError.set('');
    this.svc.patchPartita(p.id, this.modificaForm.value).subscribe({
      next: () => { this.saving.set(false); this.showModifica.set(false); this.reload(); },
      error: e => { this.saveError.set(e.error?.detail ?? 'Errore salvataggio'); this.saving.set(false); }
    });
  }

  selectPossessore(p: Possessore) {
    this.selectedPossessore.set(p);
    this.possessoriResults.set([]);
    this.possessoreSearch.setValue('', { emitEvent: false });
  }

  addPossessore() {
    const p = this.partita();
    const sel = this.selectedPossessore();
    if (!p || !sel) return;
    this.saving.set(true);
    this.svc.addPossessore(p.id, {
      possessore_id: sel.id,
      titolo: this.titoloCtrl.value || 'proprietà esclusiva',
      quota: this.quotaCtrl.value || undefined,
      tipo_partita: (p.tipo || 'principale').toLowerCase() as 'principale' | 'secondaria',
    }).subscribe({
      next: () => { this.saving.set(false); this.cancelAddPossessore(); this.reload(); },
      error: () => { this.saving.set(false); }
    });
  }

  cancelAddPossessore() {
    this.showAddPossessore.set(false);
    this.selectedPossessore.set(null);
    this.possessoriResults.set([]);
    this.possessoreSearch.setValue('', { emitEvent: false });
    this.titoloCtrl.setValue('proprietà esclusiva');
    this.quotaCtrl.setValue('');
  }

  removePossessore(r: PossessorePartita) {
    const p = this.partita();
    if (!p || !confirm(`Rimuovere ${r.nome_completo} da questa partita?`)) return;
    this.svc.removePossessore(p.id, r.id).subscribe({ next: () => this.reload(), error: () => {} });
  }

  removeImmobile(r: Immobile) {
    const p = this.partita();
    if (!p || !confirm(`Rimuovere immobile "${r.natura}" in ${r.localita_nome}?`)) return;
    this.svc.removeImmobile(p.id, r.id).subscribe({ next: () => this.reload(), error: () => {} });
  }

  removeVariazione(r: Variazione) {
    const p = this.partita();
    if (!p || !confirm(`Eliminare variazione "${r.tipo}" del ${r.data_variazione?.slice(0,10)}?`)) return;
    this.svc.removeVariazione(p.id, r.id).subscribe({ next: () => this.reload(), error: () => {} });
  }
}
