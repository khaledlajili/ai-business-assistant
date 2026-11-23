import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { marked } from 'marked';
import { ApiService, ChatResponse } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { ChatStateService } from '../../core/chat-state.service';
import { HeaderComponent } from '../../shared/header/header.component';

interface QueryPreset {
  label: string;
  text: string;
  roles: string[];
}

const ALL_PRESETS: QueryPreset[] = [
  {
    label: 'High-value inactive customers',
    text: 'Which high-value customers spent more than 500 DT last month but have not ordered this month?',
    roles: ['viewer', 'manager', 'sales_rep'],
  },
  {
    label: 'Sales – previous month',
    text: 'What were total sales in the previous month?',
    roles: ['viewer', 'manager', 'sales_rep'],
  },
  {
    label: 'Sales – current month',
    text: 'What are total sales so far this month?',
    roles: ['viewer', 'manager', 'sales_rep'],
  },
  {
    label: 'Search customer Ahmed',
    text: 'Search for customers named Ahmed',
    roles: ['viewer', 'manager', 'sales_rep'],
  },
  {
    label: 'List pending drafts',
    text: 'Show pending email drafts',
    roles: ['viewer', 'manager', 'sales_rep'],
  },
  {
    label: 'Create follow-up draft',
    text: 'Create a follow-up email draft for customer e0000000-0000-0000-0000-000000000002 with subject We miss you and a short polite body',
    roles: ['manager', 'sales_rep'],
  },
];

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  template: `
    <div class="layout">
      <app-header title="Assistant"></app-header>

      <div class="messages">
        <div *ngFor="let m of chat.messages()" [class]="'msg ' + m.role">
          <div class="bubble user-bubble" *ngIf="m.role === 'user'">{{ m.text }}</div>
          <div class="bubble md" *ngIf="m.role === 'assistant'" [innerHTML]="m.html"></div>
          <div class="tools" *ngIf="m.toolResults?.length">
            <details>
              <summary>Tool results ({{ m.toolResults!.length }})</summary>
              <pre>{{ m.toolResults | json }}</pre>
            </details>
          </div>
        </div>
      </div>

      <form class="input-bar" (ngSubmit)="send()">
        <input
          [(ngModel)]="input"
          name="msg"
          placeholder="Ask about customers, sales, drafts…"
          [disabled]="busy()"
        />
        <button type="submit" [disabled]="busy() || !input.trim()">Send</button>
      </form>

      <div class="presets">
        <p class="presets-title">Available for {{ auth.currentUser()?.role }}:</p>
        <button type="button" *ngFor="let p of visiblePresets()" (click)="preset(p.text)">
          {{ p.label }}
        </button>
      </div>
    </div>
  `
})
export class ChatComponent {
  input = '';
  busy = signal(false);

  visiblePresets = computed(() => {
    const role = this.auth.currentUser()?.role || 'viewer';
    return ALL_PRESETS.filter((p) => p.roles.includes(role));
  });

  constructor(
    public auth: AuthService,
    public chat: ChatStateService,
    private api: ApiService,
  ) {}

  preset(text: string) {
    this.input = text;
  }

  send() {
    const text = this.input.trim();
    if (!text || this.busy()) return;

    this.chat.add({ role: 'user', text });
    this.input = '';
    this.busy.set(true);

    this.api.chat(text).subscribe({
      next: (res: ChatResponse) => {
        const html = marked.parse(res.reply || '', { async: false }) as string;
        this.chat.add({
          role: 'assistant',
          text: res.reply,
          html,
          toolResults: res.tool_results,
        });
        this.busy.set(false);
      },
      error: (err) => {
        const msg = err.error?.detail || 'Error talking to the assistant.';
        this.chat.add({ role: 'assistant', text: msg, html: msg });
        this.busy.set(false);
      },
    });
  }
}
