import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Draft } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { HeaderComponent } from '../../shared/header/header.component';

@Component({
  selector: 'app-drafts',
  standalone: true,
  imports: [CommonModule, HeaderComponent],
  template: `
    <div class="layout">
      <app-header title="Email Drafts"></app-header>

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
  `
})
export class DraftsComponent implements OnInit {
  drafts = signal<Draft[]>([]);
  filter = signal('pending_review');

  constructor(
    public auth: AuthService,
    private api: ApiService,
  ) {}

  ngOnInit() {
    this.load('pending_review');
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
}
