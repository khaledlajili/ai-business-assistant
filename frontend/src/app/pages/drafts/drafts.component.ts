import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, Draft } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { ChatStateService } from '../../core/chat-state.service';

@Component({
  selector: 'app-drafts',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="layout">
      <header>
        <h1>Email Drafts</h1>
        <nav>
          <a routerLink="/chat">Chat</a>
          <a routerLink="/drafts">Drafts</a>
          <span class="user" [title]="auth.currentUser()?.full_name">
            {{ shortName() }} ({{ auth.currentUser()?.role }})
          </span>
          <button class="link" (click)="logout()">Logout</button>
        </nav>
      </header>

      <div class="filters">
        <button [class.active]="filter()==='pending_review'" (click)="load('pending_review')">Pending</button>
        <button [class.active]="filter()==='approved'" (click)="load('approved')">Approved</button>
        <button [class.active]="filter()==='sent'" (click)="load('sent')">Sent</button>
        <button [class.active]="filter()==='failed'" (click)="load('failed')">Failed</button>
      </div>

      <div class="list">
        <div class="card" *ngFor="let d of drafts()">
          <div class="meta">
            <strong>{{ d.customer_name }}</strong>
            <span class="status">{{ d.status }}</span>
          </div>
          <div class="subject">{{ d.subject }}</div>
          <pre class="body">{{ d.body }}</pre>
          <div class="actions" *ngIf="d.status === 'pending_review' && canApprove()">
            <button (click)="approve(d)">Approve</button>
            <button class="danger" (click)="reject(d)">Reject</button>
          </div>
          <div class="actions" *ngIf="d.status === 'approved' && canSend()">
            <button (click)="send(d)">Send</button>
          </div>
        </div>
        <p *ngIf="!drafts().length" class="empty">No drafts in this status.</p>
      </div>
    </div>
  `,
  styles: [`
    .layout { min-height: 100vh; background: #0f172a; color: #e2e8f0; overflow-x: hidden; }
    header {
      display: flex; justify-content: space-between; align-items: center;
      padding: .6rem 1rem; border-bottom: 1px solid #1e293b; gap: .75rem; flex-wrap: wrap;
    }
    h1 { margin: 0; font-size: 1.05rem; white-space: nowrap; }
    nav { display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; min-width: 0; }
    nav a { color: #94a3b8; text-decoration: none; white-space: nowrap; font-size: .9rem; }
    .user {
      color: #64748b; font-size: .8rem; max-width: 140px;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .link { background: none; border: none; color: #f87171; cursor: pointer; white-space: nowrap; }
    .filters { padding: 1rem; display: flex; gap: .5rem; flex-wrap: wrap; }
    .filters button {
      background: #1e293b; border: 1px solid #334155; color: #94a3b8;
      padding: .4rem .8rem; border-radius: 6px; cursor: pointer;
    }
    .filters button.active { background: #3b82f6; color: white; border-color: #3b82f6; }
    .list { padding: 0 1rem 2rem; display: grid; gap: 1rem; }
    .card { background: #1e293b; border-radius: 10px; padding: 1rem; overflow: hidden; }
    .meta { display: flex; justify-content: space-between; margin-bottom: .4rem; gap: .5rem; }
    .status { font-size: .8rem; color: #94a3b8; text-transform: uppercase; white-space: nowrap; }
    .subject { font-weight: 600; margin-bottom: .5rem; word-break: break-word; }
    .body {
      background: #0f172a; padding: .75rem; border-radius: 6px;
      white-space: pre-wrap; font-size: .85rem; max-height: 120px; overflow: auto;
    }
    .actions { margin-top: .75rem; display: flex; gap: .5rem; flex-wrap: wrap; }
    .actions button {
      padding: .4rem .9rem; border: none; border-radius: 6px;
      background: #22c55e; color: white; cursor: pointer;
    }
    .actions button.danger { background: #ef4444; }
    .empty { color: #64748b; text-align: center; margin-top: 2rem; }
  `]
})
export class DraftsComponent implements OnInit {
  drafts = signal<Draft[]>([]);
  filter = signal('pending_review');

  constructor(
    public auth: AuthService,
    private api: ApiService,
    private chat: ChatStateService,
  ) {}

  ngOnInit() {
    this.load('pending_review');
  }

  shortName(): string {
    const n = this.auth.currentUser()?.full_name || '';
    return n.length > 18 ? n.slice(0, 16) + '…' : n;
  }

  canApprove() {
    return this.auth.currentUser()?.role === 'manager';
  }

  canSend() {
    return this.auth.currentUser()?.role === 'manager';
  }

  load(status: string) {
    this.filter.set(status);
    this.api.listDrafts(status).subscribe({
      next: (list) => this.drafts.set(list),
      error: () => this.drafts.set([]),
    });
  }

  approve(d: Draft) {
    this.api.approveDraft(d.draft_id).subscribe(() => this.load(this.filter()));
  }

  reject(d: Draft) {
    this.api.rejectDraft(d.draft_id).subscribe(() => this.load(this.filter()));
  }

  send(d: Draft) {
    const key = `ui-${d.draft_id}-${Date.now()}`;
    this.api.sendDraft(d.draft_id, key).subscribe(() => this.load('sent'));
  }

  logout() {
    this.chat.clear();
    this.auth.logout();
  }
}
