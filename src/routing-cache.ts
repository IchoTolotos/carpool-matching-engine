import { MatchingEngineError } from "./errors.js";
import type { RouteEvaluation, RouteRequest, RoutingProvider } from "./types.js";
import { validateRouteEvaluation } from "./validation.js";

function routeCacheKey(request: RouteRequest): string {
  return JSON.stringify({
    destination: request.destination,
    origin: request.origin,
    stops: request.stops,
  });
}

export class GuardedRoutingProvider {
  private readonly cache = new Map<string, Promise<RouteEvaluation>>();
  private calls = 0;

  constructor(
    private readonly provider: RoutingProvider,
    private readonly maximumCalls: number,
  ) {}

  get callCount(): number {
    return this.calls;
  }

  async route(request: RouteRequest): Promise<RouteEvaluation> {
    const key = routeCacheKey(request);
    const cached = this.cache.get(key);
    if (cached) {
      return await cached;
    }
    if (this.calls >= this.maximumCalls) {
      throw new MatchingEngineError(
        "ROUTING_CALL_LIMIT_EXCEEDED",
        `Matching requires more than the configured ${this.maximumCalls} routing calls.`,
        { maximumCalls: this.maximumCalls },
      );
    }
    this.calls += 1;
    const pending = this.provider.route(request).then((evaluation) => {
      validateRouteEvaluation(request, evaluation);
      return evaluation;
    });
    this.cache.set(key, pending);
    return await pending;
  }
}
