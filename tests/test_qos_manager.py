"""
Tests for QoS Manager functionality
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.core.qos_manager import QoSManager, FiveQI, ResourceType


class TestQoSManager(unittest.TestCase):
    """Test cases for QoS Manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.qos_manager = QoSManager()
    
    def test_create_flow(self):
        """Test QoS flow creation"""
        # Test valid 5QI
        result = self.qos_manager.create_flow(1, 2)  # Conversational video
        self.assertTrue(result)
        self.assertEqual(self.qos_manager.get_active_flows_count(), 1)
        
        # Test invalid 5QI
        result = self.qos_manager.create_flow(2, 999)
        self.assertFalse(result)
        self.assertEqual(self.qos_manager.get_active_flows_count(), 1)
    
    def test_flow_characteristics(self):
        """Test flow characteristics retrieval"""
        self.qos_manager.create_flow(1, 2)  # Conversational video
        
        char = self.qos_manager.get_flow_characteristics(1)
        self.assertIsNotNone(char)
        self.assertEqual(char.priority_level, 40)
        self.assertEqual(char.packet_delay_budget_ms, 150)
        self.assertEqual(char.packet_error_rate, 1e-3)
        self.assertEqual(char.resource_type, ResourceType.GBR)
    
    def test_gbr_detection(self):
        """Test GBR flow detection"""
        self.qos_manager.create_flow(1, 2)  # GBR flow
        self.qos_manager.create_flow(2, 5)  # Non-GBR flow
        
        self.assertTrue(self.qos_manager.is_gbr_flow(1))
        self.assertFalse(self.qos_manager.is_gbr_flow(2))
    
    def test_remove_flow(self):
        """Test flow removal"""
        self.qos_manager.create_flow(1, 2)
        self.assertEqual(self.qos_manager.get_active_flows_count(), 1)
        
        result = self.qos_manager.remove_flow(1)
        self.assertTrue(result)
        self.assertEqual(self.qos_manager.get_active_flows_count(), 0)
        
        # Try to remove non-existent flow
        result = self.qos_manager.remove_flow(999)
        self.assertFalse(result)


class TestFiveQI(unittest.TestCase):
    """Test cases for 5QI implementation"""
    
    def test_valid_qi_values(self):
        """Test valid 5QI value handling"""
        # Test some standard values
        char_2 = FiveQI.get_qos_characteristics(2)
        self.assertIsNotNone(char_2)
        self.assertEqual(char_2.priority_level, 40)
        
        char_5 = FiveQI.get_qos_characteristics(5)
        self.assertIsNotNone(char_5)
        self.assertEqual(char_5.resource_type, ResourceType.NON_GBR)
    
    def test_invalid_qi_values(self):
        """Test invalid 5QI value handling"""
        char = FiveQI.get_qos_characteristics(999)
        self.assertIsNone(char)
    
    def test_gbr_classification(self):
        """Test GBR classification"""
        self.assertTrue(FiveQI.is_gbr(1))   # GBR
        self.assertTrue(FiveQI.is_gbr(82))  # Delay Critical GBR
        self.assertFalse(FiveQI.is_gbr(5))  # Non-GBR
    
    def test_get_all_qi_values(self):
        """Test getting all available 5QI values"""
        all_qis = FiveQI.get_all_qi_values()
        self.assertIn(1, all_qis)
        self.assertIn(2, all_qis)
        self.assertIn(5, all_qis)
        self.assertIn(82, all_qis)


if __name__ == '__main__':
    unittest.main()