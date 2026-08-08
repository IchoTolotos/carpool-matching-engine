import { MatchingEngineError } from "../errors.js";
import { haversineDistanceKm } from "../geometry.js";
import type {
  Coordinate,
  RouteEvaluation,
  RouteRequest,
  RouteStop,
  RoutingProvider,
} from "../types.js";

export type StraightLineRoutingOptions = Readonly<{
  speedKilometersPerHour: number;
  stopPenaltySeconds: number;
}>;

function permutations<T>(values: readonly T[]): T[][] {
  if (values.length <= 1) {
    return [[...values]];
  }
  const result: T[][] = [];
  for (const [index, value] of values.entries()) {
    const remaining = values.filter((_, candidateIndex) => candidateIndex !== index);
    for (const suffix of permutations(remaining)) {
      result.push([value as T, ...suffix]);
    }
  }
  return result;
}

function compareStopOrders(left: readonly RouteStop[], right: readonly RouteStop[]): number {
  return left
    .map((stop) => stop.id)
    .join("\u0000")
    .localeCompare(right.map((stop) => stop.id).join("\u0000"));
}

export class StraightLineRoutingProvider implements RoutingProvider {
  constructor(private readonly options: StraightLineRoutingOptions) {
    if (
      !Number.isFinite(options.speedKilometersPerHour) ||
      options.speedKilometersPerHour <= 0 ||
      !Number.isFinite(options.stopPenaltySeconds) ||
      options.stopPenaltySeconds < 0
    ) {
      throw new MatchingEngineError(
        "INVALID_INPUT",
        "Straight-line routing options must use a positive speed and non-negative stop penalty.",
      );
    }
  }

  async route(request: RouteRequest): Promise<RouteEvaluation> {
    if (request.stops.length > 8) {
      throw new MatchingEngineError(
        "INVALID_INPUT",
        "The simulation provider supports at most eight stops because it evaluates every permutation.",
        { stopCount: request.stops.length },
      );
    }
    const orderedStops = this.chooseStopOrder(request);
    const geometry: Coordinate[] = [
      request.origin,
      ...orderedStops.map((stop) => stop.coordinate),
      request.destination,
    ];
    const segmentDurationSeconds = geometry.slice(0, -1).map((coordinate, index) => {
      const distanceKm = haversineDistanceKm(coordinate, geometry[index + 1] as Coordinate);
      const travelSeconds = (distanceKm / this.options.speedKilometersPerHour) * 3_600;
      const isStopArrival = index < orderedStops.length;
      return travelSeconds + (isStopArrival ? this.options.stopPenaltySeconds : 0);
    });
    return {
      durationSeconds: segmentDurationSeconds.reduce((sum, duration) => sum + duration, 0),
      geometry,
      orderedStopIds: orderedStops.map((stop) => stop.id),
      segmentDurationSeconds,
    };
  }

  private chooseStopOrder(request: RouteRequest): RouteStop[] {
    let bestOrder: RouteStop[] | null = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    for (const order of permutations(request.stops)) {
      const points = [request.origin, ...order.map((stop) => stop.coordinate), request.destination];
      const distance = points
        .slice(0, -1)
        .reduce(
          (sum, coordinate, index) =>
            sum + haversineDistanceKm(coordinate, points[index + 1] as Coordinate),
          0,
        );
      if (
        distance < bestDistance ||
        (distance === bestDistance && bestOrder && compareStopOrders(order, bestOrder) < 0)
      ) {
        bestDistance = distance;
        bestOrder = order;
      }
    }
    return bestOrder ?? [];
  }
}
