import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface ChatResponse {
  reply: string;
  tool_results: any[];
}

export interface Draft {
  draft_id: string;
  customer_id: string;
  customer_name: string;
  customer_email: string;
  subject: string;
  body: string;
  status: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  health() {
    return this.http.get<{ status: string }>(`${environment.apiUrl}/health`);
  }

  chat(message: string) {
    return this.http.post<ChatResponse>(`${environment.apiUrl}/assistant/chat`, { message });
  }

  listDrafts(status?: string) {
    const params: any = {};
    if (status) params.status = status;
    return this.http.get<Draft[]>(`${environment.apiUrl}/drafts`, { params });
  }

  approveDraft(id: string) {
    return this.http.post(`${environment.apiUrl}/drafts/${id}/approve`, {});
  }

  rejectDraft(id: string) {
    return this.http.post(`${environment.apiUrl}/drafts/${id}/reject`, {});
  }

  sendDraft(id: string, idempotencyKey: string) {
    return this.http.post(`${environment.apiUrl}/drafts/${id}/send`, {
      idempotency_key: idempotencyKey,
    });
  }
}
