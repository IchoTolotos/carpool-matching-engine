import { projectPointOntoPolyline } from "./geometry.js";
import type { Driver, MatchingProblem, Passenger, RouteEvaluation } from "./types.js";
import { groupsAreCompatible } from "./validation.js";

export type DriverContext = Readonly<{
  baseline: RouteEvaluation;
  cumulativeDurationSeconds: readonly number[];
  driver: Driver;
  pinnedPassengerIds: readonly string[];
  seatsRemaining: number;
}>;

export type CandidateEdge = Readonly<{
  cost: number;
  driverId: string;
  estimatedAddedSeconds: number;
  passengerId: string;
  pickupDistanceKm: number;
  projectionProgress: number;
}>;

function remainingBaselineSeconds(
  context: DriverContext,
  segmentIndex: number,
  segmentFraction: number,
): number {
  const segmentStart = context.cumulativeDurationSeconds[segmentIndex] ?? 0;
  const segmentDuration = context.baseline.segmentDurationSeconds[segmentIndex] ?? 0;
  const projectedElapsed = segmentStart + segmentDuration * segmentFraction;
  return Math.max(0, context.baseline.durationSeconds - projectedElapsed);
}

function candidateCost(edge: Omit<CandidateEdge, "cost">): number {
  return Math.round(
    edge.estimatedAddedSeconds * 1_000 + edge.pickupDistanceKm * 100 + edge.projectionProgress * 10,
  );
}

function compareCandidates(left: CandidateEdge, right: CandidateEdge): number {
  return (
    left.cost - right.cost ||
    left.driverId.localeCompare(right.driverId) ||
    left.passengerId.localeCompare(right.passengerId)
  );
}

export function buildCandidateEdges(input: {
  contexts: ReadonlyMap<string, DriverContext>;
  directDurationByPassengerId: ReadonlyMap<string, number>;
  passengers: readonly Passenger[];
  problem: MatchingProblem;
}): Map<string, CandidateEdge[]> {
  const result = new Map<string, CandidateEdge[]>();

  for (const passenger of input.passengers) {
    const directDuration = input.directDurationByPassengerId.get(passenger.id);
    if (directDuration === undefined) {
      throw new Error(`Missing direct duration for passenger ${passenger.id}.`);
    }
    const edges: CandidateEdge[] = [];
    for (const context of input.contexts.values()) {
      if (
        context.seatsRemaining <= 0 ||
        !groupsAreCompatible(context.driver.groupId, passenger.groupId, input.problem.groupPolicy)
      ) {
        continue;
      }
      const projection = projectPointOntoPolyline(passenger.origin, context.baseline.geometry);
      const estimatedAddedSeconds = Math.max(
        0,
        directDuration -
          remainingBaselineSeconds(context, projection.segmentIndex, projection.segmentFraction),
      );
      if (
        input.problem.mode.kind === "natural-carpool" &&
        (projection.distanceKm > input.problem.mode.maxPickupDistanceKm ||
          estimatedAddedSeconds > input.problem.mode.maxDetourSeconds)
      ) {
        continue;
      }
      const edgeWithoutCost = {
        driverId: context.driver.id,
        estimatedAddedSeconds,
        passengerId: passenger.id,
        pickupDistanceKm: projection.distanceKm,
        projectionProgress: projection.progress,
      };
      edges.push({ ...edgeWithoutCost, cost: candidateCost(edgeWithoutCost) });
    }
    result.set(passenger.id, edges.sort(compareCandidates));
  }
  return result;
}
