export function isGoogleAuthConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);
}

export function signInWithGoogle(): void {
  if (!isGoogleAuthConfigured()) {
    return;
  }

  window.location.href = `/api/auth/google?redirect=${encodeURIComponent(window.location.href)}`;
}
