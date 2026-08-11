# Retired: `network/graph.py`

`graph_simulated.py` was imported by `interface/routers/network.py` and served
straight to the HUD's network command centre through `/api/network/graph`,
`/api/network/stats` and `/api/network/graph/{node_id}`.

Every node in it was invented at import time with `random`:

* 5 "Neural Process 0x{i}" compute nodes with `random.randint(10, 90)` load
* 45 devices with randomly-assigned layer, device type, trust status, and
  fabricated `192.168.{random}.{100+i}` addresses
* **20 "Threat IP {random}.{random}.{random}.{random}" nodes**, each marked
  `risk: high`, `trust: blocked`, joined to the gateway by an edge whose
  relation is literally `"attack"`

So the console displayed twenty attacks that never happened, against devices
that do not exist, and no part of the UI distinguished that from observation.

A real implementation already existed the whole time —
`core/network_topology_graph.py`, SQLite-backed, populated from live events by
`core/network_graph_builder.py`, and exposing the identical method surface. The
router simply imported the wrong module. It now reads the real graph, which
shows an empty topology until something is actually observed.

Kept here rather than deleted, in line with the rest of `archive/`. It is not
imported by anything.
