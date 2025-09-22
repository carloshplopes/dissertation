"""
Tests for QoS functionality.
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.qos.qci_mapping import QCIMapping, QoSCharacteristics, ResourceType
from src.qos.qos_manager import QoSManager, QoSFlow


class TestQCIMapping(unittest.TestCase):
    """Test QCI mapping functionality."""
    
    def test_get_qos_characteristics(self):
        """Test getting QoS characteristics for valid QCI."""
        char = QCIMapping.get_qos_characteristics(1)
        self.assertIsInstance(char, QoSCharacteristics)
        self.assertEqual(char.resource_type, ResourceType.GBR)
        self.assertEqual(char.priority_level, 20)
        self.assertEqual(char.packet_delay_budget, 100)
        self.assertEqual(char.packet_error_rate, 1e-2)
    
    def test_invalid_qci(self):
        """Test handling of invalid QCI values."""
        with self.assertRaises(ValueError):
            QCIMapping.get_qos_characteristics(999)
    
    def test_is_gbr_service(self):
        """Test GBR service detection."""
        self.assertTrue(QCIMapping.is_gbr_service(1))  # GBR
        self.assertFalse(QCIMapping.is_gbr_service(9))  # Non-GBR
    
    def test_get_supported_qcis(self):
        """Test getting supported QCI list."""
        qcis = QCIMapping.get_supported_qcis()
        self.assertIsInstance(qcis, list)
        self.assertIn(1, qcis)
        self.assertIn(9, qcis)


class TestQoSManager(unittest.TestCase):
    """Test QoS Manager functionality."""
    
    def setUp(self):
        self.qos_manager = QoSManager()
    
    def test_create_flow(self):
        """Test creating QoS flows."""
        flow = self.qos_manager.create_flow(qci=9, ue_id=1)
        self.assertIsInstance(flow, QoSFlow)
        self.assertEqual(flow.qci, 9)
        self.assertEqual(flow.ue_id, 1)
        self.assertTrue(flow.active)
    
    def test_remove_flow(self):
        """Test removing QoS flows."""
        flow = self.qos_manager.create_flow(qci=9, ue_id=1)
        flow_id = flow.flow_id
        
        success = self.qos_manager.remove_flow(flow_id)
        self.assertTrue(success)
        
        # Try to get removed flow
        retrieved_flow = self.qos_manager.get_flow(flow_id)
        self.assertIsNone(retrieved_flow)
    
    def test_get_flows_by_ue(self):
        """Test getting flows by UE ID."""
        ue_id = 1
        flow1 = self.qos_manager.create_flow(qci=9, ue_id=ue_id)
        flow2 = self.qos_manager.create_flow(qci=1, ue_id=ue_id)
        
        flows = self.qos_manager.get_flows_by_ue(ue_id)
        self.assertEqual(len(flows), 2)
        self.assertIn(flow1, flows)
        self.assertIn(flow2, flows)
    
    def test_calculate_scheduling_priority(self):
        """Test scheduling priority calculation."""
        flow = self.qos_manager.create_flow(qci=1, ue_id=1)  # High priority QCI
        priority = self.qos_manager.calculate_scheduling_priority(flow.flow_id)
        self.assertIsInstance(priority, float)
        self.assertGreaterEqual(priority, 0)
    
    def test_allocate_resources(self):
        """Test resource allocation."""
        # Create some flows
        self.qos_manager.create_flow(qci=1, ue_id=1)  # GBR
        self.qos_manager.create_flow(qci=9, ue_id=2)  # Non-GBR
        
        allocations = self.qos_manager.allocate_resources()
        self.assertIsInstance(allocations, dict)
    
    def test_system_metrics(self):
        """Test system metrics calculation."""
        # Create some flows
        self.qos_manager.create_flow(qci=1, ue_id=1)
        self.qos_manager.create_flow(qci=9, ue_id=2)
        
        metrics = self.qos_manager.get_system_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_flows', metrics)
        self.assertIn('active_flows', metrics)
        self.assertIn('gbr_flows', metrics)
        self.assertEqual(metrics['total_flows'], 2)
        self.assertEqual(metrics['gbr_flows'], 1)


if __name__ == '__main__':
    unittest.main()