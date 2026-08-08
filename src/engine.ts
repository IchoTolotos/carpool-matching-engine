import { solveAssignments } from "./assignment.js";
import { buildCandidateEdges } from "./candidates.js";
import { buildDirectDurationTable, buildDriverContexts } from "./context.js";
import { MatchingEngineError } from "./errors.js";
import { buildPublicResult } from "./result.js";
import { buildRoutePlans, chooseEdgesToBlacklist } from "./route-plans.js";
import { GuardedRoutingProvider } from "./routing-cache.js";
import type { MatchingProblem, MatchingResult, Passenger, RoutingProvider } from "./types.js";
import { validateProblem } from "./validation.js";

function combineAssignments(input: {
  optionalAssignments: ReadonlyMap<string, string>;
  passengers: readonly Passenger[];
}): Map<string, string> {
  const result = new Map<string, string>();
  for (const passenger of input.passengers) {
    if (passenger.pinnedDriverId) {
      result.set(passenger.id, passenger.pinnedDriverId);
    }
  }
  for (const [passengerId, driverId] of input.optionalAssignments) {
    result.set(passengerId, driverId);
  }
  return result;
}

function assertFullCoverage(
  problem: MatchingProblem,
  assignments: ReadonlyMap<string, string>,
): void {
  if (problem.mode.kind !== "full-coverage" || assignments.size === problem.passengers.length) {
    return;
  }
  const unassignedPassengerIds = problem.passengers
    .filter((passenger) => !assignments.has(passenger.id))
    .map((passenger) => passenger.id)
    .sort();
  throw new MatchingEngineError(
    "FULL_COVERAGE_IMPOSSIBLE",
    `Full coverage could not assign ${unassignedPassengerIds.length} passenger(s).`,
    { unassignedPassengerIds },
  );
}

export async function matchCarpools(
  problem: MatchingProblem,
  routingProvider: RoutingProvider,
): Promise<MatchingResult> {
  validateProblem(problem);
  const routing = new GuardedRoutingProvider(routingProvider, problem.limits.maxRoutingCalls);
  const passengerById = new Map(problem.passengers.map((passenger) => [passenger.id, passenger]));
  const contexts = await buildDriverContexts({ problem, routing });
  const optionalPassengers = problem.passengers.filter(
    (passenger) => passenger.pinnedDriverId === null,
  );
  const directDurationByPassengerId = await buildDirectDurationTable({
    destination: problem.destination,
    passengers: optionalPassengers,
    routing,
  });
  const candidates = buildCandidateEdges({
    contexts,
    directDurationByPassengerId,
    passengers: optionalPassengers,
    problem,
  });
  const blacklistedEdges = new Set<string>();
  const optionalPassengerIds = optionalPassengers.map((passenger) => passenger.id);
  let optionalAssignments = solveAssignments({
    blacklistedEdges,
    candidateEdgesByPassengerId: candidates,
    contexts,
    passengerIds: optionalPassengerIds,
  });
  let assignments = combineAssignments({ optionalAssignments, passengers: problem.passengers });
  assertFullCoverage(problem, assignments);
  let plans = await buildRoutePlans({
    assignments,
    contexts,
    destination: problem.destination,
    passengerById,
    routing,
  });
  let repairRounds = 0;

  while (true) {
    const violatingPlans = [...plans.values()].filter(
      (plan) => plan.detourSeconds > problem.mode.maxDetourSeconds,
    );
    if (violatingPlans.length === 0) {
      break;
    }
    if (repairRounds >= problem.limits.maxRepairRounds) {
      throw new MatchingEngineError(
        "DETOUR_CONSTRAINT_UNSATISFIED",
        "Matching exhausted the configured repair rounds before satisfying the detour constraint.",
        {
          maxRepairRounds: problem.limits.maxRepairRounds,
          violatingDriverIds: violatingPlans.map((plan) => plan.context.driver.id).sort(),
        },
      );
    }
    const selectedEdges = await chooseEdgesToBlacklist({
      destination: problem.destination,
      passengerById,
      plans: violatingPlans,
      routing,
    });
    if (selectedEdges.length === 0) {
      throw new MatchingEngineError(
        "DETOUR_CONSTRAINT_UNSATISFIED",
        "A route violates the detour constraint but has no removable optional passenger.",
        { violatingDriverIds: violatingPlans.map((plan) => plan.context.driver.id).sort() },
      );
    }
    for (const selectedEdge of selectedEdges) {
      blacklistedEdges.add(selectedEdge);
    }
    repairRounds += 1;
    optionalAssignments = solveAssignments({
      blacklistedEdges,
      candidateEdgesByPassengerId: candidates,
      contexts,
      passengerIds: optionalPassengerIds,
    });
    assignments = combineAssignments({ optionalAssignments, passengers: problem.passengers });
    plans = await buildRoutePlans({
      assignments,
      contexts,
      destination: problem.destination,
      passengerById,
      routing,
    });
  }

  assertFullCoverage(problem, assignments);
  return buildPublicResult({
    assignments,
    blacklistedEdges,
    candidates,
    passengers: problem.passengers,
    plans,
    repairRounds,
    routingCallCount: routing.callCount,
  });
}
