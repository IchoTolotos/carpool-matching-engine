export type MinCostFlowEdge = {
  capacity: number;
  cost: number;
  initialCapacity: number;
  reverseIndex: number;
  to: number;
};

type HeapItem = Readonly<{ distance: number; node: number }>;

class MinHeap {
  private readonly items: HeapItem[] = [];

  get size(): number {
    return this.items.length;
  }

  push(item: HeapItem): void {
    this.items.push(item);
    let index = this.items.length - 1;
    while (index > 0) {
      const parent = Math.floor((index - 1) / 2);
      if ((this.items[parent]?.distance ?? Number.POSITIVE_INFINITY) <= item.distance) {
        break;
      }
      this.items[index] = this.items[parent] as HeapItem;
      index = parent;
    }
    this.items[index] = item;
  }

  pop(): HeapItem | undefined {
    const first = this.items[0];
    const last = this.items.pop();
    if (!first || !last || this.items.length === 0) {
      return first;
    }

    let index = 0;
    while (true) {
      const left = index * 2 + 1;
      const right = left + 1;
      if (left >= this.items.length) {
        break;
      }
      const smallerChild =
        right < this.items.length &&
        (this.items[right]?.distance ?? Number.POSITIVE_INFINITY) <
          (this.items[left]?.distance ?? Number.POSITIVE_INFINITY)
          ? right
          : left;
      if ((this.items[smallerChild]?.distance ?? Number.POSITIVE_INFINITY) >= last.distance) {
        break;
      }
      this.items[index] = this.items[smallerChild] as HeapItem;
      index = smallerChild;
    }
    this.items[index] = last;
    return first;
  }
}

export function createMinCostFlowGraph(nodeCount: number): MinCostFlowEdge[][] {
  return Array.from({ length: nodeCount }, () => []);
}

export function addMinCostFlowEdge(
  graph: MinCostFlowEdge[][],
  from: number,
  to: number,
  capacity: number,
  cost: number,
): void {
  const forward: MinCostFlowEdge = {
    to,
    reverseIndex: graph[to]?.length ?? 0,
    capacity,
    initialCapacity: capacity,
    cost,
  };
  const backward: MinCostFlowEdge = {
    to: from,
    reverseIndex: graph[from]?.length ?? 0,
    capacity: 0,
    initialCapacity: 0,
    cost: -cost,
  };
  graph[from]?.push(forward);
  graph[to]?.push(backward);
}

export function solveMinCostFlow(
  graph: MinCostFlowEdge[][],
  source: number,
  sink: number,
  maximumFlow: number,
): Readonly<{ cost: number; flow: number }> {
  const nodeCount = graph.length;
  const potential = new Array<number>(nodeCount).fill(0);
  let flow = 0;
  let totalCost = 0;

  while (flow < maximumFlow) {
    const distances = new Array<number>(nodeCount).fill(Number.POSITIVE_INFINITY);
    const previousNode = new Array<number>(nodeCount).fill(-1);
    const previousEdge = new Array<number>(nodeCount).fill(-1);
    const heap = new MinHeap();
    distances[source] = 0;
    heap.push({ distance: 0, node: source });

    while (heap.size > 0) {
      const current = heap.pop();
      if (!current || current.distance !== distances[current.node]) {
        continue;
      }
      for (const [edgeIndex, edge] of (graph[current.node] ?? []).entries()) {
        if (edge.capacity <= 0) {
          continue;
        }
        const nextDistance =
          current.distance + edge.cost + (potential[current.node] ?? 0) - (potential[edge.to] ?? 0);
        if (nextDistance >= (distances[edge.to] ?? Number.POSITIVE_INFINITY)) {
          continue;
        }
        distances[edge.to] = nextDistance;
        previousNode[edge.to] = current.node;
        previousEdge[edge.to] = edgeIndex;
        heap.push({ distance: nextDistance, node: edge.to });
      }
    }

    if (!Number.isFinite(distances[sink])) {
      break;
    }
    for (let node = 0; node < nodeCount; node += 1) {
      if (Number.isFinite(distances[node])) {
        potential[node] = (potential[node] ?? 0) + (distances[node] ?? 0);
      }
    }

    let addedFlow = maximumFlow - flow;
    for (let node = sink; node !== source; ) {
      const parent = previousNode[node] ?? -1;
      const edgeIndex = previousEdge[node] ?? -1;
      if (parent < 0 || edgeIndex < 0) {
        addedFlow = 0;
        break;
      }
      addedFlow = Math.min(addedFlow, graph[parent]?.[edgeIndex]?.capacity ?? 0);
      node = parent;
    }
    if (addedFlow <= 0) {
      break;
    }

    for (let node = sink; node !== source; ) {
      const parent = previousNode[node] ?? -1;
      const edgeIndex = previousEdge[node] ?? -1;
      if (parent < 0 || edgeIndex < 0) {
        throw new Error("Residual path became invalid while applying flow.");
      }
      const edge = graph[parent]?.[edgeIndex] as MinCostFlowEdge;
      edge.capacity -= addedFlow;
      const reverse = graph[node]?.[edge.reverseIndex] as MinCostFlowEdge;
      reverse.capacity += addedFlow;
      totalCost += edge.cost * addedFlow;
      node = parent;
    }
    flow += addedFlow;
  }

  return { cost: totalCost, flow };
}
