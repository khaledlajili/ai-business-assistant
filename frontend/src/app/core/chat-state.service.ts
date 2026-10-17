import { Injectable, signal } from '@angular/core';

export interface Message {
  role: 'user' | 'assistant';
  text: string;
  html?: string;
  toolResults?: any[];
}

@Injectable({ providedIn: 'root' })
export class ChatStateService {
  messages = signal<Message[]>([]);

  add(msg: Message) {
    this.messages.update((m) => [...m, msg]);
  }

  clear() {
    this.messages.set([]);
  }
}
