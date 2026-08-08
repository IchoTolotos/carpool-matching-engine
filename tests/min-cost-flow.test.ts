import { describe, expect, it } from "vitest";
import {
  addMinCostFlowEdge,
  createMinCostFlowGraph,
  solveMinCostFlow,
} from "../src/min-cost-flow.js";

describe("solveMinCostFlow", () => {
  it("maximizes flow and selects the minimum-cost augmenting paths", () => {
    const graph = createMinCostFlowGraph(6);
    addMinCostFlowEdge(graph, 0, 1, 1, 0);
    addMinCostFlowEdge(graph, 0, 2, 1, 0);
    addMinCostFlowEdge(graph, 1, 3, 1, 1);
    addMinCostFlowEdge(graph, 1, 4, 1, 10);
    addMinCostFlowEdge(graph, 2, 3, 1, 2);
    addMinCostFlowEdge(graph, 2, 4, 1, 1);
    addMinCostFlowEdge(graph, 3, 5, 1, 0);
    addMinCostFlowEdge(graph, 4, 5, 1, 0);

    expect(solveMinCostFlow(graph, 0, 5, 2)).toEqual({ cost: 2, flow: 2 });
  });
});
