# 5G NR QoS and Mobility Simulation Framework

This repository contains the source code for the simulations conducted as part of the Master's Thesis titled: **"[Evaluation of 5G Networks for Large-Scale Event Transmission]"** at the **[IST - Lisbon University]**.

## About The Project

This project provides a simulation framework to evaluate the performance of 5G New Radio (NR) networks under various Quality of Service (QoS) configurations and mobility scenarios. The code was specifically developed to generate the results presented in Chapters [ex: 3, 4, and 5] of the aforementioned dissertation.

The primary focus is on the practical implementation and analysis of the 3GPP 5QI (5G QoS Identifier) mechanism for Guaranteed Bit Rate (GBR) services. A key use case explored is high-bitrate uplink video streaming, simulating real-world conditions for media production over 5G.

### Key Features

* **Configurable 5G NR Scenarios:** Easily define network layouts with single or multiple gNBs (base stations).
* **5QI QoS Framework:** Implementation of the standardized mapping between 5QI values and QoS characteristics (latency, reliability, priority).
* **User Mobility:** Models both stationary and mobile User Equipment (UE) to test performance on the move.
* **Handover Simulation:** Evaluates the impact of handover procedures on service continuity and performance.
* **Performance Metrics:** Generates key metrics such as throughput, packet delay, and packet error rate.

### Built With

* [Python 3.x](https://www.python.org/)
* [NumPy](https://numpy.org/)
* [Matplotlib](https://matplotlib.org/)
* [Nome do Simulador, ex: ns-3, OMNeT++, ou outra biblioteca principal]

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

* Python 3.8 or higher
* pip
    ```sh
    pip install -r requirements.txt
    ```

### Installation

1.  Clone the repo
    ```sh
    git clone [https://github.com/](https://github.com/)[your_username]/[your_repository_name].git
    ```
2.  Navigate to the project directory
    ```sh
    cd [your_repository_name]
    ```
3.  Install the required packages
    ```sh
    pip install -r requirements.txt
    ```

## Usage

To run a specific simulation, execute the main script with the desired configuration file. For example:

```sh
python run_simulation.py --config scenarios/appendix_B_scenario.json
