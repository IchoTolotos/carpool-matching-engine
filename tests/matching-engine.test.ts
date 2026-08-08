import { describe, expect, it } from "vitest";
import {
  type MatchingProblem,
  matchCarpools,
  type RouteEvaluation,
  type RoutingProvider,
} from "../src/index.js";
import { StraightLineRoutingProvider } from "../src/testing/index.js";

const destination = { latitude: 0, longitude: 0.02 } as const;
const routing = new StraightLineRoutingProvider({
  speedKilometersPerHour: 36,
  stopPenaltySeconds: 0,
});

function naturalProblem(overrides: Partial<MatchingProblem> = {}): MatchingProblem {
  return {
    destination,
    drivers: [
      {
        capacity: 2,
        groupId: null,
        id: "driver-west",
        origin: { latitude: 0, longitude: 0 },
      },
    ],
    groupPolicy: "same-group",
    limits: { maxRepairRounds: 10, maxRoutingCalls: 100 },
    mode: {
      kind: "natural-carpool",
      maxDetourSeconds: 300,
      maxPickupDistanceKm: 2,
    },
    passengers: [],
    ...overrides,
  };
}

describe("matchCarpools", () => {
  it("assigns passengers to the closest compatible baseline while respecting capacity", async () => {
    const result = await matchCarpools(
      naturalProblem({
        drivers: [
          {
            capacity: 1,
            groupId: null,
            id: "driver-west",
            origin: { latitude: 0, longitude: 0 },
          },
          {
            capacity: 1,
            groupId: null,
            id: "driver-north",
            origin: { latitude: 0.02, longitude: 0.02 },
          },
        ],
        mode: {
          kind: "natural-carpool",
          maxDetourSeconds: 300,
          maxPickupDistanceKm: 0.5,
        },
        passengers: [
          {
            groupId: null,
            id: "passenger-west",
            origin: { latitude: 0.0002, longitude: 0.01 },
            pinnedDriverId: null,
          },
          {
            groupId: null,
            id: "passenger-north",
            origin: { latitude: 0.01, longitude: 0.0202 },
            pinnedDriverId: null,
          },
        ],
      }),
      routing,
    );

    expect(result.assignments).toEqual([
      expect.objectContaining({
        driverId: "driver-north",
        passengerId: "passenger-north",
        pinned: false,
      }),
      expect.objectContaining({
        driverId: "driver-west",
        passengerId: "passenger-west",
        pinned: false,
      }),
    ]);
    expect(result.unassignedPassengerIds).toEqual([]);
    expect(result.routes).toHaveLength(2);
  });

  it("reserves capacity for pinned passengers", async () => {
    const result = await matchCarpools(
      naturalProblem({
        drivers: [
          {
            capacity: 1,
            groupId: null,
            id: "driver-west",
            origin: { latitude: 0, longitude: 0 },
          },
        ],
        passengers: [
          {
            groupId: null,
            id: "passenger-pinned",
            origin: { latitude: 0, longitude: 0.008 },
            pinnedDriverId: "driver-west",
          },
          {
            groupId: null,
            id: "passenger-optional",
            origin: { latitude: 0, longitude: 0.012 },
            pinnedDriverId: null,
          },
        ],
      }),
      routing,
    );

    expect(result.assignments).toEqual([
      {
        driverId: "driver-west",
        estimatedAddedSeconds: null,
        passengerId: "passenger-pinned",
        pickupDistanceKm: null,
        pinned: true,
      },
    ]);
    expect(result.unassignedPassengerIds).toEqual(["passenger-optional"]);
  });

  it("enforces group compatibility before scoring candidate edges", async () => {
    const result = await matchCarpools(
      naturalProblem({
        drivers: [
          {
            capacity: 1,
            groupId: "blue",
            id: "driver-blue",
            origin: { latitude: 0, longitude: 0 },
          },
          {
            capacity: 1,
            groupId: "red",
            id: "driver-red",
            origin: { latitude: 0.0001, longitude: 0 },
          },
        ],
        passengers: [
          {
            groupId: "red",
            id: "passenger-red",
            origin: { latitude: 0, longitude: 0.01 },
            pinnedDriverId: null,
          },
        ],
      }),
      routing,
    );

    expect(result.assignments[0]?.driverId).toBe("driver-red");
  });

  it("allows an ungrouped passenger to match any driver only under the explicit policy", async () => {
    const base = naturalProblem({
      drivers: [
        {
          capacity: 1,
          groupId: "blue",
          id: "driver-blue",
          origin: { latitude: 0, longitude: 0 },
        },
      ],
      passengers: [
        {
          groupId: null,
          id: "passenger-ungrouped",
          origin: { latitude: 0, longitude: 0.01 },
          pinnedDriverId: null,
        },
      ],
    });

    const isolated = await matchCarpools(base, routing);
    const permissive = await matchCarpools(
      { ...base, groupPolicy: "ungrouped-passengers-match-any-driver" },
      routing,
    );

    expect(isolated.unassignedPassengerIds).toEqual(["passenger-ungrouped"]);
    expect(permissive.assignments[0]?.driverId).toBe("driver-blue");
  });

  it("repairs a route whose real detour exceeds the projection lower bound", async () => {
    const result = await matchCarpools(
      naturalProblem({
        mode: {
          kind: "natural-carpool",
          maxDetourSeconds: 20,
          maxPickupDistanceKm: 1,
        },
        passengers: [
          {
            groupId: null,
            id: "passenger-off-route",
            origin: { latitude: 0.005, longitude: 0.01 },
            pinnedDriverId: null,
          },
        ],
      }),
      routing,
    );

    expect(result.assignments).toEqual([]);
    expect(result.unassignedPassengerIds).toEqual(["passenger-off-route"]);
    expect(result.diagnostics.repairRounds).toBe(1);
    expect(result.diagnostics.blacklistedEdgeCount).toBe(1);
  });

  it("fails explicitly when full coverage cannot satisfy the route constraints", async () => {
    const promise = matchCarpools(
      {
        ...naturalProblem({
          passengers: [
            {
              groupId: null,
              id: "passenger-off-route",
              origin: { latitude: 0.005, longitude: 0.01 },
              pinnedDriverId: null,
            },
          ],
        }),
        mode: { kind: "full-coverage", maxDetourSeconds: 20 },
      },
      routing,
    );

    await expect(promise).rejects.toMatchObject({
      code: "FULL_COVERAGE_IMPOSSIBLE",
    });
  });

  it("rejects malformed routing responses instead of inferring missing data", async () => {
    const invalidProvider: RoutingProvider = {
      async route(): Promise<RouteEvaluation> {
        return {
          durationSeconds: 10,
          geometry: [
            { latitude: 0, longitude: 0 },
            { latitude: 0, longitude: 0.02 },
          ],
          orderedStopIds: [],
          segmentDurationSeconds: [],
        };
      },
    };

    await expect(matchCarpools(naturalProblem(), invalidProvider)).rejects.toMatchObject({
      code: "INVALID_ROUTING_RESPONSE",
    });
  });

  it("enforces the routing-call budget", async () => {
    const promise = matchCarpools(
      naturalProblem({
        limits: { maxRepairRounds: 1, maxRoutingCalls: 1 },
        passengers: [
          {
            groupId: null,
            id: "passenger-1",
            origin: { latitude: 0, longitude: 0.01 },
            pinnedDriverId: null,
          },
        ],
      }),
      routing,
    );

    await expect(promise).rejects.toMatchObject({
      code: "ROUTING_CALL_LIMIT_EXCEEDED",
    });
  });
});
