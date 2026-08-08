import { matchCarpools } from "../dist/index.js";
import { StraightLineRoutingProvider } from "../dist/testing/index.js";

const problem = {
  destination: { latitude: 48.1372, longitude: 11.5756 },
  drivers: [
    {
      capacity: 2,
      groupId: null,
      id: "driver-1",
      origin: { latitude: 48.125, longitude: 11.55 },
    },
  ],
  groupPolicy: "same-group",
  limits: { maxRepairRounds: 10, maxRoutingCalls: 100 },
  mode: {
    kind: "natural-carpool",
    maxDetourSeconds: 12 * 60,
    maxPickupDistanceKm: 3,
  },
  passengers: [
    {
      groupId: null,
      id: "passenger-1",
      origin: { latitude: 48.13, longitude: 11.56 },
      pinnedDriverId: null,
    },
    {
      groupId: null,
      id: "passenger-2",
      origin: { latitude: 48.132, longitude: 11.568 },
      pinnedDriverId: null,
    },
  ],
};

const routing = new StraightLineRoutingProvider({
  speedKilometersPerHour: 35,
  stopPenaltySeconds: 30,
});
const result = await matchCarpools(problem, routing);
process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
