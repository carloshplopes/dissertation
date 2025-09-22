"""
Configuration classes for the simulation framework
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SimulationConfig:
    """Configuration parameters for the simulation"""
    simulation_time: float = 100.0  # seconds
    random_seed: Optional[int] = None
    log_level: str = "INFO"
    output_directory: str = "results"
    enable_plots: bool = True
    
    # Network configuration
    num_gnbs: int = 1
    coverage_radius: float = 500.0  # meters
    carrier_frequency: float = 3.5e9  # Hz (3.5 GHz)
    bandwidth: float = 100e6  # Hz (100 MHz)
    
    # UE configuration
    num_ues: int = 1
    initial_positions: Optional[List[tuple]] = None
    mobility_model: str = "random_walk"
    mobility_speed: float = 1.4  # m/s (walking speed)
    
    # Traffic configuration
    traffic_model: str = "video_streaming"
    packet_size: int = 1500  # bytes
    packet_interval: float = 0.033  # seconds (30 fps)
    qi_value: int = 2  # 5QI for conversational video