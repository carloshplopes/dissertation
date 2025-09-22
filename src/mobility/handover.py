"""
Handover Management for 5G NR Simulation

This module implements handover procedures and decision algorithms
for seamless mobility support in 5G networks.
"""

import simpy
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class HandoverType(Enum):
    """Types of handover procedures"""
    INTRA_FREQUENCY = "intra_frequency"  # Same frequency
    INTER_FREQUENCY = "inter_frequency"  # Different frequency
    INTER_RAT = "inter_rat"              # Different Radio Access Technology


class HandoverCause(Enum):
    """Reasons for handover initiation"""
    COVERAGE = "coverage"                # Moving out of coverage
    QOS_DEGRADATION = "qos_degradation" # Quality of service issues
    LOAD_BALANCING = "load_balancing"   # Network load balancing
    INTERFERENCE = "interference"        # High interference
    USER_PREFERENCE = "user_preference" # User or network preference


@dataclass
class HandoverEvent:
    """Handover event record"""
    timestamp: float
    ue_id: int
    source_gnb_id: Optional[int]
    target_gnb_id: int
    handover_type: HandoverType
    cause: HandoverCause
    duration: float  # Handover execution time
    success: bool
    signal_strength_before: float
    signal_strength_after: float
    position: Tuple[float, float]


@dataclass
class HandoverMeasurement:
    """Measurement report for handover decisions"""
    gnb_id: int
    signal_strength: float  # dBm
    signal_quality: float   # SINR in dB
    distance: float         # meters
    timestamp: float


