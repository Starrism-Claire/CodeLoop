import heapq


def shortest_paths(graph, source):
    """Return shortest distances from source using Dijkstra's algorithm."""
    if source not in graph:
        raise ValueError(f"unknown source node: {source}")

    distances = {source: 0}
    queue = [(0, source)]
    visited = set()

    while queue:
        current_distance, node = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)

        for neighbor, weight in graph.get(node, {}).items():
            if weight < 0:
                raise ValueError("negative edge weights are not supported")

            new_distance = current_distance + weight

            # BUG: compares against the current node's distance instead of
            # the neighbor's best known distance.
            if new_distance < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_distance
                heapq.heappush(queue, (new_distance, neighbor))

    return distances
