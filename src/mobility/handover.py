"""
Handover management for 5G NR simulations.

This module implements handover procedures, measurements, and events
for maintaining connectivity during UE mobility.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import numpy as np


class HandoverType(Enum):
    """Types of handover procedures."""
    INTRA_FREQUENCY = "intra_frequency"
    INTER_FREQUENCY = "inter_frequency"
    INTER_RAT = "inter_rat"


class HandoverCause(Enum):
    """Causes for handover initiation."""
    COVERAGE = "coverage"  # Poor signal quality
    LOAD_BALANCING = "load_balancing"  # Load distribution
    INTERFERENCE = "interference"  # Interference avoidance
    TRAFFIC_STEERING = "traffic_steering"  # Service-based steering


@dataclass
class HandoverEvent:
    """Represents a handover event."""
    ue_id: int
    source_gnb_id: int
    target_gnb_id: int
    handover_type: HandoverType
    cause: HandoverCause
    trigger_time: float
    preparation_time: float = 0.0
    execution_time: float = 0.0
    completion_time: float = 0.0
    success: bool = False
    failure_reason: Optional[str] = None
    
    @property
    def total_interruption_time(self) -> float:
        """Calculate total interruption time in ms."""
        if not self.success:
            return 0.0
        return self.completion_time - self.trigger_time
    
    @property
    def handover_duration(self) -> float:
        """Calculate handover duration in ms."""
        if not self.success:
            return 0.0
        return self.completion_time - self.preparation_time


class HandoverManager:
    """Manages handover procedures for the simulation."""
    
    def __init__(self):
        self.handover_events: List[HandoverEvent] = []
        self.measurement_config = {
            'a3_offset': 3.0,  # dB
            'hysteresis': 1.0,  # dB
            'time_to_trigger': 160,  # ms
            'measurement_period': 200,  # ms
        }
        self.handover_timers = {
            'preparation_time': 50,  # ms
            'execution_time': 40,   # ms
            'completion_time': 10   # ms
        }
        self.ongoing_handovers: Dict[int, HandoverEvent] = {}  # ue_id -> event
        self.handover_statistics = {
            'total_attempts': 0,
            'successful_handovers': 0,
            'failed_handovers': 0,
            'ping_pong_handovers': 0
        }
    
    def evaluate_handover_conditions(self, ue_id: int, rsrp_measurements: List[Tuple[int, float]],
                                   current_gnb_id: int) -> Optional[Tuple[int, HandoverCause]]:
        """
        Evaluate if handover conditions are met for a UE.
        
        Args:
            ue_id: User Equipment ID
            rsrp_measurements: List of (gNB_id, RSRP) measurements
            current_gnb_id: Currently serving gNB ID
            
        Returns:
            Tuple of (target_gnb_id, cause) if handover should be triggered, None otherwise
        """
        if len(rsrp_measurements) < 2:
            return None
        
        # Find serving cell RSRP
        serving_rsrp = None
        for gnb_id, rsrp in rsrp_measurements:
            if gnb_id == current_gnb_id:
                serving_rsrp = rsrp
                break
        
        if serving_rsrp is None:
            return None
        
        # Check A3 event (Neighbour becomes offset better than serving)
        for gnb_id, rsrp in rsrp_measurements:
            if gnb_id != current_gnb_id:
                if rsrp > serving_rsrp + self.measurement_config['a3_offset'] + self.measurement_config['hysteresis']:
                    return gnb_id, HandoverCause.COVERAGE
        
        # Check for coverage-based handover (serving cell too weak)
        if serving_rsrp < -120:  # dBm threshold
            # Find best neighbor
            best_neighbor = max([m for m in rsrp_measurements if m[0] != current_gnb_id], 
                              key=lambda x: x[1], default=None)
            if best_neighbor and best_neighbor[1] > serving_rsrp + 10:
                return best_neighbor[0], HandoverCause.COVERAGE
        
        return None
    
    def initiate_handover(self, ue_id: int, source_gnb_id: int, target_gnb_id: int,
                         cause: HandoverCause, current_time: float) -> bool:
        """
        Initiate a handover procedure.
        
        Args:
            ue_id: User Equipment ID
            source_gnb_id: Source gNB ID
            target_gnb_id: Target gNB ID
            cause: Handover cause
            current_time: Current simulation time
            
        Returns:
            True if handover initiated successfully
        """
        # Check if UE already has ongoing handover
        if ue_id in self.ongoing_handovers:
            return False
        
        # Create handover event
        handover_event = HandoverEvent(
            ue_id=ue_id,
            source_gnb_id=source_gnb_id,
            target_gnb_id=target_gnb_id,
            handover_type=HandoverType.INTRA_FREQUENCY,  # Simplified
            cause=cause,
            trigger_time=current_time
        )
        
        self.ongoing_handovers[ue_id] = handover_event
        self.handover_statistics['total_attempts'] += 1
        
        return True
    
    def process_handover_procedures(self, current_time: float) -> List[Tuple[int, int, int]]:
        """
        Process ongoing handover procedures.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            List of completed handovers as (ue_id, source_gnb, target_gnb) tuples
        """
        completed_handovers = []
        to_remove = []
        
        for ue_id, event in self.ongoing_handovers.items():
            elapsed_time = current_time - event.trigger_time
            
            # Handover preparation phase
            if event.preparation_time == 0.0 and elapsed_time >= 0:
                event.preparation_time = current_time
            
            # Handover execution phase
            if (event.execution_time == 0.0 and 
                elapsed_time >= self.handover_timers['preparation_time']):
                event.execution_time = current_time
            
            # Handover completion phase
            if (event.completion_time == 0.0 and 
                elapsed_time >= (self.handover_timers['preparation_time'] + 
                               self.handover_timers['execution_time'])):
                
                # Simulate handover success/failure
                success_probability = self._calculate_handover_success_probability(event)
                if np.random.random() < success_probability:
                    event.success = True
                    event.completion_time = current_time
                    completed_handovers.append((ue_id, event.source_gnb_id, event.target_gnb_id))
                    self.handover_statistics['successful_handovers'] += 1
                else:
                    event.success = False
                    event.failure_reason = "Radio link failure"
                    event.completion_time = current_time
                    self.handover_statistics['failed_handovers'] += 1
                
                self.handover_events.append(event)
                to_remove.append(ue_id)
        
        # Remove completed handovers
        for ue_id in to_remove:
            del self.ongoing_handovers[ue_id]
        
        return completed_handovers
    
    def _calculate_handover_success_probability(self, event: HandoverEvent) -> float:
        """Calculate probability of handover success."""
        base_probability = 0.95  # 95% base success rate
        
        # Adjust based on handover cause
        if event.cause == HandoverCause.COVERAGE:
            return base_probability
        elif event.cause == HandoverCause.INTERFERENCE:
            return base_probability * 0.9
        elif event.cause == HandoverCause.LOAD_BALANCING:
            return base_probability * 0.98
        else:
            return base_probability
    
    def detect_ping_pong_handover(self, ue_id: int, source_gnb_id: int, 
                                 target_gnb_id: int, time_window: float = 10000) -> bool:
        """
        Detect ping-pong handover (back-and-forth between same cells).
        
        Args:
            ue_id: User Equipment ID
            source_gnb_id: Source gNB ID
            target_gnb_id: Target gNB ID
            time_window: Time window in ms to check for ping-pong
            
        Returns:
            True if ping-pong handover detected
        """
        current_time = time.time() * 1000  # Convert to ms
        
        # Check recent handovers for this UE
        recent_handovers = [
            event for event in self.handover_events
            if (event.ue_id == ue_id and 
                event.success and 
                current_time - event.completion_time <= time_window)
        ]
        
        # Look for back-and-forth pattern
        for event in recent_handovers:
            if (event.source_gnb_id == target_gnb_id and 
                event.target_gnb_id == source_gnb_id):
                self.handover_statistics['ping_pong_handovers'] += 1
                return True
        
        return False
    
    def get_handover_statistics(self) -> Dict:
        """Get comprehensive handover statistics."""
        total_attempts = self.handover_statistics['total_attempts']
        successful = self.handover_statistics['successful_handovers']
        failed = self.handover_statistics['failed_handovers']
        ping_pong = self.handover_statistics['ping_pong_handovers']
        
        if total_attempts == 0:
            return {
                'total_attempts': 0,
                'successful_handovers': 0,
                'failed_handovers': 0,
                'ping_pong_handovers': 0,
                'success_rate': 0.0,
                'failure_rate': 0.0,
                'ping_pong_rate': 0.0,
                'average_handover_duration': 0.0,
                'average_interruption_time': 0.0
            }
        
        successful_events = [e for e in self.handover_events if e.success]
        avg_duration = (sum(e.handover_duration for e in successful_events) / len(successful_events)
                       if successful_events else 0.0)
        avg_interruption = (sum(e.total_interruption_time for e in successful_events) / len(successful_events)
                           if successful_events else 0.0)
        
        return {
            'total_attempts': total_attempts,
            'successful_handovers': successful,
            'failed_handovers': failed,
            'ping_pong_handovers': ping_pong,
            'success_rate': successful / total_attempts,
            'failure_rate': failed / total_attempts,
            'ping_pong_rate': ping_pong / successful if successful > 0 else 0.0,
            'average_handover_duration': avg_duration,
            'average_interruption_time': avg_interruption
        }
    
    def get_handover_events_by_ue(self, ue_id: int) -> List[HandoverEvent]:
        """Get all handover events for a specific UE."""
        return [event for event in self.handover_events if event.ue_id == ue_id]
    
    def get_handover_events_by_cause(self, cause: HandoverCause) -> List[HandoverEvent]:
        """Get all handover events for a specific cause."""
        return [event for event in self.handover_events if event.cause == cause]
    
    def reset_statistics(self):
        """Reset handover statistics."""
        self.handover_events.clear()
        self.ongoing_handovers.clear()
        self.handover_statistics = {
            'total_attempts': 0,
            'successful_handovers': 0,
            'failed_handovers': 0,
            'ping_pong_handovers': 0
        }