import type { CandidateEdge } from "./candidates.js";
import type { InternalRoutePlan } from "./route-plans.js";
import type { MatchedRoute, MatchingResult, Passenger, PassengerAssignment } from "./types.js";

function findCandidateEdge(
  candidates: ReadonlyMap<string, readonly CandidateEdge[]>,
  passengerId: string,
  driverId: string,
): CandidateEdge | undefined {
  return candidates.get(passengerId)?.find((edge) => edge.driverId === driverId);
}

export function buildPublicResult(input: {
  assignments: ReadonlyMap<string, string>;
  blacklistedEdges: ReadonlySet<string>;
  candidates: ReadonlyMap<string, readonly CandidateEdge[]>;
  passengers: readonly Passenger[];
  plans: ReadonlyMap<string, InternalRoutePlan>;
  repairRounds: number;
  routingCallCount: number;
}): MatchingResult {
  const passengerById = new Map(input.passengers.map((passenger) => [passenger.id, passenger]));
  const assignments: PassengerAssignment[] = [...input.assignments]
    .map(([passengerId, driverId]) => {
      const passenger = passengerById.get(passengerId) as Passenger;
      const pinned = passenger.pinnedDriverId !== null;
      const candidate = pinned
        ? undefined
        : findCandidateEdge(input.candidates, passengerId, driverId);
      return {
        driverId,
        estimatedAddedSeconds: candidate?.estimatedAddedSeconds ?? null,
        passengerId,
        pickupDistanceKm: candidate?.pickupDistanceKm ?? null,
        pinned,
      };
    })
    .sort((left, right) => left.passengerId.localeCompare(right.passengerId));
  const routes: MatchedRoute[] = [...input.plans.values()]
    .map((plan) => ({
      baselineDurationSeconds: plan.context.baseline.durationSeconds,
      detourSeconds: plan.detourSeconds,
      driverId: plan.context.driver.id,
      durationSeconds: plan.route.durationSeconds,
      geometry: plan.route.geometry,
      orderedPassengerIds: plan.route.orderedStopIds,
      passengerIds: plan.assignedPassengerIds,
    }))
    .sort((left, right) => left.driverId.localeCompare(right.driverId));
  const candidateEdgeCount = [...input.candidates.values()].reduce(
    (sum, edges) => sum + edges.length,
    0,
  );
  return {
    assignments,
    diagnostics: {
      blacklistedEdgeCount: input.blacklistedEdges.size,
      candidateEdgeCount,
      repairRounds: input.repairRounds,
      routingCallCount: input.routingCallCount,
    },
    routes,
    unassignedPassengerIds: input.passengers
      .filter((passenger) => !input.assignments.has(passenger.id))
      .map((passenger) => passenger.id)
      .sort(),
  };
}
