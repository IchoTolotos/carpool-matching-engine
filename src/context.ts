import type { DriverContext } from "./candidates.js";
import type { GuardedRoutingProvider } from "./routing-cache.js";
import type { MatchingProblem, Passenger, RouteEvaluation } from "./types.js";

function cumulativeDurations(route: RouteEvaluation): number[] {
  const cumulative = [0];
  for (const duration of route.segmentDurationSeconds) {
    cumulative.push((cumulative.at(-1) ?? 0) + duration);
  }
  return cumulative;
}

function passengersByDriver(passengers: readonly Passenger[]): Map<string, Passenger[]> {
  const result = new Map<string, Passenger[]>();
  for (const passenger of passengers) {
    if (!passenger.pinnedDriverId) {
      continue;
    }
    const existing = result.get(passenger.pinnedDriverId) ?? [];
    existing.push(passenger);
    result.set(passenger.pinnedDriverId, existing);
  }
  for (const pinnedPassengers of result.values()) {
    pinnedPassengers.sort((left, right) => left.id.localeCompare(right.id));
  }
  return result;
}

export async function buildDriverContexts(input: {
  problem: MatchingProblem;
  routing: GuardedRoutingProvider;
}): Promise<Map<string, DriverContext>> {
  const pinnedByDriver = passengersByDriver(input.problem.passengers);
  const contexts = await Promise.all(
    [...input.problem.drivers]
      .sort((left, right) => left.id.localeCompare(right.id))
      .map(async (driver) => {
        const pinnedPassengers = pinnedByDriver.get(driver.id) ?? [];
        const baseline = await input.routing.route({
          destination: input.problem.destination,
          origin: driver.origin,
          stops: pinnedPassengers.map((passenger) => ({
            coordinate: passenger.origin,
            id: passenger.id,
          })),
        });
        return {
          baseline,
          cumulativeDurationSeconds: cumulativeDurations(baseline),
          driver,
          pinnedPassengerIds: pinnedPassengers.map((passenger) => passenger.id),
          seatsRemaining: driver.capacity - pinnedPassengers.length,
        } satisfies DriverContext;
      }),
  );
  return new Map(contexts.map((context) => [context.driver.id, context]));
}

export async function buildDirectDurationTable(input: {
  destination: MatchingProblem["destination"];
  passengers: readonly Passenger[];
  routing: GuardedRoutingProvider;
}): Promise<Map<string, number>> {
  const rows = await Promise.all(
    [...input.passengers]
      .sort((left, right) => left.id.localeCompare(right.id))
      .map(async (passenger) => {
        const route = await input.routing.route({
          destination: input.destination,
          origin: passenger.origin,
          stops: [],
        });
        return [passenger.id, route.durationSeconds] as const;
      }),
  );
  return new Map(rows);
}
