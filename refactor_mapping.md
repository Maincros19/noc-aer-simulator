# Refactor Mapping: Python Analytical to C++ Cycle-Accurate

This document identifies the analytical calculations currently performed in `nmnist_train_sim.py` and maps them to the new responsibilities of the C++ simulator.

| Metric / Calculation | Current Python Implementation (Analytical) | New C++ Implementation (Cycle-Accurate) |
| :--- | :--- | :--- |
| **Latency** | `get_lat(src, dst)`: Manhattan distance * factor + `np.random.normal`. | Calculated in `Router::switchFlit` using `current_time - flit.injection_time`. |
| **Congestion Loss** | `congestion_loss`: Linear factor of `injected_count` + `np.random.uniform`. | Naturally occurring when `input_buffers` exceed `max_buffer_size` in `Router::receiveFlit`. |
| **Energy** | `total_received * energy_per_spike`. | Sum of static energy (cycles) + dynamic energy (flit hops/switches) calculated per router. |
| **Throughput** | `total_received / (num_samples * 15)`. | `total_received / simulation_end_time`. |
| **Jitter** | `np.std(latencies)` from analytical latencies. | Standard deviation of actual flit latencies recorded during simulation. |

## Required C++ Changes
1.  **Router Class**:
    *   Add `max_buffer_size` to enforce physical limits and cause drops.
    *   Track `total_hops` or `total_switches` for dynamic energy.
    *   Track `squared_latency` to calculate variance/jitter.
    *   Add `getEnergy()` method based on technology parameters.
2.  **Network Class**:
    *   Aggregate metrics from all routers (Total Energy, Avg Latency, Total Dropped).
    *   Provide a summary report or individual getters for Python.
3.  **Pybind Interface**:
    *   Expose new metric getters.
    *   Allow setting `max_buffer_size` from Python.

## Required Python Changes
1.  Remove `get_lat` function.
2.  Remove `latencies` list and manual `injected_count` tracking for metrics.
3.  Remove `congestion_loss` and `total_dropped` analytical formulas.
4.  Call `network.runSimulation()` and then retrieve results using `network.get_total_energy()`, `network.get_avg_latency()`, etc.
