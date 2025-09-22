# 5G NR QoS and Mobility Simulation Framework

This repository contains the source code for the simulations conducted as part of the Master's Thesis titled: **"5G Network Performance Evaluation: QoS Mapping and Mobility Analysis for Demanding Applications"** at the **Universidade do Porto**.

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
* [SimPy](https://simpy.readthedocs.io/) - Discrete Event Simulation Framework

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
python run_simulation.py --config scenarios/appendix_B_scenario.json
```

### Available Scenarios

* `scenarios/single_gnb_stationary.json` - Single gNB with stationary UE
* `scenarios/multi_gnb_mobility.json` - Multiple gNBs with mobile UE
* `scenarios/handover_evaluation.json` - Handover performance analysis
* `scenarios/appendix_B_scenario.json` - Appendix B validation scenario

### Output

The simulation generates:
* Performance metrics in CSV format
* Visualization plots (throughput, delay, handover events)
* Detailed logs for analysis

## Project Structure

```
dissertation/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── simulation_engine.py
│   │   └── qos_manager.py
│   ├── network/
│   │   ├── __init__.py
│   │   ├── gnb.py
│   │   ├── ue.py
│   │   └── channel.py
│   ├── mobility/
│   │   ├── __init__.py
│   │   ├── mobility_models.py
│   │   └── handover.py
│   └── utils/
│       ├── __init__.py
│       ├── metrics.py
│       └── config_parser.py
├── scenarios/
├── results/
├── tests/
├── run_simulation.py
├── requirements.txt
└── README.md
```

## Contributing

This is academic research code. For questions or collaboration opportunities, please contact the author.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

Carlos Lopes - carlos.lopes@example.com

Project Link: [https://github.com/carloshplopes/dissertation](https://github.com/carloshplopes/dissertation)
