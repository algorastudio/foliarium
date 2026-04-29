import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Partita, PartitaDetail, Possessore } from '../models';

export interface SearchParams {
  comune_id?: number;
  numero_partita?: number;
  possessore?: string;
  immobile_natura?: string;
  suffisso?: string;
}

@Injectable({ providedIn: 'root' })
export class PartiteService {
  private http = inject(HttpClient);

  search(p: SearchParams) {
    let params = new HttpParams();
    if (p.comune_id != null) params = params.set('comune_id', p.comune_id);
    if (p.numero_partita != null) params = params.set('numero_partita', p.numero_partita);
    if (p.possessore) params = params.set('possessore', p.possessore);
    if (p.immobile_natura) params = params.set('immobile_natura', p.immobile_natura);
    if (p.suffisso) params = params.set('suffisso', p.suffisso);
    return this.http.get<Partita[]>('/api/partite', { params });
  }

  getDetail(id: number) {
    return this.http.get<PartitaDetail>(`/api/partite/${id}`);
  }

  getGenealogia(id: number) {
    return this.http.get<any>(`/api/genealogia/${id}`);
  }

  searchPossessori(q: string) {
    return this.http.get<Possessore[]>(`/api/possessori?q=${encodeURIComponent(q)}`);
  }

  addPossessore(partitaId: number, payload: object) {
    return this.http.post<{ ok: boolean }>(`/api/partite/${partitaId}/possessori`, payload);
  }

  removePossessore(partitaId: number, possessoreId: number) {
    return this.http.delete<void>(`/api/partite/${partitaId}/possessori/${possessoreId}`);
  }

  addImmobile(partitaId: number, payload: object) {
    return this.http.post<{ id: number }>(`/api/partite/${partitaId}/immobili`, payload);
  }

  removeImmobile(partitaId: number, immobileId: number) {
    return this.http.delete<void>(`/api/partite/${partitaId}/immobili/${immobileId}`);
  }

  addVariazione(partitaId: number, payload: object) {
    return this.http.post<{ id: number }>(`/api/partite/${partitaId}/variazioni`, payload);
  }

  removeVariazione(partitaId: number, variazioneId: number) {
    return this.http.delete<void>(`/api/partite/${partitaId}/variazioni/${variazioneId}`);
  }

  patchPartita(id: number, payload: object) {
    return this.http.patch<{ ok: boolean }>(`/api/partite/${id}`, payload);
  }

  getComuni() {
    return this.http.get<{ id: number; nome: string; provincia: string }[]>('/api/comuni');
  }
}
