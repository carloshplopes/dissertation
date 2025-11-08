# 5G NR QoS and Mobility Simulation Framework

This repository contains the source code for the simulations conducted as part of the Master's Thesis titled: **Large-Scale Live Event Using 5g Networks** at the **IST - Lisbon University**.


## About The Project

This project provides a simulation framework to evaluate the performance of 5G New Radio (NR) networks under various Quality of Service (QoS) configurations and mobility scenarios. The simulations were implemented using **ns-3**, a discrete-event network simulator.

The framework leverages the **5G-LENA NR module**, an open-source extension developed by the CTTC, which provides a 3GPP-compliant implementation of the 5G NR protocol stack. This setup was used to generate the results presented in Chapter 5 of the dissertation.

The primary focus is on the practical analysis of the 3GPP 5QI (5G QoS Identifier) mechanism for Guaranteed Bit Rate (GBR) services. A key use case explored is high-bitrate uplink video streaming, simulating real-world conditions for media production over 5G.

### Key Features

* **Configurable 5G NR Scenarios:** Define network layouts with single or multiple gNBs.
* **5QI QoS Framework:** Implementation of the standardized mapping between 5QI values and QoS characteristics.
* **User Mobility:** Models both stationary and mobile User Equipment (UE).
* **Handover Simulation:** Evaluates the impact of handover procedures on service continuity.
* **3GPP-Compliant Stack:** Built on the ns-3 5G-LENA module for realistic NR protocol behavior.
* **Performance Metrics:** Generates key metrics such as throughput, packet delay, and packet error rate.

### Built With

* [ns-3 (Network Simulator 3)](https://www.nsnam.org/)
* [5G-LENA NR Module (CTTC)](https://5g-lena.cttc.es/)


## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

* A working installation of ns-3 (version [ex: ns-3.42]).
* The 5G-LENA NR module properly integrated with your ns-3 installation.


### Installation & Usage

1.  Clone the repo into your `ns-3/scratch` directory:
    ```sh
    git clone [https://github.com/](https://github.com/)[your_username]/[your_repository_name].git [your_repository_name]
    ```
2.  Navigate to your ns-3 directory and build the project:
    ```sh
    ./ns3 build
    ```
3.  Run a simulation scenario:
    ```sh
    ./ns3 run "scratch/[your_repository_name]/[script_name]"
    ```
For more details on the available parameters and scenarios, please refer to the documentation within the code or the dissertation text.

## Associated Publication

For a detailed explanation of the methodology, scenarios, and analysis of the results, please refer to the full dissertation document:

**[Dissertation](https://fenix.tecnico.ulisboa.pt/cursos/merc/dissertacao/1128253548924068)**

## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

## Contact

Carlos Lopes - [carlos.pinho.lopes@tecnico.ulisboa.pt]

Project Link: [https://github.com/carloshplopes/dissertation](https://github.com/carloshplopes/[dissertation)
