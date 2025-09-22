"""
Tests for mobility functionality.
"""

import unittest
import sys
import os
import math

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.mobility.user_equipment import UserEquipment, Position, MobilityModel
from src.mobility.handover import HandoverManager, HandoverEvent, HandoverCause, HandoverType


class TestPosition(unittest.TestCase):
    """Test Position class."""
    
    def test_distance_calculation(self):
        """Test distance calculation between positions."""
        pos1 = Position(0, 0)
        pos2 = Position(3, 4)
        distance = pos1.distance_to(pos2)
        self.assertAlmostEqual(distance, 5.0, places=5)
    
    def test_position_arithmetic(self):
        """Test position addition and subtraction."""
        pos1 = Position(1, 2)
        pos2 = Position(3, 4)
        
        result_add = pos1 + pos2
        self.assertEqual(result_add.x, 4)
        self.assertEqual(result_add.y, 6)
        
        result_sub = pos2 - pos1
        self.assertEqual(result_sub.x, 2)
        self.assertEqual(result_sub.y, 2)


class TestUserEquipment(unittest.TestCase):
    """Test UserEquipment functionality."""
    
    def test_stationary_ue(self):
        """Test stationary UE behavior."""
        initial_pos = Position(10, 20)
        ue = UserEquipment(ue_id=1, initial_position=initial_pos, 
                          mobility_model=MobilityModel.STATIONARY)
        
        # Update position multiple times
        for _ in range(10):
            ue.update_position(0.1)
        
        # Should remain at initial position
        self.assertEqual(ue.current_position.x, initial_pos.x)
        self.assertEqual(ue.current_position.y, initial_pos.y)
    
    def test_linear_ue(self):
        """Test linear mobility UE."""
        initial_pos = Position(0, 0)
        ue = UserEquipment(ue_id=1, initial_position=initial_pos,
                          mobility_model=MobilityModel.LINEAR,
                          speed=10.0, direction=0.0)  # Moving in +x direction
        
        # Update position
        ue.update_position(1.0)  # 1 second
        
        # Should have moved 10 meters in x direction
        self.assertAlmostEqual(ue.current_position.x, 10.0, places=5)
        self.assertAlmostEqual(ue.current_position.y, 0.0, places=5)
    
    def test_rsrp_calculation(self):
        """Test RSRP calculation."""
        ue = UserEquipment(ue_id=1, initial_position=Position(0, 0))
        gnb_position = Position(100, 0)  # 100m away
        
        rsrp = ue.calculate_rsrp(gnb_position, tx_power=46.0)
        self.assertIsInstance(rsrp, float)
        self.assertLess(rsrp, 46.0)  # Should be less than TX power due to path loss
    
    def test_trajectory_tracking(self):
        """Test trajectory tracking."""
        ue = UserEquipment(ue_id=1, initial_position=Position(0, 0),
                          mobility_model=MobilityModel.LINEAR,
                          speed=1.0, direction=0.0)
        
        initial_length = len(ue.trajectory)
        
        # Move UE
        for _ in range(5):
            ue.update_position(1.0)
        
        # Trajectory should have grown
        self.assertEqual(len(ue.trajectory), initial_length + 5)
    
    def test_rsrp_measurements_update(self):
        """Test RSRP measurements update."""
        ue = UserEquipment(ue_id=1, initial_position=Position(0, 0))
        
        gnb_positions = {
            0: Position(100, 0),
            1: Position(0, 100),
            2: Position(-100, 0)
        }
        
        ue.update_rsrp_measurements(gnb_positions)
        
        # Should have measurements for all gNBs
        self.assertEqual(len(ue.rsrp_measurements), 3)
        
        # Should be sorted by RSRP (best first)
        rsrp_values = [rsrp for _, rsrp in ue.rsrp_measurements]
        self.assertEqual(rsrp_values, sorted(rsrp_values, reverse=True))
    
    def test_best_serving_gnb(self):
        """Test best serving gNB selection."""
        ue = UserEquipment(ue_id=1, initial_position=Position(0, 0))
        
        gnb_positions = {
            0: Position(50, 0),   # Closest
            1: Position(100, 0),  # Farther
            2: Position(200, 0)   # Farthest
        }
        
        ue.update_rsrp_measurements(gnb_positions)
        best_gnb = ue.get_best_serving_gnb()
        
        # Should select the closest gNB (gNB 0)
        self.assertEqual(best_gnb, 0)


class TestHandoverManager(unittest.TestCase):
    """Test HandoverManager functionality."""
    
    def setUp(self):
        self.handover_manager = HandoverManager()
    
    def test_evaluate_handover_conditions(self):
        """Test handover condition evaluation."""
        # Mock RSRP measurements (gNB_id, RSRP)
        rsrp_measurements = [
            (0, -80),  # Current serving
            (1, -75),  # Better neighbor
            (2, -90)   # Worse neighbor
        ]
        
        result = self.handover_manager.evaluate_handover_conditions(
            ue_id=1, rsrp_measurements=rsrp_measurements, current_gnb_id=0
        )
        
        # Should trigger handover to gNB 1 (better signal)
        self.assertIsNotNone(result)
        target_gnb_id, cause = result
        self.assertEqual(target_gnb_id, 1)
        self.assertEqual(cause, HandoverCause.COVERAGE)
    
    def test_initiate_handover(self):
        """Test handover initiation."""
        success = self.handover_manager.initiate_handover(
            ue_id=1, source_gnb_id=0, target_gnb_id=1,
            cause=HandoverCause.COVERAGE, current_time=1000.0
        )
        
        self.assertTrue(success)
        self.assertIn(1, self.handover_manager.ongoing_handovers)
        
        # Check handover event
        event = self.handover_manager.ongoing_handovers[1]
        self.assertEqual(event.ue_id, 1)
        self.assertEqual(event.source_gnb_id, 0)
        self.assertEqual(event.target_gnb_id, 1)
        self.assertEqual(event.cause, HandoverCause.COVERAGE)
    
    def test_process_handover_procedures(self):
        """Test handover procedure processing."""
        # Initiate handover
        self.handover_manager.initiate_handover(
            ue_id=1, source_gnb_id=0, target_gnb_id=1,
            cause=HandoverCause.COVERAGE, current_time=0.0
        )
        
        # Process after enough time has passed
        completed = self.handover_manager.process_handover_procedures(200.0)
        
        # Should have completed handovers
        if completed:
            ue_id, source_gnb, target_gnb = completed[0]
            self.assertEqual(ue_id, 1)
            self.assertEqual(source_gnb, 0)
            self.assertEqual(target_gnb, 1)
    
    def test_handover_statistics(self):
        """Test handover statistics collection."""
        # Initial statistics
        stats = self.handover_manager.get_handover_statistics()
        self.assertEqual(stats['total_attempts'], 0)
        
        # Initiate handover
        self.handover_manager.initiate_handover(
            ue_id=1, source_gnb_id=0, target_gnb_id=1,
            cause=HandoverCause.COVERAGE, current_time=0.0
        )
        
        # Check updated statistics
        stats = self.handover_manager.get_handover_statistics()
        self.assertEqual(stats['total_attempts'], 1)


if __name__ == '__main__':
    unittest.main()