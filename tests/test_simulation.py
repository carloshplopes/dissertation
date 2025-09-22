"""
Tests for simulation functionality.
"""

import unittest
import sys
import os
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.simulation.engine import SimulationEngine, SimulationConfig
from src.simulation.metrics import MetricsCollector, SimulationResults
from src.utils.config import ConfigManager


class TestSimulationConfig(unittest.TestCase):
    """Test SimulationConfig functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SimulationConfig()
        self.assertEqual(config.simulation_time, 60.0)
        self.assertEqual(config.time_step, 0.1)
        self.assertEqual(config.num_gnbs, 3)
        self.assertEqual(config.num_ues, 10)
        self.assertEqual(config.frequency, 3500.0)
        self.assertEqual(config.bandwidth, 100.0)


class TestSimulationEngine(unittest.TestCase):
    """Test SimulationEngine functionality."""
    
    def test_engine_initialization(self):
        """Test simulation engine initialization."""
        config = SimulationConfig(
            simulation_time=5.0,
            time_step=0.5,
            num_gnbs=2,
            num_ues=5
        )
        
        engine = SimulationEngine(config)
        
        # Check initialization
        self.assertEqual(len(engine.gnbs), 2)
        self.assertEqual(len(engine.ues), 5)
        self.assertIsNotNone(engine.channel_model)
        self.assertIsNotNone(engine.handover_manager)
        self.assertIsNotNone(engine.metrics_collector)
        self.assertEqual(engine.time_steps, 10)  # 5.0 / 0.5
    
    def test_short_simulation_run(self):
        """Test running a short simulation."""
        config = SimulationConfig(
            simulation_time=1.0,
            time_step=0.5,
            num_gnbs=2,
            num_ues=3
        )
        
        engine = SimulationEngine(config)
        results = engine.run_simulation()
        
        # Check results
        self.assertIsInstance(results, SimulationResults)
        self.assertIsNotNone(results.summary_statistics)
        self.assertGreater(results.execution_time, 0)


class TestMetricsCollector(unittest.TestCase):
    """Test MetricsCollector functionality."""
    
    def setUp(self):
        self.collector = MetricsCollector()
    
    def test_add_measurement(self):
        """Test adding measurements."""
        measurement = {
            'timestamp': 0.0,
            'system_metrics': {
                'total_ues': 10,
                'connected_ues': 8,
                'average_throughput_dl_mbps': 50.0
            },
            'ue_metrics': {},
            'gnb_metrics': {}
        }
        
        self.collector.add_measurement(measurement)
        self.assertEqual(len(self.collector.measurements), 1)
        self.assertEqual(len(self.collector.time_series_data['throughput_dl']), 1)
    
    def test_generate_results(self):
        """Test results generation."""
        # Add some dummy measurements
        for i in range(5):
            measurement = {
                'timestamp': float(i),
                'system_metrics': {
                    'total_ues': 10,
                    'connected_ues': 8 + i,
                    'average_throughput_dl_mbps': 50.0 + i * 10,
                    'handover_statistics': {'total_attempts': i}
                },
                'ue_metrics': {
                    0: {
                        'position': [i * 10, 0],
                        'throughput_dl_mbps': 20.0 + i * 5,
                        'speed': 5.0
                    }
                },
                'gnb_metrics': {
                    0: {
                        'position': [0, 0],
                        'connected_ues': 5,
                        'resource_utilization': 0.5 + i * 0.1
                    }
                }
            }
            self.collector.add_measurement(measurement)
        
        results = self.collector.generate_results()
        
        # Check results structure
        self.assertIsInstance(results, SimulationResults)
        self.assertIsInstance(results.summary_statistics, dict)
        self.assertIsInstance(results.ue_statistics, dict)
        self.assertIsInstance(results.gnb_statistics, dict)
        self.assertFalse(results.metrics_data.empty)
    
    def test_export_results(self):
        """Test results export."""
        # Add a dummy measurement
        measurement = {
            'timestamp': 0.0,
            'system_metrics': {'total_ues': 10},
            'ue_metrics': {},
            'gnb_metrics': {}
        }
        self.collector.add_measurement(measurement)
        
        results = self.collector.generate_results()
        
        # Test CSV export
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            try:
                self.collector.export_results(results, f.name)
                self.assertTrue(os.path.exists(f.name))
            finally:
                os.unlink(f.name)
        
        # Test JSON export
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            try:
                self.collector.export_results(results, f.name)
                self.assertTrue(os.path.exists(f.name))
            finally:
                os.unlink(f.name)


class TestConfigManager(unittest.TestCase):
    """Test ConfigManager functionality."""
    
    def test_create_default_config(self):
        """Test creating default configurations."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            try:
                ConfigManager.create_default_config(f.name, 'basic')
                self.assertTrue(os.path.exists(f.name))
                
                # Try to load it back
                config = ConfigManager.load_config(f.name)
                self.assertIsInstance(config, SimulationConfig)
            finally:
                os.unlink(f.name)
    
    def test_validate_config(self):
        """Test configuration validation."""
        valid_config = {
            'simulation': {
                'simulation_time': 30.0,
                'time_step': 0.1
            },
            'network': {
                'num_gnbs': 3
            },
            'ues': {
                'num_ues': 10
            }
        }
        
        # Should not raise exception
        ConfigManager.validate_config(valid_config)
        
        # Invalid config should raise exception
        invalid_config = {
            'simulation': {
                'simulation_time': -1.0,  # Invalid negative time
                'time_step': 0.1
            },
            'network': {
                'num_gnbs': 3
            },
            'ues': {
                'num_ues': 10
            }
        }
        
        with self.assertRaises(Exception):
            ConfigManager.validate_config(invalid_config)
    
    def test_available_scenarios(self):
        """Test getting available scenarios."""
        scenarios = ConfigManager.get_available_scenarios()
        self.assertIsInstance(scenarios, list)
        self.assertIn('basic', scenarios)
        self.assertIn('mobility', scenarios)
        self.assertIn('video_streaming', scenarios)


if __name__ == '__main__':
    unittest.main()