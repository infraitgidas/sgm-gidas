export type AccessState =
  | "loading"
  | "error"
  | "first-admin"
  | "authenticated"
  | "login";

type LandingAccessStateInput = {
  sessionLoading: boolean;
  userExists: boolean;
  setupError: boolean;
  needsInitialAdmin: boolean | undefined;
};

export function getLandingAccessState({
  sessionLoading,
  userExists,
  setupError,
  needsInitialAdmin,
}: LandingAccessStateInput): AccessState {
  if (sessionLoading) return "loading";
  if (userExists) return "authenticated";
  if (needsInitialAdmin === true) return "first-admin";
  if (needsInitialAdmin === false) return "login";
  if (setupError) return "error";
  return "loading";
}
