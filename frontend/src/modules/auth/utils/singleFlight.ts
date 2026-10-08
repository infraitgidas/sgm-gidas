export function createSingleFlight<TArgs extends unknown[], TResult>(
  operation: (...args: TArgs) => Promise<TResult>
) {
  let active: Promise<TResult> | null = null;

  return (...args: TArgs): Promise<TResult> => {
    if (active) return active;

    active = operation(...args).finally(() => {
      active = null;
    });
    return active;
  };
}
