import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ChatStateService } from '../../core/chat-state.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <header>
      <div class="header-left">
        <h1>{{ title }}</h1>
        <nav>
          <a routerLink="/chat" routerLinkActive="active">Chat</a>
          <a routerLink="/drafts" routerLinkActive="active">Drafts</a>
        </nav>
      </div>
      <div class="header-right">
        <span class="user" [title]="fullUserLabel()">{{ shortUserLabel() }}</span>
        <button class="link" type="button" (click)="logout()">Logout</button>
      </div>
    </header>
  `,
  styles: [`
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 0.6rem 1rem;
      border-bottom: 1px solid #1e293b;
      flex-shrink: 0;
      min-width: 0;
      background: #0f172a;
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

    nav {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    nav a {
      color: #94a3b8;
      text-decoration: none;
      white-space: nowrap;
      font-size: 0.9rem;
    }

    nav a:hover,
    nav a.active {
      color: #e2e8f0;
    }

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

    @media (max-width: 640px) {
      header {
        padding: 0.5rem 0.75rem;
        flex-wrap: wrap;
      }
      .header-right {
        max-width: 100%;
      }
      h1 {
        font-size: 1rem;
      }
      .user {
        font-size: 0.75rem;
        max-width: 120px;
      }
    }
  `]
})
export class HeaderComponent {
  @Input() title = 'Assistant';

  constructor(
    public auth: AuthService,
    private chat: ChatStateService,
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

  logout() {
    this.chat.clear();
    this.auth.logout();
  }
}
