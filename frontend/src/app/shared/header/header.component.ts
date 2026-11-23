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
  `
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
