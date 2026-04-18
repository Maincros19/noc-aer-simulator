# NoC-AER Simulator: Neuromorphic-Optimized Cycle-Accurate Simulation

## Overview
This repository hosts a Network-on-Chip (NoC) simulator specifically designed for Address Event Representation (AER) based neuromorphic systems. The simulator has been refactored to provide a **cycle-accurate simulation framework** with **zero event loss** and **real fan-out connectivity**, aligning it with the fundamental requirements of spike-based neuromorphic hardware.

## Key Features

### 1. Cycle-Accurate C++ Backend
*   **Physical Fidelity:** All network metrics (latency, jitter, throughput, energy) are calculated cycle-by-cycle within a high-performance C++ engine.
*   **Zero Event Loss:** Implements an ideal backpressure mechanism where flits are never dropped due to buffer overflows, ensuring 100% delivery ratio for AER events.
*   **Energy Modeling:** Detailed dynamic and static energy calculations based on real manufacturing technology parameters (CMOS 65nm to 22nm FD-SOI).

### 2. Real AER Fan-out Connectivity
*   **Architectural Mapping:** Unlike simplified models, this simulator implements a **real fan-out** based on the Spiking Neural Network (SNN) architecture.
*   **Spike-to-Flit Propagation:**
    *   **Input -> Conv1:** Each input spike is propagated to all 12 feature maps of the first convolutional layer.
    *   **Conv1 -> Conv2:** Spikes from the first layer are sent to all 32 feature maps of the second layer.
    *   **Conv2 -> FC:** Spikes from the second layer are delivered to the 10 output neurons.
*   **Massive Traffic Generation:** This realistic connectivity generates hundreds of thousands of NoC events from a few thousand spikes, providing a true stress test for the communication infrastructure.

### 3. Distributed Spatial & Temporal Mapping
*   **Spatial Distribution:** Neurons and sensors are distributed across the 4x4 mesh to minimize local congestion and maximize parallelism.
*   **Temporal Scaling:** Implements a realistic AER temporal scaling that preserves the timing relationships of spikes while allowing the NoC sufficient cycles to process the massive event bursts.

## Architecture

*   **Frontend (Python):** Uses `snntorch` and `tonic` for SNN training and AER event generation from the N-MNIST dataset. It manages the mapping and interacts with the backend via `pybind11`.
*   **Backend (C++):** A discrete-event simulator that manages routers, buffers, XY-routing, and arbitration. It provides precise hardware metrics back to the frontend.

## Experimental Results (100 Iterations, Real Fan-out)

| Metric | 1 Epoch | 2 Epochs | 3 Epochs |
| :--- | :---: | :---: | :---: |
| **IA Accuracy** | 96.88% | 97.16% | 96.88% |
| **Flits Injected** | 695,132 | 708,448 | 758,356 |
| **Avg Latency (cycles)** | 5.97 | 5.98 | 5.99 |
| **Total Energy (uJ)** | 3.00 | 3.05 | 3.19 |
| **Sim Time (s)** | 9.54 | 9.33 | 9.81 |

## Installation & Usage

### Prerequisites
*   Python 3.11+, CMake, G++, `pybind11`, `torch`, `snntorch`, `tonic`.

### Build & Run
1.  **Build C++ Core:**
    ```bash
    cd cpp_simulator && mkdir build && cd build
    cmake -Dpybind11_DIR=$(python3.11 -m pybind11 --cmakedir) ..
    make
    ```
2.  **Run Simulation:**
    ```bash
    python3 nmnist_train_sim.py
    ```
    Follow the interactive menu to select technology, network congestion, and training parameters (epochs/iterations).

## License
This project is intended for research in neuromorphic hardware and NoC architectures.
