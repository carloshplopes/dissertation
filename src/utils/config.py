"""
Configuration management for 5G NR simulations.

This module provides utilities for loading and validating simulation configurations.
"""

import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import jsonschema


class ConfigManager:
    """Manages simulation configuration loading and validation."""
    
    # Configuration schema for validation
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "simulation": {
                "type": "object",
                "properties": {
                    "simulation_time": {"type": "number", "minimum": 0},
                    "time_step": {"type": "number", "minimum": 0.001},
                    "output_file": {"type": "string"},
                    "enable_visualization": {"type": "boolean"}
                },
                "required": ["simulation_time", "time_step"]
            },
            "network": {
                "type": "object",
                "properties": {
                    "num_gnbs": {"type": "integer", "minimum": 1},
                    "gnb_positions": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    },
                    "gnb_tx_power": {"type": "number"},
                    "frequency": {"type": "number", "minimum": 0},
                    "bandwidth": {"type": "number", "minimum": 0}
                },
                "required": ["num_gnbs"]
            },
            "ues": {
                "type": "object",
                "properties": {
                    "num_ues": {"type": "integer", "minimum": 1},
                    "ue_positions": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    },
                    "mobility_models": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["stationary", "linear", "random_walk", "circular", "highway"]
                        }
                    },
                    "mobility_params": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["num_ues"]
            },
            "channel": {
                "type": "object",
                "properties": {
                    "propagation_model": {
                        "type": "string",
                        "enum": ["free_space", "urban_macro", "urban_micro", "indoor", "rural_macro"]
                    },
                    "enable_shadowing": {"type": "boolean"},
                    "enable_fast_fading": {"type": "boolean"}
                }
            },
            "qos": {
                "type": "object",
                "properties": {
                    "default_qci": {"type": "integer", "minimum": 1, "maximum": 255},
                    "qos_flows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ue_id": {"type": "integer"},
                                "qci": {"type": "integer"},
                                "guaranteed_bitrate_ul": {"type": "integer"},
                                "guaranteed_bitrate_dl": {"type": "integer"}
                            },
                            "required": ["ue_id", "qci"]
                        }
                    }
                }
            }
        },
        "required": ["simulation", "network", "ues"]
    }
    
    @classmethod
    def load_config(cls, config_file: str):
        """
        Load configuration from file.
        
        Args:
            config_file: Path to configuration file (JSON or YAML)
            
        Returns:
            Dictionary with configuration data
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        from ..simulation.engine import SimulationConfig  # Import here to avoid circular imports
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        # Load configuration based on file extension
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                config_data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        
        # Validate configuration
        cls.validate_config(config_data)
        
        # Convert to SimulationConfig
        return cls._create_simulation_config(config_data)
    
    @classmethod
    def validate_config(cls, config_data: Dict[str, Any]):
        """
        Validate configuration against schema.
        
        Args:
            config_data: Configuration dictionary
            
        Raises:
            jsonschema.ValidationError: If config is invalid
        """
        jsonschema.validate(config_data, cls.CONFIG_SCHEMA)
    
    @classmethod
    def _create_simulation_config(cls, config_data: Dict[str, Any]):
        """Create SimulationConfig from validated configuration data."""
        from ..simulation.engine import SimulationConfig  # Import here to avoid circular imports
        sim_config = config_data.get('simulation', {})
        network_config = config_data.get('network', {})
        ues_config = config_data.get('ues', {})
        channel_config = config_data.get('channel', {})
        qos_config = config_data.get('qos', {})
        
        return SimulationConfig(
            # Simulation parameters
            simulation_time=sim_config.get('simulation_time', 60.0),
            time_step=sim_config.get('time_step', 0.1),
            output_file=sim_config.get('output_file'),
            enable_visualization=sim_config.get('enable_visualization', False),
            
            # Network parameters
            num_gnbs=network_config.get('num_gnbs', 3),
            gnb_positions=network_config.get('gnb_positions'),
            gnb_tx_power=network_config.get('gnb_tx_power', 46.0),
            frequency=network_config.get('frequency', 3500.0),
            bandwidth=network_config.get('bandwidth', 100.0),
            
            # UE parameters
            num_ues=ues_config.get('num_ues', 10),
            ue_positions=ues_config.get('ue_positions'),
            mobility_models=ues_config.get('mobility_models'),
            mobility_params=ues_config.get('mobility_params'),
            
            # Channel parameters
            propagation_model=channel_config.get('propagation_model', 'urban_macro'),
            enable_shadowing=channel_config.get('enable_shadowing', True),
            enable_fast_fading=channel_config.get('enable_fast_fading', True),
            
            # QoS parameters
            default_qci=qos_config.get('default_qci', 9),
            qos_flows=qos_config.get('qos_flows')
        )
    
    @classmethod
    def create_default_config(cls, config_file: str, scenario: str = "basic"):
        """
        Create a default configuration file.
        
        Args:
            config_file: Output configuration file path
            scenario: Scenario type ("basic", "mobility", "video_streaming")
        """
        if scenario == "basic":
            config = cls._create_basic_scenario_config()
        elif scenario == "mobility":
            config = cls._create_mobility_scenario_config()
        elif scenario == "video_streaming":
            config = cls._create_video_streaming_scenario_config()
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        # Save configuration
        config_path = Path(config_file)
        with open(config_path, 'w') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            else:
                json.dump(config, f, indent=2)
    
    @classmethod
    def _create_basic_scenario_config(cls) -> Dict[str, Any]:
        """Create basic scenario configuration."""
        return {
            "simulation": {
                "simulation_time": 30.0,
                "time_step": 0.1,
                "output_file": "results/basic_scenario_results.json",
                "enable_visualization": True
            },
            "network": {
                "num_gnbs": 3,
                "gnb_positions": [[-500, 0], [500, 0], [0, 866]],
                "gnb_tx_power": 46.0,
                "frequency": 3500.0,
                "bandwidth": 100.0
            },
            "ues": {
                "num_ues": 10,
                "mobility_models": ["stationary"] * 10
            },
            "channel": {
                "propagation_model": "urban_macro",
                "enable_shadowing": True,
                "enable_fast_fading": True
            },
            "qos": {
                "default_qci": 9
            }
        }
    
    @classmethod
    def _create_mobility_scenario_config(cls) -> Dict[str, Any]:
        """Create mobility scenario configuration."""
        return {
            "simulation": {
                "simulation_time": 60.0,
                "time_step": 0.1,
                "output_file": "results/mobility_scenario_results.json",
                "enable_visualization": True
            },
            "network": {
                "num_gnbs": 4,
                "gnb_positions": [[-1000, -1000], [1000, -1000], [-1000, 1000], [1000, 1000]],
                "gnb_tx_power": 46.0,
                "frequency": 3500.0,
                "bandwidth": 100.0
            },
            "ues": {
                "num_ues": 15,
                "mobility_models": ["random_walk"] * 8 + ["linear"] * 4 + ["circular"] * 3,
                "mobility_params": [
                    {"max_speed": 5.0, "direction_change_prob": 0.1} for _ in range(8)
                ] + [
                    {"speed": 10.0, "direction": i * 1.57} for i in range(4)  # 0, π/2, π, 3π/2
                ] + [
                    {"radius": 200.0, "angular_speed": 0.05, "center_x": 0, "center_y": 0} for _ in range(3)
                ]
            },
            "channel": {
                "propagation_model": "urban_macro",
                "enable_shadowing": True,
                "enable_fast_fading": True
            },
            "qos": {
                "default_qci": 9
            }
        }
    
    @classmethod
    def _create_video_streaming_scenario_config(cls) -> Dict[str, Any]:
        """Create video streaming scenario configuration."""
        return {
            "simulation": {
                "simulation_time": 45.0,
                "time_step": 0.05,
                "output_file": "results/video_streaming_results.json",
                "enable_visualization": True
            },
            "network": {
                "num_gnbs": 3,
                "gnb_positions": [[-800, 0], [800, 0], [0, 1200]],
                "gnb_tx_power": 46.0,
                "frequency": 3500.0,
                "bandwidth": 100.0
            },
            "ues": {
                "num_ues": 12,
                "mobility_models": ["stationary"] * 4 + ["linear"] * 4 + ["random_walk"] * 4,
                "mobility_params": [
                    {} for _ in range(4)  # Stationary UEs
                ] + [
                    {"speed": 15.0, "direction": i * 0.785} for i in range(4)  # Linear motion
                ] + [
                    {"max_speed": 8.0, "direction_change_prob": 0.15} for _ in range(4)  # Random walk
                ]
            },
            "channel": {
                "propagation_model": "urban_macro",
                "enable_shadowing": True,
                "enable_fast_fading": True
            },
            "qos": {
                "default_qci": 75,  # High-bitrate video streaming
                "qos_flows": [
                    {"ue_id": i, "qci": 75, "guaranteed_bitrate_ul": 50000, "guaranteed_bitrate_dl": 100000}
                    for i in range(6)  # First 6 UEs have high-bitrate video flows
                ] + [
                    {"ue_id": i, "qci": 9}  # Remaining UEs have default flows
                    for i in range(6, 12)
                ]
            }
        }
    
    @classmethod
    def get_available_scenarios(cls) -> list[str]:
        """Get list of available predefined scenarios."""
        return ["basic", "mobility", "video_streaming"]