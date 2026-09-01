import unittest

from dijkstra import shortest_paths


class DijkstraTests(unittest.TestCase):
    def test_finds_shortest_paths_in_weighted_graph(self):
        graph = {
            "A": {"B": 4, "C": 1},
            "B": {"D": 1},
            "C": {"B": 2, "D": 5},
            "D": {},
        }

        self.assertEqual(
            shortest_paths(graph, "A"),
            {"A": 0, "C": 1, "B": 3, "D": 4},
        )

    def test_keeps_best_distance_when_longer_path_is_seen_later(self):
        graph = {
            "A": {"B": 1, "C": 10},
            "B": {"C": 1},
            "C": {},
        }

        self.assertEqual(shortest_paths(graph, "A")["C"], 2)

    def test_handles_zero_weight_edges(self):
        graph = {
            "A": {"B": 0, "C": 5},
            "B": {"C": 0, "D": 2},
            "C": {"D": 1},
            "D": {},
        }

        self.assertEqual(
            shortest_paths(graph, "A"),
            {"A": 0, "B": 0, "C": 0, "D": 1},
        )

    def test_handles_cycles_without_revisiting_forever(self):
        graph = {
            "A": {"B": 2, "C": 9},
            "B": {"C": 2, "A": 2},
            "C": {"D": 1, "B": 2},
            "D": {"B": 3},
        }

        self.assertEqual(
            shortest_paths(graph, "A"),
            {"A": 0, "B": 2, "C": 4, "D": 5},
        )

    def test_handles_neighbor_without_explicit_adjacency_entry(self):
        graph = {
            "A": {"B": 3},
        }

        self.assertEqual(shortest_paths(graph, "A"), {"A": 0, "B": 3})

    def test_source_with_no_edges_returns_only_source(self):
        graph = {
            "A": {},
            "B": {"C": 1},
            "C": {},
        }

        self.assertEqual(shortest_paths(graph, "A"), {"A": 0})

    def test_negative_weight_discovered_after_first_hop_raises_value_error(self):
        graph = {
            "A": {"B": 1},
            "B": {"C": -2},
            "C": {},
        }

        with self.assertRaises(ValueError):
            shortest_paths(graph, "A")

    def test_does_not_mutate_input_graph(self):
        graph = {
            "A": {"B": 1},
            "B": {"C": 2},
            "C": {},
        }
        expected_graph = {
            "A": {"B": 1},
            "B": {"C": 2},
            "C": {},
        }

        shortest_paths(graph, "A")

        self.assertEqual(graph, expected_graph)

    def test_ignores_unreachable_nodes(self):
        graph = {
            "A": {"B": 2},
            "B": {},
            "Z": {},
        }

        self.assertEqual(shortest_paths(graph, "A"), {"A": 0, "B": 2})

    def test_unknown_source_raises_value_error(self):
        with self.assertRaises(ValueError):
            shortest_paths({"A": {}}, "missing")

    def test_negative_weight_raises_value_error(self):
        graph = {
            "A": {"B": -1},
            "B": {},
        }

        with self.assertRaises(ValueError):
            shortest_paths(graph, "A")


if __name__ == "__main__":
    unittest.main()
