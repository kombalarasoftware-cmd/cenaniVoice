import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Server-side auth guard middleware.
 * Protects /dashboard routes by checking for access_token cookie.
 * Falls back to checking Authorization header for API-like access.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public routes
  if (
    pathname.startsWith('/login') ||
    pathname.startsWith('/register') ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next();
  }

  // Check for token in cookie (preferred) or Authorization header
  const tokenCookie = request.cookies.get('access_token')?.value;
  const tokenHeader = request.headers.get('authorization')?.replace('Bearer ', '');
  const token = tokenCookie || tokenHeader;

  // Protected routes: redirect unauthenticated users to login
  if (pathname.startsWith('/dashboard') || pathname === '/') {
    if (!token) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Basic JWT expiry check (no signature verification on edge, that's backend's job)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp && payload.exp * 1000 < Date.now()) {
        const loginUrl = new URL('/login', request.url);
        loginUrl.searchParams.set('expired', '1');
        return NextResponse.redirect(loginUrl);
      }
    } catch {
      // Malformed token — redirect to login
      const loginUrl = new URL('/login', request.url);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Add security headers to all responses
  const response = NextResponse.next();
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all paths except static files and images
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
