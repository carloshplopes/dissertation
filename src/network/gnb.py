"""
gNB (5G Base Station) implementation for 5G NR simulations.

This module provides gNB functionality including resource management,
scheduling, and UE connections.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import numpy as np
from ..mobility.user_equipment import Position
from ..qos.qos_manager import QoSManager, QoSFlow


@dataclass
class ResourceBlock:
    """Physical Resource Block (PRB) in 5G NR."""
    rb_id: int
    frequency: float  # MHz
    allocated: bool = False
    ue_id: Optional[int] = None
    qos_flow_id: Optional[int] = None


@dataclass
class BeamConfiguration:
    """Beam configuration for gNB."""
    beam_id: int
    azimuth: float  # degrees
    elevation: float  # degrees
    gain: float  # dBi
    beamwidth_h: float  # horizontal beamwidth in degrees
    beamwidth_v: float  # vertical beamwidth in degrees


class GNodeB:
    """5G New Radio Base Station (gNB)."""
    
    def __init__(self, gnb_id: int, position: Position, 
                 tx_power: float = 46.0, frequency: float = 3500.0,
                 bandwidth: float = 100.0, num_antennas: int = 64):
        self.gnb_id = gnb_id
        self.position = position
        self.tx_power = tx_power  # dBm
        self.frequency = frequency  # MHz
        self.bandwidth = bandwidth  # MHz
        self.num_antennas = num_antennas
        
        # Resource management
        self.num_prbs = int(bandwidth * 5)  # Approximately 5 PRBs per MHz for 5G NR
        self.resource_blocks = [
            ResourceBlock(rb_id=i, frequency=frequency + i * 0.18)  # 180 kHz per PRB
            for i in range(self.num_prbs)
        ]
        
        # Connected UEs
        self.connected_ues: Set[int] = set()
        self.ue_contexts: Dict[int, dict] = {}
        
        # QoS Management
        self.qos_manager = QoSManager()
        
        # Beamforming configuration
        self.beams = self._initialize_beams()
        self.ue_beam_mapping: Dict[int, int] = {}  # ue_id -> beam_id
        
        # Statistics
        self.statistics = {
            'total_ues_served': 0,
            'active_connections': 0,
            'total_data_transmitted': 0,  # bytes
            'total_data_received': 0,     # bytes
            'resource_utilization': 0.0,
            'handovers_in': 0,
            'handovers_out': 0
        }
    
    def _initialize_beams(self) -> List[BeamConfiguration]:
        """Initialize beam configurations for beamforming."""
        beams = []
        num_beams = min(16, self.num_antennas // 4)  # Up to 16 beams
        
        for i in range(num_beams):
            azimuth = (360.0 / num_beams) * i
            beam = BeamConfiguration(
                beam_id=i,
                azimuth=azimuth,
                elevation=0.0,  # Horizontal beamforming
                gain=10 * np.log10(self.num_antennas),  # Array gain
                beamwidth_h=360.0 / num_beams,
                beamwidth_v=60.0
            )
            beams.append(beam)
        
        return beams
    
    def add_ue(self, ue_id: int, initial_qci: int = 9) -> bool:
        """
        Add a UE to this gNB.
        
        Args:
            ue_id: User Equipment ID
            initial_qci: Initial 5QI for default bearer
            
        Returns:
            True if UE was successfully added
        """
        if ue_id in self.connected_ues:
            return False
        
        # Check capacity
        if len(self.connected_ues) >= 100:  # Maximum 100 UEs per gNB
            return False
        
        self.connected_ues.add(ue_id)
        self.ue_contexts[ue_id] = {
            'connection_time': 0.0,
            'total_data_ul': 0,
            'total_data_dl': 0,
            'qos_flows': []
        }
        
        # Create default QoS flow
        default_flow = self.qos_manager.create_flow(initial_qci, ue_id)
        self.ue_contexts[ue_id]['qos_flows'].append(default_flow.flow_id)
        
        # Assign beam
        self._assign_beam_to_ue(ue_id)
        
        self.statistics['total_ues_served'] += 1
        self.statistics['active_connections'] = len(self.connected_ues)
        
        return True
    
    def remove_ue(self, ue_id: int) -> bool:
        """
        Remove a UE from this gNB.
        
        Args:
            ue_id: User Equipment ID
            
        Returns:
            True if UE was successfully removed
        """
        if ue_id not in self.connected_ues:
            return False
        
        # Remove QoS flows for this UE
        flows = self.qos_manager.get_flows_by_ue(ue_id)
        for flow in flows:
            self.qos_manager.remove_flow(flow.flow_id)
        
        # Clean up contexts
        self.connected_ues.remove(ue_id)
        del self.ue_contexts[ue_id]
        
        if ue_id in self.ue_beam_mapping:
            del self.ue_beam_mapping[ue_id]
        
        self.statistics['active_connections'] = len(self.connected_ues)
        
        return True
    
    def _assign_beam_to_ue(self, ue_id: int):
        """Assign the best beam to a UE based on current load."""
        # Simple round-robin beam assignment
        beam_loads = {}
        for beam in self.beams:
            beam_loads[beam.beam_id] = sum(1 for mapped_beam_id in self.ue_beam_mapping.values() 
                                         if mapped_beam_id == beam.beam_id)
        
        # Find beam with minimum load
        best_beam_id = min(beam_loads.keys(), key=lambda x: beam_loads[x])
        self.ue_beam_mapping[ue_id] = best_beam_id
    
    def create_qos_flow(self, ue_id: int, qci: int, **flow_params) -> Optional[int]:
        """
        Create a new QoS flow for a UE.
        
        Args:
            ue_id: User Equipment ID
            qci: 5G QoS Class Identifier
            **flow_params: Additional flow parameters
            
        Returns:
            Flow ID if successful, None otherwise
        """
        if ue_id not in self.connected_ues:
            return None
        
        flow = self.qos_manager.create_flow(qci, ue_id, **flow_params)
        self.ue_contexts[ue_id]['qos_flows'].append(flow.flow_id)
        
        return flow.flow_id
    
    def allocate_resources(self) -> Dict[int, List[int]]:
        """
        Allocate physical resource blocks to UEs based on QoS requirements.
        
        Returns:
            Dictionary mapping UE ID to list of allocated PRB IDs
        """
        allocations = {}
        
        # Get QoS-based resource allocations
        qos_allocations = self.qos_manager.allocate_resources()
        
        # Reset PRB allocations
        for rb in self.resource_blocks:
            rb.allocated = False
            rb.ue_id = None
            rb.qos_flow_id = None
        
        available_prbs = list(range(self.num_prbs))
        
        # Allocate PRBs based on QoS requirements
        for flow_id, (ul_bitrate, dl_bitrate) in qos_allocations.items():
            flow = self.qos_manager.get_flow(flow_id)
            if not flow:
                continue
            
            ue_id = flow.ue_id
            
            # Calculate required PRBs (simplified)
            # Assume 1 Mbps per PRB (this is a simplification)
            required_prbs = max(1, int(dl_bitrate / 1000))  # Convert kbps to Mbps
            required_prbs = min(required_prbs, len(available_prbs))
            
            if ue_id not in allocations:
                allocations[ue_id] = []
            
            # Allocate PRBs
            allocated_prbs = available_prbs[:required_prbs]
            available_prbs = available_prbs[required_prbs:]
            
            for prb_id in allocated_prbs:
                self.resource_blocks[prb_id].allocated = True
                self.resource_blocks[prb_id].ue_id = ue_id
                self.resource_blocks[prb_id].qos_flow_id = flow_id
                allocations[ue_id].append(prb_id)
        
        # Calculate resource utilization
        allocated_prbs = sum(1 for rb in self.resource_blocks if rb.allocated)
        self.statistics['resource_utilization'] = allocated_prbs / self.num_prbs
        
        return allocations
    
    def calculate_throughput(self, ue_id: int, ue_position: Position) -> Tuple[float, float]:
        """
        Calculate achievable throughput for a UE.
        
        Args:
            ue_id: User Equipment ID
            ue_position: UE position
            
        Returns:
            Tuple of (uplink_throughput_mbps, downlink_throughput_mbps)
        """
        if ue_id not in self.connected_ues:
            return 0.0, 0.0
        
        # Calculate distance and path loss
        distance = self.position.distance_to(ue_position)
        
        # Simplified Shannon capacity calculation
        # C = B * log2(1 + SNR)
        
        # Path loss calculation (simplified)
        if distance < 1.0:
            distance = 1.0
        
        path_loss_db = 32.4 + 20 * np.log10(self.frequency) + 20 * np.log10(distance / 1000)
        
        # Add beamforming gain
        beam_id = self.ue_beam_mapping.get(ue_id, 0)
        beam_gain = self.beams[beam_id].gain if beam_id < len(self.beams) else 0
        
        # Calculate received power
        rx_power_dbm = self.tx_power - path_loss_db + beam_gain
        
        # Calculate SNR (assuming noise floor of -174 dBm/Hz)
        noise_power_dbm = -174 + 10 * np.log10(self.bandwidth * 1e6)  # Convert MHz to Hz
        snr_db = rx_power_dbm - noise_power_dbm
        snr_linear = 10 ** (snr_db / 10)
        
        # Shannon capacity
        bandwidth_hz = self.bandwidth * 1e6
        capacity_bps = bandwidth_hz * np.log2(1 + snr_linear)
        capacity_mbps = capacity_bps / 1e6
        
        # Account for resource allocation
        allocated_prbs = len([rb for rb in self.resource_blocks 
                            if rb.allocated and rb.ue_id == ue_id])
        prb_fraction = allocated_prbs / self.num_prbs if self.num_prbs > 0 else 0
        
        achievable_capacity = capacity_mbps * prb_fraction
        
        # Assume symmetric for simplicity (in reality UL/DL would be different)
        return achievable_capacity * 0.7, achievable_capacity  # UL typically lower
    
    def update_statistics(self, time_step: float):
        """Update gNB statistics."""
        # Update connection times
        for ue_id in self.connected_ues:
            self.ue_contexts[ue_id]['connection_time'] += time_step
        
        # Update QoS flow statistics would be done here
        # (simplified for this implementation)
    
    def handover_preparation(self, ue_id: int, target_gnb_id: int) -> bool:
        """
        Prepare for handover of a UE to another gNB.
        
        Args:
            ue_id: User Equipment ID
            target_gnb_id: Target gNB ID
            
        Returns:
            True if preparation successful
        """
        if ue_id not in self.connected_ues:
            return False
        
        # In a real implementation, this would involve:
        # 1. Resource reservation at target
        # 2. Context transfer
        # 3. Path switch preparation
        
        self.statistics['handovers_out'] += 1
        return True
    
    def handover_reception(self, ue_id: int, source_gnb_id: int, context: dict) -> bool:
        """
        Receive a UE from handover.
        
        Args:
            ue_id: User Equipment ID
            source_gnb_id: Source gNB ID
            context: UE context from source gNB
            
        Returns:
            True if reception successful
        """
        success = self.add_ue(ue_id, context.get('initial_qci', 9))
        if success:
            self.statistics['handovers_in'] += 1
            # Restore context
            if ue_id in self.ue_contexts:
                self.ue_contexts[ue_id].update(context)
        
        return success
    
    def get_load(self) -> float:
        """Get current load as fraction of maximum capacity."""
        return len(self.connected_ues) / 100.0  # Assuming max 100 UEs
    
    def get_statistics(self) -> dict:
        """Get comprehensive gNB statistics."""
        qos_stats = self.qos_manager.get_system_metrics()
        
        return {
            'gnb_id': self.gnb_id,
            'position': (self.position.x, self.position.y),
            'connected_ues': len(self.connected_ues),
            'resource_utilization': self.statistics['resource_utilization'],
            'load': self.get_load(),
            'qos_metrics': qos_stats,
            'handovers_in': self.statistics['handovers_in'],
            'handovers_out': self.statistics['handovers_out'],
            'total_ues_served': self.statistics['total_ues_served'],
            'num_beams': len(self.beams),
            'bandwidth': self.bandwidth,
            'frequency': self.frequency
        }