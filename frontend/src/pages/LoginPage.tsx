import { AuthPage } from "./AuthPage";

export function LoginPage() {
  return (
    <AuthPage
      mode="login"
      eyebrow="Local Flight Console"
      title="Sign in to your live aircraft search workspace."
      actionLabel="Log in"
      alternateLabel="Need an account?"
      alternatePath="/signup"
      alternateAction="Create one"
      summary="Airzone keeps the first release tight and local: authenticated access, focused search flows, and a clean path to production-grade aviation data later."
    />
  );
}

