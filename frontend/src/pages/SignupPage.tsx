import { AuthPage } from "./AuthPage";

export function SignupPage() {
  return (
    <AuthPage
      mode="signup"
      eyebrow="Create Access"
      title="Open your Airzone account and start tracking flights."
      actionLabel="Create account"
      alternateLabel="Already signed up?"
      alternatePath="/login"
      alternateAction="Log in"
      summary="Your account is the gatekeeper for the search tools in this local build, with secure cookie sessions and password handling handled by the FastAPI backend."
    />
  );
}

