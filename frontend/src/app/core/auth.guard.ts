import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, map, take } from 'rxjs';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const decide = () =>
    auth.isLoggedIn() ? true : router.createUrlTree(['/login']);

  if (auth.ready()) {
    return decide();
  }

  return toObservable(auth.ready).pipe(
    filter((v) => v === true),
    take(1),
    map(() => decide()),
  );
};
