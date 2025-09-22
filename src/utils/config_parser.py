"""
Configuration Parser for 5G NR Simulation Framework

This module handles loading and validation of simulation configuration files.
"""

import json
import jsonschema
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..core.config import SimulationConfig

logger = logging.getLogger(__name__)


class ConfigParser:
    """
    Configuration parser and validator for simulation parameters
    """
    
    # JSON Schema for configuration validation
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "simulation": {
                "type": "object",
                "properties": {
                    "simulation_time": {"type": "number", "minimum": 0.1},
                    "random_seed": {"type": ["integer", "null"]},
                    "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                    "output_directory": {"type": "string"},
                    "enable_plots": {"type": "boolean"}
                },
                "required": ["simulation_time"],
                "additionalProperties": False
            },
            "network": {
                "type": "object",
                "properties": {
                    "num_gnbs": {"type": "integer", "minimum": 1},
                    "coverage_radius": {"type": "number", "minimum": 10},
                    "carrier_frequency": {"type": "number", "minimum": 1e9},
                    "bandwidth": {"type": "number", "minimum": 1e6},
                    "gnb_positions": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    }
                },
                "required": ["num_gnbs"],
                "additionalProperties": False
            },
            "ue": {
                "type": "object",
                "properties": {
                    "num_ues": {"type": "integer", "minimum": 1},
                    "initial_positions": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    },
                    "mobility_model": {
                        "type": "string",
                        "enum": ["stationary", "random_walk", "random_waypoint", "linear", "circular", "manhattan"]
                    },
                    "mobility_speed": {"type": "number", "minimum": 0}
                },
                "required": ["num_ues"],
                "additionalProperties": False
            },
            "traffic": {
                "type": "object",
                "properties": {
                    "traffic_model": {"type": "string"},
                    "packet_size": {"type": "integer", "minimum": 64},
                    "packet_interval": {"type": "number", "minimum": 0.001},
                    "qi_value": {"type": "integer", "minimum": 1, "maximum": 85}
                },
                "required": ["qi_value"],
                "additionalProperties": False
            },
            "handover": {
                "type": "object",
                "properties": {
                    "hysteresis": {"type": "number", "minimum": 0},
                    "time_to_trigger": {"type": "number", "minimum": 0.001},
                    "signal_threshold": {"type": "number", "maximum": -50}
                },
                "additionalProperties": False
            },
            "channel": {
                "type": "object", 
                "properties": {
                    "channel_type": {
                        "type": "string",
                        "enum": ["free_space", "urban_macro", "urban_micro", "indoor", "rural_macro"]
                    },
                    "temperature": {"type": "number", "minimum": 200}
                },
                "additionalProperties": False
            }
        },
        "required": ["simulation", "network", "ue", "traffic"],
        "additionalProperties": False
    }

    @classmethod
    def load_config(cls, config_path: str) -> SimulationConfig:
        """
        Load configuration from JSON file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            SimulationConfig object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If JSON is invalid
            jsonschema.ValidationError: If config doesn't match schema
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        logger.info(f"Loading configuration from {config_path}")
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
            
        # Validate configuration against schema
        try:
            jsonschema.validate(config_data, cls.CONFIG_SCHEMA)
        except jsonschema.ValidationError as e:
            logger.error(f"Configuration validation error: {e.message}")
            raise
            
        logger.info("Configuration loaded and validated successfully")
        
        # Convert to SimulationConfig object
        return cls._dict_to_config(config_data)

    @classmethod
    def _dict_to_config(cls, config_data: Dict[str, Any]) -> SimulationConfig:
        """Convert configuration dictionary to SimulationConfig object"""
        
        # Extract sections with defaults
        sim_config = config_data.get('simulation', {})
        net_config = config_data.get('network', {})
        ue_config = config_data.get('ue', {})
        traffic_config = config_data.get('traffic', {})
        
        # Create SimulationConfig with all parameters
        config = SimulationConfig(
            # Simulation parameters
            simulation_time=sim_config.get('simulation_time', 100.0),
            random_seed=sim_config.get('random_seed'),
            log_level=sim_config.get('log_level', 'INFO'),
            output_directory=sim_config.get('output_directory', 'results'),
            enable_plots=sim_config.get('enable_plots', True),
            
            # Network parameters
            num_gnbs=net_config.get('num_gnbs', 1),
            coverage_radius=net_config.get('coverage_radius', 500.0),
            carrier_frequency=net_config.get('carrier_frequency', 3.5e9),
            bandwidth=net_config.get('bandwidth', 100e6),
            
            # UE parameters
            num_ues=ue_config.get('num_ues', 1),
            initial_positions=ue_config.get('initial_positions'),
            mobility_model=ue_config.get('mobility_model', 'random_walk'),
            mobility_speed=ue_config.get('mobility_speed', 1.4),
            
            # Traffic parameters
            traffic_model=traffic_config.get('traffic_model', 'video_streaming'),
            packet_size=traffic_config.get('packet_size', 1500),
            packet_interval=traffic_config.get('packet_interval', 0.033),
            qi_value=traffic_config.get('qi_value', 2)
        )
        
        return config

    @classmethod
    def create_default_config(cls, output_path: str = "config_template.json"):
        """Create a default configuration file template"""
        
        default_config = {
            "simulation": {
                "simulation_time": 100.0,
                "random_seed": 42,
                "log_level": "INFO",
                "output_directory": "results",
                "enable_plots": True
            },
            "network": {
                "num_gnbs": 3,
                "coverage_radius": 500.0,
                "carrier_frequency": 3.5e9,
                "bandwidth": 100e6,
                "gnb_positions": [
                    [0, 0],
                    [800, 0],
                    [400, 692]
                ]
            },
            "ue": {
                "num_ues": 5,
                "initial_positions": [
                    [100, 100],
                    [200, 150],
                    [300, 200],
                    [600, 100],
                    [500, 400]
                ],
                "mobility_model": "random_walk",
                "mobility_speed": 1.4
            },
            "traffic": {
                "traffic_model": "video_streaming",
                "packet_size": 1500,
                "packet_interval": 0.033,
                "qi_value": 2
            },
            "handover": {
                "hysteresis": 3.0,
                "time_to_trigger": 0.16,
                "signal_threshold": -110.0
            },
            "channel": {
                "channel_type": "urban_macro",
                "temperature": 290.0
            }
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Default configuration template created: {output_path}")
        except IOError as e:
            logger.error(f"Failed to create configuration template: {e}")
            raise

    @classmethod
    def validate_config_file(cls, config_path: str) -> bool:
        """
        Validate configuration file without loading
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            cls.load_config(config_path)
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    @classmethod
    def get_scenario_configs(cls) -> Dict[str, Dict]:
        """Get predefined scenario configurations"""
        
        scenarios = {
            "single_gnb_stationary": {
                "simulation": {
                    "simulation_time": 60.0,
                    "random_seed": 42,
                    "log_level": "INFO",
                    "output_directory": "results/single_gnb_stationary",
                    "enable_plots": True
                },
                "network": {
                    "num_gnbs": 1,
                    "coverage_radius": 500.0,
                    "carrier_frequency": 3.5e9,
                    "bandwidth": 100e6
                },
                "ue": {
                    "num_ues": 1,
                    "initial_positions": [[100, 100]],
                    "mobility_model": "stationary",
                    "mobility_speed": 0.0
                },
                "traffic": {
                    "traffic_model": "video_streaming",
                    "packet_size": 1500,
                    "packet_interval": 0.033,
                    "qi_value": 2
                }
            },
            
            "multi_gnb_mobility": {
                "simulation": {
                    "simulation_time": 120.0,
                    "random_seed": 123,
                    "log_level": "INFO",
                    "output_directory": "results/multi_gnb_mobility",
                    "enable_plots": True
                },
                "network": {
                    "num_gnbs": 3,
                    "coverage_radius": 400.0,
                    "carrier_frequency": 3.5e9,
                    "bandwidth": 100e6
                },
                "ue": {
                    "num_ues": 5,
                    "mobility_model": "random_walk",
                    "mobility_speed": 3.0
                },
                "traffic": {
                    "traffic_model": "video_streaming",
                    "packet_size": 1500,
                    "packet_interval": 0.033,
                    "qi_value": 2
                },
                "handover": {
                    "hysteresis": 2.0,
                    "time_to_trigger": 0.16,
                    "signal_threshold": -110.0
                }
            },
            
            "handover_evaluation": {
                "simulation": {
                    "simulation_time": 200.0,
                    "random_seed": 456,
                    "log_level": "INFO",
                    "output_directory": "results/handover_evaluation",
                    "enable_plots": True
                },
                "network": {
                    "num_gnbs": 4,
                    "coverage_radius": 300.0,
                    "carrier_frequency": 3.5e9,
                    "bandwidth": 100e6
                },
                "ue": {
                    "num_ues": 10,
                    "mobility_model": "linear",
                    "mobility_speed": 5.0
                },
                "traffic": {
                    "traffic_model": "video_streaming",
                    "packet_size": 1500,
                    "packet_interval": 0.020,
                    "qi_value": 4
                },
                "handover": {
                    "hysteresis": 4.0,
                    "time_to_trigger": 0.32,
                    "signal_threshold": -105.0
                }
            },
            
            "appendix_b_scenario": {
                "simulation": {
                    "simulation_time": 300.0,
                    "random_seed": 789,
                    "log_level": "INFO",
                    "output_directory": "results/appendix_b",
                    "enable_plots": True
                },
                "network": {
                    "num_gnbs": 7,
                    "coverage_radius": 500.0,
                    "carrier_frequency": 3.5e9,
                    "bandwidth": 100e6
                },
                "ue": {
                    "num_ues": 20,
                    "mobility_model": "random_waypoint",
                    "mobility_speed": 1.4
                },
                "traffic": {
                    "traffic_model": "mixed_services",
                    "packet_size": 1500,
                    "packet_interval": 0.033,
                    "qi_value": 1
                },
                "handover": {
                    "hysteresis": 3.0,
                    "time_to_trigger": 0.16,
                    "signal_threshold": -110.0
                },
                "channel": {
                    "channel_type": "urban_macro",
                    "temperature": 290.0
                }
            }
        }
        
        return scenarios

    @classmethod
    def create_scenario_configs(cls, output_dir: str = "scenarios"):
        """Create all predefined scenario configuration files"""
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        scenarios = cls.get_scenario_configs()
        
        for scenario_name, config in scenarios.items():
            config_file = output_path / f"{scenario_name}.json"
            
            try:
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                logger.info(f"Created scenario config: {config_file}")
            except IOError as e:
                logger.error(f"Failed to create scenario {scenario_name}: {e}")

    @classmethod
    def merge_configs(cls, base_config: Dict, override_config: Dict) -> Dict:
        """
        Merge two configuration dictionaries
        
        Args:
            base_config: Base configuration
            override_config: Override values
            
        Returns:
            Merged configuration
        """
        def deep_merge(base: Dict, override: Dict) -> Dict:
            result = base.copy()
            
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
                    
            return result
            
        return deep_merge(base_config, override_config)