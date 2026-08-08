import type { CandidateEdge, DriverContext } from "./candidates.js";
import { addMinCostFlowEdge, createMinCostFlowGraph, solveMinCostFlow } from "./min-cost-flow.js";

export function solveAssignments(input: {
  blacklistedEdges: ReadonlySet<string>;
  candidateEdgesByPassengerId: ReadonlyMap<string, readonly CandidateEdge[]>;
  contexts: ReadonlyMap<string, DriverContext>;
  passengerIds: readonly string[];
}): Map<string, string> {
  const passengerIds = [...input.passengerIds].sort();
  const driverIds = [...input.contexts.keys()].sort();
  const passengerNodeById = new Map<string, number>();
  const driverNodeById = new Map<string, number>();
  const driverIdByNode = new Map<number, string>();
  let nextNode = 1;

  for (const passengerId of passengerIds) {
    passengerNodeById.set(passengerId, nextNode);
    nextNode += 1;
  }
  for (const driverId of driverIds) {
    driverNodeById.set(driverId, nextNode);
    driverIdByNode.set(nextNode, driverId);
    nextNode += 1;
  }
  const sink = nextNode;
  const graph = createMinCostFlowGraph(sink + 1);

  for (const passengerId of passengerIds) {
    addMinCostFlowEdge(graph, 0, passengerNodeById.get(passengerId) as number, 1, 0);
  }
  for (const driverId of driverIds) {
    const capacity = input.contexts.get(driverId)?.seatsRemaining ?? 0;
    if (capacity > 0) {
      addMinCostFlowEdge(graph, driverNodeById.get(driverId) as number, sink, capacity, 0);
    }
  }
  for (const passengerId of passengerIds) {
    const passengerNode = passengerNodeById.get(passengerId) as number;
    for (const edge of input.candidateEdgesByPassengerId.get(passengerId) ?? []) {
      if (input.blacklistedEdges.has(edgeKey(passengerId, edge.driverId))) {
        continue;
      }
      const driverNode = driverNodeById.get(edge.driverId);
      if (driverNode !== undefined) {
        addMinCostFlowEdge(graph, passengerNode, driverNode, 1, edge.cost);
      }
    }
  }

  solveMinCostFlow(graph, 0, sink, passengerIds.length);
  const assignments = new Map<string, string>();
  for (const [passengerId, passengerNode] of passengerNodeById) {
    for (const edge of graph[passengerNode] ?? []) {
      const driverId = driverIdByNode.get(edge.to);
      if (driverId && edge.initialCapacity === 1 && edge.capacity === 0) {
        assignments.set(passengerId, driverId);
        break;
      }
    }
  }
  return assignments;
}

export function edgeKey(passengerId: string, driverId: string): string {
  return `${passengerId}::${driverId}`;
}
