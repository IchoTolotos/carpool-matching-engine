export type Coordinate = Readonly<{
  latitude: number;
  longitude: number;
}>;

export type Driver = Readonly<{
  id: string;
  origin: Coordinate;
  capacity: number;
  groupId: string | null;
}>;

export type Passenger = Readonly<{
  id: string;
  origin: Coordinate;
  groupId: string | null;
  pinnedDriverId: string | null;
}>;

export type RouteStop = Readonly<{
  id: string;
  coordinate: Coordinate;
}>;

export type RouteRequest = Readonly<{
  origin: Coordinate;
  destination: Coordinate;
  stops: readonly RouteStop[];
}>;

export type RouteEvaluation = Readonly<{
  durationSeconds: number;
  geometry: readonly Coordinate[];
  segmentDurationSeconds: readonly number[];
  orderedStopIds: readonly string[];
}>;

export interface RoutingProvider {
  route(request: RouteRequest): Promise<RouteEvaluation>;
}

export type GroupPolicy = "same-group" | "ungrouped-passengers-match-any-driver";

export type MatchingMode =
  | Readonly<{
      kind: "natural-carpool";
      maxDetourSeconds: number;
      maxPickupDistanceKm: number;
    }>
  | Readonly<{
      kind: "full-coverage";
      maxDetourSeconds: number;
    }>;

export type MatchingLimits = Readonly<{
  maxRepairRounds: number;
  maxRoutingCalls: number;
}>;

export type MatchingProblem = Readonly<{
  destination: Coordinate;
  drivers: readonly Driver[];
  passengers: readonly Passenger[];
  groupPolicy: GroupPolicy;
  mode: MatchingMode;
  limits: MatchingLimits;
}>;

export type PassengerAssignment = Readonly<{
  passengerId: string;
  driverId: string;
  pinned: boolean;
  estimatedAddedSeconds: number | null;
  pickupDistanceKm: number | null;
}>;

export type MatchedRoute = Readonly<{
  driverId: string;
  passengerIds: readonly string[];
  orderedPassengerIds: readonly string[];
  baselineDurationSeconds: number;
  durationSeconds: number;
  detourSeconds: number;
  geometry: readonly Coordinate[];
}>;

export type MatchingDiagnostics = Readonly<{
  blacklistedEdgeCount: number;
  candidateEdgeCount: number;
  repairRounds: number;
  routingCallCount: number;
}>;

export type MatchingResult = Readonly<{
  assignments: readonly PassengerAssignment[];
  routes: readonly MatchedRoute[];
  unassignedPassengerIds: readonly string[];
  diagnostics: MatchingDiagnostics;
}>;
