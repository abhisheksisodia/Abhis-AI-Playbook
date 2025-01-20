import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const authPages = ['/auth/login', '/auth/register'];
  const isAuthPage = authPages.includes(request.nextUrl.pathname);
  const token = request.cookies.get('auth-token');

  if (isAuthPage && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  if (!isAuthPage && !token) {
    return NextResponse.redirect(new URL('/auth/login', request.url));
  }
}

export const config = {
  matcher: ['/dashboard/:path*', '/auth/:path*'],
}; 