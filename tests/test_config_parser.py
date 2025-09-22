"""
Tests for Configuration Parser
"""

import unittest
import json
import tempfile
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.config_parser import ConfigParser
from src.core.config import SimulationConfig


class TestConfigParser(unittest.TestCase):
    """Test cases for Configuration Parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_config = {
            "simulation": {
                "simulation_time": 100.0,
                "random_seed": 42,
                "log_level": "INFO"
            },
            "network": {
                "num_gnbs": 3,
                "coverage_radius": 500.0
            },
            "ue": {
                "num_ues": 5,
                "mobility_model": "random_walk"
            },
            "traffic": {
                "qi_value": 2,
                "packet_size": 1500
            }
        }
    
    def test_valid_config_loading(self):
        """Test loading a valid configuration"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_config, f)
            temp_path = f.name
        
        try:
            config = ConfigParser.load_config(temp_path)
            self.assertIsInstance(config, SimulationConfig)
            self.assertEqual(config.simulation_time, 100.0)
            self.assertEqual(config.num_gnbs, 3)
            self.assertEqual(config.num_ues, 5)
            self.assertEqual(config.qi_value, 2)
        finally:
            os.unlink(temp_path)
    
    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            with self.assertRaises(json.JSONDecodeError):
                ConfigParser.load_config(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_missing_required_fields(self):
        """Test validation of missing required fields"""
        invalid_config = {
            "simulation": {
                "simulation_time": 100.0
            }
            # Missing network, ue, and traffic sections
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            with self.assertRaises(Exception):  # Should raise validation error
                ConfigParser.load_config(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config should pass
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_config, f)
            temp_path = f.name
        
        try:
            result = ConfigParser.validate_config_file(temp_path)
            self.assertTrue(result)
        finally:
            os.unlink(temp_path)
    
    def test_predefined_scenarios(self):
        """Test predefined scenario configurations"""
        scenarios = ConfigParser.get_scenario_configs()
        
        self.assertIn('single_gnb_stationary', scenarios)
        self.assertIn('multi_gnb_mobility', scenarios)
        self.assertIn('appendix_b_scenario', scenarios)
        
        # Test that scenarios are valid
        for name, scenario_config in scenarios.items():
            config = ConfigParser._dict_to_config(scenario_config)
            self.assertIsInstance(config, SimulationConfig)
    
    def test_config_merging(self):
        """Test configuration merging"""
        base_config = {
            "simulation": {"simulation_time": 100.0},
            "network": {"num_gnbs": 1}
        }
        
        override_config = {
            "simulation": {"random_seed": 42},
            "network": {"coverage_radius": 600.0}
        }
        
        merged = ConfigParser.merge_configs(base_config, override_config)
        
        self.assertEqual(merged["simulation"]["simulation_time"], 100.0)
        self.assertEqual(merged["simulation"]["random_seed"], 42)
        self.assertEqual(merged["network"]["num_gnbs"], 1)
        self.assertEqual(merged["network"]["coverage_radius"], 600.0)


if __name__ == '__main__':
    unittest.main()