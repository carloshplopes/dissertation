# 5G NR QoS and Mobility Simulation Framework

This repository contains the source code for the simulations conducted as part of the Master's Thesis titled: **"5G Network Performance Analysis with Quality of Service and Mobility Considerations"** at the **Technical University**.

## About The Project

This project provides a simulation framework to evaluate the performance of 5G New Radio (NR) networks under various Quality of Service (QoS) configurations and mobility scenarios. The code was specifically developed to generate the results presented in Chapters 3, 4, and 5 of the aforementioned dissertation.

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
* [Pandas](https://pandas.pydata.org/)

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
    git clone https://github.com/carloshplopes/dissertation.git
    ```
2.  Navigate to the project directory
    ```sh
    cd dissertation
    ```
3.  Install the required packages
    ```sh
    pip install -r requirements.txt
    ```

## Usage

To run a specific simulation, execute the main script with the desired configuration file. For example:

```sh
python run_simulation.py --config scenarios/basic_scenario.json
```

### Example Scenarios

* **Basic 5QI Mapping:** Demonstrates standard QoS parameter mapping
* **Mobile UE Scenario:** Simulates user mobility with handover events
* **Video Streaming:** High-bitrate uplink streaming analysis
* **Multi-gNB Network:** Complex network topology with multiple base stations

## Project Structure

```
dissertation/
├── src/
│   ├── qos/
│   │   ├── __init__.py
│   │   ├── qci_mapping.py
│   │   └── qos_manager.py
│   ├── mobility/
│   │   ├── __init__.py
│   │   ├── user_equipment.py
│   │   └── handover.py
│   ├── network/
│   │   ├── __init__.py
│   │   ├── gnb.py
│   │   └── channel.py
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   └── metrics.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── visualization.py
├── scenarios/
│   ├── basic_scenario.json
│   ├── mobility_scenario.json
│   └── video_streaming_scenario.json
├── tests/
│   ├── test_qos.py
│   ├── test_mobility.py
│   └── test_simulation.py
├── results/
├── requirements.txt
└── run_simulation.py
```

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Carlos H. P. Lopes - [your.email@example.com](mailto:your.email@example.com)

Project Link: [https://github.com/carloshplopes/dissertation](https://github.com/carloshplopes/dissertation)
