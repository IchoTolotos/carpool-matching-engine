import { edgeKey } from "./assignment.js";
import type { DriverContext } from "./candidates.js";
import type { GuardedRoutingProvider } from "./routing-cache.js";
import type { MatchingProblem, Passenger, RouteEvaluation } from "./types.js";

export type InternalRoutePlan = Readonly<{
  assignedPassengerIds: readonly string[];
  context: DriverContext;
  detourSeconds: number;
  route: RouteEvaluation;
}>;

async function evaluateDriverRoute(input: {
  assignedPassengerIds: readonly string[];
  context: DriverContext;
  destination: MatchingProblem["destination"];
  passengerById: ReadonlyMap<string, Passenger>;
  routing: GuardedRoutingProvider;
}): Promise<InternalRoutePlan> {
  const passengerIds = [...input.assignedPassengerIds].sort();
  const route = await input.routing.route({
    destination: input.destination,
    origin: input.context.driver.origin,
    stops: passengerIds.map((passengerId) => {
      const passenger = input.passengerById.get(passengerId);
      if (!passenger) {
        throw new Error(`Missing passenger ${passengerId} while evaluating a route.`);
      }
      return { coordinate: passenger.origin, id: passenger.id };
    }),
  });
  return {
    assignedPassengerIds: passengerIds,
    context: input.context,
    detourSeconds: Math.max(0, route.durationSeconds - input.context.baseline.durationSeconds),
    route,
  };
}

export async function buildRoutePlans(input: {
  assignments: ReadonlyMap<string, string>;
  contexts: ReadonlyMap<string, DriverContext>;
  destination: MatchingProblem["destination"];
  passengerById: ReadonlyMap<string, Passenger>;
  routing: GuardedRoutingProvider;
}): Promise<Map<string, InternalRoutePlan>> {
  const passengerIdsByDriverId = new Map<string, string[]>();
  for (const [passengerId, driverId] of input.assignments) {
    const existing = passengerIdsByDriverId.get(driverId) ?? [];
    existing.push(passengerId);
    passengerIdsByDriverId.set(driverId, existing);
  }
  const plans = await Promise.all(
    [...input.contexts.values()].map(async (context) =>
      evaluateDriverRoute({
        assignedPassengerIds: passengerIdsByDriverId.get(context.driver.id) ?? [],
        context,
        destination: input.destination,
        passengerById: input.passengerById,
        routing: input.routing,
      }),
    ),
  );
  return new Map(plans.map((plan) => [plan.context.driver.id, plan]));
}

export async function chooseEdgesToBlacklist(input: {
  destination: MatchingProblem["destination"];
  passengerById: ReadonlyMap<string, Passenger>;
  plans: readonly InternalRoutePlan[];
  routing: GuardedRoutingProvider;
}): Promise<string[]> {
  const selectedEdges: string[] = [];
  for (const plan of input.plans) {
    const pinnedIds = new Set(plan.context.pinnedPassengerIds);
    const removablePassengerIds = plan.assignedPassengerIds.filter(
      (passengerId) => !pinnedIds.has(passengerId),
    );
    let bestPassengerId: string | null = null;
    let bestGainSeconds = Number.NEGATIVE_INFINITY;

    for (const passengerId of removablePassengerIds) {
      const routeWithoutPassenger = await evaluateDriverRoute({
        assignedPassengerIds: plan.assignedPassengerIds.filter((id) => id !== passengerId),
        context: plan.context,
        destination: input.destination,
        passengerById: input.passengerById,
        routing: input.routing,
      });
      const gainSeconds = plan.route.durationSeconds - routeWithoutPassenger.route.durationSeconds;
      if (
        gainSeconds > bestGainSeconds ||
        (gainSeconds === bestGainSeconds &&
          passengerId.localeCompare(bestPassengerId ?? passengerId) < 0)
      ) {
        bestGainSeconds = gainSeconds;
        bestPassengerId = passengerId;
      }
    }
    if (bestPassengerId) {
      selectedEdges.push(edgeKey(bestPassengerId, plan.context.driver.id));
    }
  }
  return selectedEdges;
}
