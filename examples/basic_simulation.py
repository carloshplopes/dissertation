#!/usr/bin/env python3
"""
Basic 5G NR Simulation Example

This script demonstrates the basic usage of the 5G NR QoS and Mobility 
Simulation Framework for academic research.
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.simulation_engine import SimulationEngine
from src.core.config import SimulationConfig
from src.core.qos_manager import FiveQI


def main():
    """Run basic simulation example"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting basic 5G NR simulation example")
    
    # Create configuration
    config = SimulationConfig(
        simulation_time=30.0,  # 30 seconds
        random_seed=42,
        num_gnbs=2,
        coverage_radius=400.0,
        num_ues=3,
        mobility_model="random_walk",
        mobility_speed=2.0,  # 2 m/s
        qi_value=2,  # Conversational video
        packet_interval=0.050,  # 20 fps
        output_directory="examples/results"
    )
    
    # Print some 5QI information
    logger.info("5QI Information:")
    for qi in [1, 2, 5, 82]:
        qos = FiveQI.get_qos_characteristics(qi)
        if qos:
            logger.info(f"  5QI {qi}: Priority={qos.priority_level}, "
                       f"Delay Budget={qos.packet_delay_budget_ms}ms, "
                       f"PER={qos.packet_error_rate}")
    
    # Create and run simulation
    engine = SimulationEngine(config)
    results = engine.run()
    
    # Print results summary
    logger.info("Simulation Results:")
    metrics = results.get('metrics', {})
    counters = metrics.get('counters', {})
    
    logger.info(f"  Duration: {config.simulation_time} seconds")
    logger.info(f"  Packets sent: {counters.get('total_packets_sent', 0)}")
    logger.info(f"  Packets delivered: {counters.get('total_packets_delivered', 0)}")
    
    if counters.get('total_packets_sent', 0) > 0:
        delivery_ratio = counters.get('total_packets_delivered', 0) / counters.get('total_packets_sent', 1)
        logger.info(f"  Delivery ratio: {delivery_ratio * 100:.1f}%")
    
    handover_stats = metrics.get('handover_statistics', {})
    if handover_stats:
        logger.info(f"  Total handovers: {handover_stats.get('total_handovers', 0)}")
        logger.info(f"  Handover success rate: {handover_stats.get('success_rate', 0) * 100:.1f}%")
    
    # Save results
    engine.save_results(results, "basic_simulation_results.json")
    engine.metrics.export_to_csv(config.output_directory)
    
    logger.info(f"Results saved to {config.output_directory}/")
    logger.info("Basic simulation example completed successfully!")


if __name__ == "__main__":
    main()
