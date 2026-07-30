# deep/science/algorithms.py — CS & AI Algorithms (Bible Section 1 tree)
"""Classic computer-science algorithms with step traces: sorting, searching,
dynamic programming, graph traversal. Pure-python, dependency-free."""
from __future__ import annotations

import heapq


class AlgorithmsEngine:
    def __init__(self, config=None):
        self.config = config

    # ── sorting ─────────────────────────────────────────────────────
    def quicksort(self, arr) -> dict:
        a = list(arr); comparisons = [0]

        def qs(lo, hi):
            if lo >= hi:
                return
            pivot = a[(lo + hi) // 2]; i, j = lo, hi
            while i <= j:
                while a[i] < pivot:
                    comparisons[0] += 1; i += 1
                while a[j] > pivot:
                    comparisons[0] += 1; j -= 1
                if i <= j:
                    a[i], a[j] = a[j], a[i]; i += 1; j -= 1
            qs(lo, j); qs(i, hi)
        qs(0, len(a) - 1)
        return {"sorted": a, "comparisons": comparisons[0], "result": a,
                "verbal": f"Quicksort ordered {len(a)} items in "
                          f"{comparisons[0]} comparisons."}

    def merge_sort(self, arr) -> dict:
        def ms(x):
            if len(x) <= 1:
                return x
            mid = len(x) // 2
            l, r = ms(x[:mid]), ms(x[mid:])
            out = []; i = j = 0
            while i < len(l) and j < len(r):
                if l[i] <= r[j]:
                    out.append(l[i]); i += 1
                else:
                    out.append(r[j]); j += 1
            return out + l[i:] + r[j:]
        s = ms(list(arr))
        return {"sorted": s, "result": s,
                "verbal": f"Merge sort ordered {len(s)} items (O(n log n))."}

    # ── searching ───────────────────────────────────────────────────
    def binary_search(self, arr, target) -> dict:
        lo, hi, steps = 0, len(arr) - 1, 0
        while lo <= hi:
            steps += 1; mid = (lo + hi) // 2
            if arr[mid] == target:
                return {"index": mid, "steps": steps, "result": mid,
                        "verbal": f"Found {target} at index {mid} in {steps} steps."}
            if arr[mid] < target:
                lo = mid + 1
            else:
                hi = mid - 1
        return {"index": -1, "steps": steps, "result": -1,
                "verbal": f"{target} not present ({steps} steps)."}

    # ── dynamic programming ─────────────────────────────────────────
    def knapsack(self, weights, values, capacity) -> dict:
        n = len(weights)
        dp = [[0] * (capacity + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for w in range(capacity + 1):
                dp[i][w] = dp[i-1][w]
                if weights[i-1] <= w:
                    dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])
        return {"max_value": dp[n][capacity], "result": dp[n][capacity],
                "verbal": f"0/1 knapsack optimum value {dp[n][capacity]} "
                          f"within capacity {capacity}."}

    def longest_common_subsequence(self, a, b) -> dict:
        m, n = len(a), len(b)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for i in range(1, m+1):
            for j in range(1, n+1):
                dp[i][j] = dp[i-1][j-1]+1 if a[i-1] == b[j-1] else max(dp[i-1][j], dp[i][j-1])
        return {"length": dp[m][n], "result": dp[m][n],
                "verbal": f"Longest common subsequence length {dp[m][n]}."}

    # ── graph ───────────────────────────────────────────────────────
    def dijkstra(self, graph, source) -> dict:
        dist = {source: 0}; pq = [(0, source)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, 1e18):
                continue
            for v, w in graph.get(u, {}).items():
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v] = nd; heapq.heappush(pq, (nd, v))
        return {"distances": dist, "result": dist,
                "verbal": f"Dijkstra from {source}: shortest distances {dist}."}

    def test(self) -> None:
        assert self.quicksort([3, 1, 2])["sorted"] == [1, 2, 3]
        assert self.binary_search([1, 3, 5, 7, 9], 7)["index"] == 3
        assert self.knapsack([1, 3, 4], [15, 20, 30], 4)["max_value"] == 35
        g = {"a": {"b": 1, "c": 4}, "b": {"c": 2}, "c": {}}
        assert self.dijkstra(g, "a")["distances"]["c"] == 3
        print("algorithms.AlgorithmsEngine: OK")


def test() -> None:
    AlgorithmsEngine().test()


if __name__ == "__main__":
    test()
