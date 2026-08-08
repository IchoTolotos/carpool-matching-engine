export type MatchingEngineErrorCode =
  | "CAPACITY_EXCEEDED_BY_PINNED_PASSENGERS"
  | "DETOUR_CONSTRAINT_UNSATISFIED"
  | "DUPLICATE_ID"
  | "FULL_COVERAGE_IMPOSSIBLE"
  | "INVALID_INPUT"
  | "INVALID_ROUTING_RESPONSE"
  | "PINNED_DRIVER_NOT_FOUND"
  | "ROUTING_CALL_LIMIT_EXCEEDED";

export class MatchingEngineError extends Error {
  readonly code: MatchingEngineErrorCode;
  readonly details: Readonly<Record<string, unknown>>;

  constructor(
    code: MatchingEngineErrorCode,
    message: string,
    details: Readonly<Record<string, unknown>> = {},
  ) {
    super(message);
    this.name = "MatchingEngineError";
    this.code = code;
    this.details = details;
  }
}
