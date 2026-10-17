import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { marked } from 'marked';
import { ApiService, ChatResponse } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { ChatStateService } from '../../core/chat-state.service';

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
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="layout">
      <header>
        <div class="header-left">
          <h1>Assistant</h1>
          <a routerLink="/chat">Chat</a>
          <a routerLink="/drafts">Drafts</a>
        </div>
        <div class="header-right">
          <span class="user" [title]="fullUserLabel()">{{ shortUserLabel() }}</span>
          <button class="link" type="button" (click)="logout()">Logout</button>
        </div>
      </header>

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
  `,
  styles: [`
    .layout {
      display: flex;
      flex-direction: column;
      height: 100vh;
      max-width: 100vw;
      background: #0f172a;
      color: #e2e8f0;
      overflow: hidden;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 0.6rem 1rem;
      border-bottom: 1px solid #1e293b;
      flex-shrink: 0;
      min-width: 0;
    }

    .header-left, .header-right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      min-width: 0;
    }

    .header-left {
      flex: 1 1 auto;
      overflow: hidden;
    }

    .header-right {
      flex: 0 1 auto;
      max-width: 55%;
    }

    h1 {
      margin: 0;
      font-size: 1.05rem;
      white-space: nowrap;
    }

    .header-left a {
      color: #94a3b8;
      text-decoration: none;
      white-space: nowrap;
      font-size: 0.9rem;
    }
    .header-left a:hover { color: #e2e8f0; }

    .user {
      color: #64748b;
      font-size: 0.8rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-width: 0;
    }

    .link {
      background: none;
      border: none;
      color: #f87171;
      cursor: pointer;
      white-space: nowrap;
      font-size: 0.9rem;
      flex-shrink: 0;
    }

    .messages {
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 1rem;
      min-height: 0;
    }

    .msg {
      margin-bottom: 1rem;
      max-width: min(90%, 720px);
      min-width: 0;
    }
    .msg.user { margin-left: auto; }

    .bubble {
      padding: 0.75rem 1rem;
      border-radius: 10px;
      background: #1e293b;
      max-width: 100%;
      box-sizing: border-box;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .user-bubble {
      background: #1d4ed8;
      color: #ffffff;
      white-space: pre-wrap;
    }

    .bubble.md {
      color: #e2e8f0;
      white-space: normal;
      overflow-x: auto;
    }

    .bubble.md :is(p, ul, ol, li, h1, h2, h3) {
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .bubble.md table {
      border-collapse: collapse;
      font-size: 0.85rem;
      width: max-content;
      max-width: 100%;
      display: block;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }

    .bubble.md th,
    .bubble.md td {
      border: 1px solid #334155;
      padding: 0.35rem 0.6rem;
      text-align: left;
      white-space: nowrap;
    }

    .bubble.md th { background: #0f172a; }

    .bubble.md code {
      background: #0f172a;
      padding: 0.1rem 0.3rem;
      border-radius: 3px;
      font-size: 0.85em;
      word-break: break-all;
    }

    .tools {
      margin-top: 0.4rem;
      font-size: 0.8rem;
      max-width: 100%;
      min-width: 0;
    }

    pre {
      background: #020617;
      padding: 0.5rem;
      border-radius: 6px;
      overflow-x: auto;
      max-height: 200px;
      color: #94a3b8;
      max-width: 100%;
      box-sizing: border-box;
    }

    .input-bar {
      display: flex;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      border-top: 1px solid #1e293b;
      flex-shrink: 0;
    }

    .input-bar input {
      flex: 1;
      min-width: 0;
      padding: 0.65rem 0.9rem;
      border-radius: 8px;
      border: 1px solid #334155;
      background: #1e293b;
      color: #e2e8f0;
    }

    .input-bar button {
      padding: 0.65rem 1.2rem;
      border: none;
      border-radius: 8px;
      background: #3b82f6;
      color: white;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .presets {
      padding: 0 1rem 1rem;
      flex-shrink: 0;
    }

    .presets-title {
      margin: 0 0 0.5rem;
      font-size: 0.8rem;
      color: #64748b;
    }

    .presets button {
      background: #1e293b;
      border: 1px solid #334155;
      color: #94a3b8;
      padding: 0.35rem 0.7rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.8rem;
      margin: 0 0.4rem 0.4rem 0;
    }

    .presets button:hover {
      border-color: #3b82f6;
      color: #e2e8f0;
    }

    @media (max-width: 640px) {
      header { padding: 0.5rem 0.75rem; }
      .header-left a:not(:first-of-type) { /* keep Chat/Drafts */ }
      .header-right { max-width: 50%; }
      .msg { max-width: 100%; }
      .user { font-size: 0.75rem; }
    }
  `]
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

  fullUserLabel(): string {
    const u = this.auth.currentUser();
    return u ? `${u.full_name} (${u.role})` : '';
  }

  shortUserLabel(): string {
    const u = this.auth.currentUser();
    if (!u) return '';
    const name = u.full_name.length > 14 ? u.full_name.slice(0, 12) + '…' : u.full_name;
    return `${name} (${u.role})`;
  }

  preset(text: string) {
    this.input = text;
  }

  logout() {
    this.chat.clear();
    this.auth.logout();
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
