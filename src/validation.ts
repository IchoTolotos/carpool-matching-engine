import { MatchingEngineError } from "./errors.js";
import type {
  Coordinate,
  GroupPolicy,
  MatchingProblem,
  RouteEvaluation,
  RouteRequest,
} from "./types.js";

function assertCoordinate(coordinate: Coordinate, label: string): void {
  if (
    !Number.isFinite(coordinate.latitude) ||
    coordinate.latitude < -90 ||
    coordinate.latitude > 90 ||
    !Number.isFinite(coordinate.longitude) ||
    coordinate.longitude < -180 ||
    coordinate.longitude > 180
  ) {
    throw new MatchingEngineError("INVALID_INPUT", `${label} is not a valid coordinate.`, {
      coordinate,
      label,
    });
  }
}

export function groupsAreCompatible(
  driverGroupId: string | null,
  passengerGroupId: string | null,
  policy: GroupPolicy,
): boolean {
  if (policy === "ungrouped-passengers-match-any-driver") {
    return passengerGroupId === null || driverGroupId === passengerGroupId;
  }
  return driverGroupId === passengerGroupId;
}

export function validateProblem(problem: MatchingProblem): void {
  assertCoordinate(problem.destination, "destination");
  if (!Number.isInteger(problem.limits.maxRoutingCalls) || problem.limits.maxRoutingCalls < 1) {
    throw new MatchingEngineError(
      "INVALID_INPUT",
      "limits.maxRoutingCalls must be a positive integer.",
    );
  }
  if (!Number.isInteger(problem.limits.maxRepairRounds) || problem.limits.maxRepairRounds < 0) {
    throw new MatchingEngineError(
      "INVALID_INPUT",
      "limits.maxRepairRounds must be a non-negative integer.",
    );
  }
  if (!Number.isFinite(problem.mode.maxDetourSeconds) || problem.mode.maxDetourSeconds < 0) {
    throw new MatchingEngineError(
      "INVALID_INPUT",
      "mode.maxDetourSeconds must be a non-negative finite number.",
    );
  }
  if (
    problem.mode.kind === "natural-carpool" &&
    (!Number.isFinite(problem.mode.maxPickupDistanceKm) || problem.mode.maxPickupDistanceKm < 0)
  ) {
    throw new MatchingEngineError(
      "INVALID_INPUT",
      "mode.maxPickupDistanceKm must be a non-negative finite number.",
    );
  }

  const participantIds = new Set<string>();
  const driversById = new Map(problem.drivers.map((driver) => [driver.id, driver]));
  const pinnedCountByDriverId = new Map<string, number>();

  for (const driver of problem.drivers) {
    if (!driver.id.trim()) {
      throw new MatchingEngineError("INVALID_INPUT", "Driver ids must not be empty.");
    }
    if (participantIds.has(driver.id)) {
      throw new MatchingEngineError("DUPLICATE_ID", `Duplicate participant id: ${driver.id}`, {
        participantId: driver.id,
      });
    }
    participantIds.add(driver.id);
    assertCoordinate(driver.origin, `driver ${driver.id} origin`);
    if (!Number.isInteger(driver.capacity) || driver.capacity < 0) {
      throw new MatchingEngineError(
        "INVALID_INPUT",
        `Driver ${driver.id} capacity must be a non-negative integer.`,
        { driverId: driver.id },
      );
    }
  }

  for (const passenger of problem.passengers) {
    if (!passenger.id.trim()) {
      throw new MatchingEngineError("INVALID_INPUT", "Passenger ids must not be empty.");
    }
    if (participantIds.has(passenger.id)) {
      throw new MatchingEngineError("DUPLICATE_ID", `Duplicate participant id: ${passenger.id}`, {
        participantId: passenger.id,
      });
    }
    participantIds.add(passenger.id);
    assertCoordinate(passenger.origin, `passenger ${passenger.id} origin`);
    if (!passenger.pinnedDriverId) {
      continue;
    }
    const driver = driversById.get(passenger.pinnedDriverId);
    if (!driver) {
      throw new MatchingEngineError(
        "PINNED_DRIVER_NOT_FOUND",
        `Passenger ${passenger.id} references missing driver ${passenger.pinnedDriverId}.`,
        { passengerId: passenger.id, pinnedDriverId: passenger.pinnedDriverId },
      );
    }
    if (!groupsAreCompatible(driver.groupId, passenger.groupId, problem.groupPolicy)) {
      throw new MatchingEngineError(
        "INVALID_INPUT",
        `Pinned passenger ${passenger.id} is incompatible with driver ${driver.id} under the selected group policy.`,
        { driverId: driver.id, passengerId: passenger.id },
      );
    }
    pinnedCountByDriverId.set(driver.id, (pinnedCountByDriverId.get(driver.id) ?? 0) + 1);
  }

  for (const driver of problem.drivers) {
    const pinnedCount = pinnedCountByDriverId.get(driver.id) ?? 0;
    if (pinnedCount > driver.capacity) {
      throw new MatchingEngineError(
        "CAPACITY_EXCEEDED_BY_PINNED_PASSENGERS",
        `Driver ${driver.id} has ${pinnedCount} pinned passengers but only ${driver.capacity} seats.`,
        { capacity: driver.capacity, driverId: driver.id, pinnedCount },
      );
    }
  }
}

export function validateRouteEvaluation(request: RouteRequest, evaluation: RouteEvaluation): void {
  if (!Number.isFinite(evaluation.durationSeconds) || evaluation.durationSeconds < 0) {
    throwInvalidRoutingResponse("durationSeconds must be a non-negative finite number.");
  }
  if (evaluation.geometry.length < 2) {
    throwInvalidRoutingResponse("geometry must contain at least two points.");
  }
  for (const [index, coordinate] of evaluation.geometry.entries()) {
    try {
      assertCoordinate(coordinate, `routing geometry point ${index}`);
    } catch (error) {
      throwInvalidRoutingResponse("geometry contains an invalid coordinate.", { cause: error });
    }
  }
  if (evaluation.segmentDurationSeconds.length !== evaluation.geometry.length - 1) {
    throwInvalidRoutingResponse(
      "segmentDurationSeconds must contain exactly one value per geometry segment.",
    );
  }
  if (
    evaluation.segmentDurationSeconds.some((duration) => !Number.isFinite(duration) || duration < 0)
  ) {
    throwInvalidRoutingResponse(
      "segmentDurationSeconds values must be non-negative finite numbers.",
    );
  }
  const segmentTotal = evaluation.segmentDurationSeconds.reduce(
    (sum, duration) => sum + duration,
    0,
  );
  if (Math.abs(segmentTotal - evaluation.durationSeconds) > 0.001) {
    throwInvalidRoutingResponse(
      "segmentDurationSeconds must sum to durationSeconds within one millisecond.",
      { durationSeconds: evaluation.durationSeconds, segmentTotal },
    );
  }

  const requestedStopIds = request.stops.map((stop) => stop.id).sort();
  const orderedStopIds = [...evaluation.orderedStopIds].sort();
  if (
    requestedStopIds.length !== orderedStopIds.length ||
    requestedStopIds.some((stopId, index) => stopId !== orderedStopIds[index])
  ) {
    throwInvalidRoutingResponse(
      "orderedStopIds must be an exact permutation of the requested stop ids.",
      { orderedStopIds: evaluation.orderedStopIds, requestedStopIds },
    );
  }
}

function throwInvalidRoutingResponse(
  message: string,
  details: Readonly<Record<string, unknown>> = {},
): never {
  throw new MatchingEngineError("INVALID_ROUTING_RESPONSE", message, details);
}