class HandoverManager:
    """
    Handover Management System for 5G NR Networks
    
    Implements measurement-based handover decisions with hysteresis
    and time-to-trigger mechanisms.
    """
    
    def __init__(self, env: simpy.Environment):
        self.env = env
        
        # Handover parameters
        self.measurement_interval = 0.5  # 500ms measurement reports
        self.hysteresis = 3.0           # 3 dB hysteresis
        self.time_to_trigger = 0.16     # 160ms time-to-trigger
        
        # Thresholds
        self.signal_threshold = -110.0   # dBm - minimum signal for connection
        self.handover_margin = 2.0       # dB - margin for handover decision
        
        # Handover execution parameters
        self.preparation_time = 0.05     # 50ms preparation
        self.execution_time = 0.02       # 20ms execution
        self.completion_time = 0.01      # 10ms completion
        
        # State tracking
        self.measurement_reports: Dict[int, List[HandoverMeasurement]] = {}
        self.handover_triggers: Dict[int, Dict] = {}  # UE_ID -> trigger info
        self.active_handovers: Dict[int, Dict] = {}   # UE_ID -> handover state
        self.handover_history: List[HandoverEvent] = []
        
        # Statistics
        self.stats = {
            'total_handovers': 0,
            'successful_handovers': 0,
            'failed_handovers': 0,
            'ping_pong_handovers': 0,
            'average_handover_time': 0.0
        }
        
        logger.info("Handover Manager initialized")

    def add_measurement_report(self, ue_id: int, gnb_measurements: List[HandoverMeasurement]):
        """Add measurement report from UE"""
        if ue_id not in self.measurement_reports:
            self.measurement_reports[ue_id] = []
            
        # Store measurements
        self.measurement_reports[ue_id].extend(gnb_measurements)
        
        # Keep only recent measurements (last 5 seconds)
        cutoff_time = self.env.now - 5.0
        self.measurement_reports[ue_id] = [
            m for m in self.measurement_reports[ue_id] 
            if m.timestamp > cutoff_time
        ]
        
        # Evaluate handover conditions
        self._evaluate_handover_conditions(ue_id)

    def _evaluate_handover_conditions(self, ue_id: int):
        """Evaluate if handover should be triggered"""
        if ue_id not in self.measurement_reports:
            return
            
        measurements = self.measurement_reports[ue_id]
        if not measurements:
            return
            
        # Get current serving cell (strongest signal)
        current_best = max(measurements, key=lambda m: m.signal_strength)
        
        # Check if UE is already in handover
        if ue_id in self.active_handovers:
            logger.debug(f"UE {ue_id} already in handover, skipping evaluation")
            return
            
        # Find better target cells
        potential_targets = [
            m for m in measurements 
            if (m.gnb_id != current_best.gnb_id and 
                m.signal_strength > current_best.signal_strength + self.hysteresis + self.handover_margin)
        ]
        
        if not potential_targets:
            # No better targets, clear any existing triggers
            if ue_id in self.handover_triggers:
                del self.handover_triggers[ue_id]
            return
            
        # Select best target
        best_target = max(potential_targets, key=lambda m: m.signal_strength)
        
        # Check time-to-trigger
        trigger_key = f"{current_best.gnb_id}_{best_target.gnb_id}"
        
        if ue_id not in self.handover_triggers:
            self.handover_triggers[ue_id] = {}
            
        if trigger_key not in self.handover_triggers[ue_id]:
            # Start time-to-trigger timer
            self.handover_triggers[ue_id][trigger_key] = {
                'start_time': self.env.now,
                'source_gnb': current_best.gnb_id,
                'target_gnb': best_target.gnb_id,
                'trigger_signal': best_target.signal_strength
            }
            logger.debug(f"Started handover trigger for UE {ue_id}: gNB {current_best.gnb_id} -> {best_target.gnb_id}")
            
        else:
            # Check if time-to-trigger has elapsed
            trigger_info = self.handover_triggers[ue_id][trigger_key]
            elapsed_time = self.env.now - trigger_info['start_time']
            
            if elapsed_time >= self.time_to_trigger:
                # Trigger handover
                self._initiate_handover(ue_id, trigger_info['source_gnb'], 
                                      trigger_info['target_gnb'], HandoverCause.QOS_DEGRADATION)
                # Clear trigger
                del self.handover_triggers[ue_id][trigger_key]

    def _initiate_handover(self, ue_id: int, source_gnb_id: Optional[int], 
                          target_gnb_id: int, cause: HandoverCause):
        """Initiate handover procedure"""
        if ue_id in self.active_handovers:
            logger.warning(f"UE {ue_id} already in handover, ignoring new request")
            return
            
        # Start handover process
        handover_state = {
            'ue_id': ue_id,
            'source_gnb': source_gnb_id,
            'target_gnb': target_gnb_id,
            'cause': cause,
            'start_time': self.env.now,
            'phase': 'preparation'
        }
        
        self.active_handovers[ue_id] = handover_state
        
        logger.info(f"Initiated handover for UE {ue_id}: gNB {source_gnb_id} -> {target_gnb_id} "
                   f"(cause: {cause.value})")
        
        # Start handover execution process
        self.env.process(self._execute_handover(ue_id))

    def _execute_handover(self, ue_id: int):
        """Execute handover procedure"""
        if ue_id not in self.active_handovers:
            return
            
        handover_state = self.active_handovers[ue_id]
        start_time = handover_state['start_time']
        
        try:
            # Phase 1: Preparation
            handover_state['phase'] = 'preparation'
            yield self.env.timeout(self.preparation_time)
            
            # Phase 2: Execution
            handover_state['phase'] = 'execution'
            yield self.env.timeout(self.execution_time)
            
            # Phase 3: Completion
            handover_state['phase'] = 'completion'
            yield self.env.timeout(self.completion_time)
            
            # Handover successful
            total_time = self.env.now - start_time
            self._complete_handover(ue_id, True, total_time)
            
        except Exception as e:
            # Handover failed
            logger.error(f"Handover failed for UE {ue_id}: {e}")
            total_time = self.env.now - start_time
            self._complete_handover(ue_id, False, total_time)

    def _complete_handover(self, ue_id: int, success: bool, duration: float):
        """Complete handover procedure and update statistics"""
        if ue_id not in self.active_handovers:
            return
            
        handover_state = self.active_handovers[ue_id]
        
        # Get signal strengths (simplified)
        signal_before = -100.0  # Placeholder
        signal_after = -95.0 if success else -105.0  # Placeholder
        
        # Create handover event record
        event = HandoverEvent(
            timestamp=self.env.now,
            ue_id=ue_id,
            source_gnb_id=handover_state['source_gnb'],
            target_gnb_id=handover_state['target_gnb'],
            handover_type=HandoverType.INTRA_FREQUENCY,  # Simplified
            cause=handover_state['cause'],
            duration=duration,
            success=success,
            signal_strength_before=signal_before,
            signal_strength_after=signal_after,
            position=(0, 0)  # Placeholder - would get from UE
        )
        
        self.handover_history.append(event)
        
        # Update statistics
        self.stats['total_handovers'] += 1
        if success:
            self.stats['successful_handovers'] += 1
        else:
            self.stats['failed_handovers'] += 1
            
        # Update average handover time
        total_time = self.stats['average_handover_time'] * (self.stats['total_handovers'] - 1)
        self.stats['average_handover_time'] = (total_time + duration) / self.stats['total_handovers']
        
        # Check for ping-pong handover
        if self._is_ping_pong_handover(ue_id, handover_state['target_gnb'], 
                                     handover_state['source_gnb']):
            self.stats['ping_pong_handovers'] += 1
            
        logger.info(f"Handover {'completed' if success else 'failed'} for UE {ue_id} "
                   f"in {duration*1000:.1f}ms")
        
        # Clean up
        del self.active_handovers[ue_id]

    def _is_ping_pong_handover(self, ue_id: int, current_target: int, 
                              current_source: Optional[int]) -> bool:
        """Check if this is a ping-pong handover"""
        if current_source is None:
            return False
            
        # Look for recent handover in opposite direction
        cutoff_time = self.env.now - 5.0  # 5 second window
        
        for event in reversed(self.handover_history):
            if event.timestamp < cutoff_time:
                break
                
            if (event.ue_id == ue_id and 
                event.source_gnb_id == current_target and 
                event.target_gnb_id == current_source and
                event.success):
                return True
                
        return False

    def force_handover(self, ue_id: int, target_gnb_id: int, 
                      cause: HandoverCause = HandoverCause.USER_PREFERENCE):
        """Force handover for testing or special scenarios"""
        current_source = None  # Would get from UE connection state
        self._initiate_handover(ue_id, current_source, target_gnb_id, cause)

    def set_handover_parameters(self, hysteresis: float = None, 
                               time_to_trigger: float = None,
                               signal_threshold: float = None):
        """Update handover parameters"""
        if hysteresis is not None:
            self.hysteresis = hysteresis
        if time_to_trigger is not None:
            self.time_to_trigger = time_to_trigger
        if signal_threshold is not None:
            self.signal_threshold = signal_threshold
            
        logger.info(f"Updated handover parameters: hysteresis={self.hysteresis}dB, "
                   f"TTT={self.time_to_trigger*1000}ms, threshold={self.signal_threshold}dBm")

    def get_handover_statistics(self) -> Dict[str, Any]:
        """Get handover performance statistics"""
        stats = self.stats.copy()
        
        # Calculate success rate
        if stats['total_handovers'] > 0:
            stats['success_rate'] = stats['successful_handovers'] / stats['total_handovers']
            stats['failure_rate'] = stats['failed_handovers'] / stats['total_handovers']
            stats['ping_pong_rate'] = stats['ping_pong_handovers'] / stats['total_handovers']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['ping_pong_rate'] = 0.0
            
        # Add parameter information
        stats['parameters'] = {
            'hysteresis_db': self.hysteresis,
            'time_to_trigger_ms': self.time_to_trigger * 1000,
            'signal_threshold_dbm': self.signal_threshold,
            'handover_margin_db': self.handover_margin
        }
        
        return stats

    def get_handover_events(self, ue_id: Optional[int] = None) -> List[HandoverEvent]:
        """Get handover event history"""
        if ue_id is None:
            return self.handover_history.copy()
        else:
            return [event for event in self.handover_history if event.ue_id == ue_id]

    def get_active_handovers(self) -> Dict[int, Dict]:
        """Get currently active handovers"""
        return self.active_handovers.copy()

    def clear_history(self):
        """Clear handover history (for testing)"""
        self.handover_history.clear()
        self.measurement_reports.clear()
        self.handover_triggers.clear()
        self.active_handovers.clear()
        
        # Reset statistics
        self.stats = {
            'total_handovers': 0,
            'successful_handovers': 0,
            'failed_handovers': 0,
            'ping_pong_handovers': 0,
            'average_handover_time': 0.0
        }
        
        logger.info("Handover history cleared")