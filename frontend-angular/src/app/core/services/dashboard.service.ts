import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { DashboardStats, AnalyticsData } from '../models';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private http = inject(HttpClient);

  getStats() {
    return this.http.get<DashboardStats>('/api/dashboard/stats');
  }

  getAnalytics() {
    return this.http.get<AnalyticsData>('/api/dashboard/analytics');
  }
}
