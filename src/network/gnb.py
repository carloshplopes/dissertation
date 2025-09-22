"""
gNodeB (gNB) Implementation for 5G NR Simulation

This module implements the gNB (5G base station) with QoS-aware scheduling
and radio resource management capabilities.
"""

import simpy
import numpy as np
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RadioResource:
    """Radio resource allocation unit"""
    resource_id: int
    frequency_start: float
    frequency_end: float
    bandwidth: float
    allocated_to: Optional[int] = None  # UE ID
    qi_value: Optional[int] = None


class gNB:
    """
    5G gNodeB (Base Station) Implementation
    
    Features:
    - QoS-aware scheduling based on 5QI values
    - Radio resource management
    - Signal strength calculation
    - Packet processing with delay simulation
    """
    
    def __init__(self, gnb_id: int, position: tuple, coverage_radius: float,
                 frequency: float, bandwidth: float, env: simpy.Environment,
                 qos_manager):
        self.gnb_id = gnb_id
        self.position = position  # (x, y) coordinates
        self.coverage_radius = coverage_radius
        self.frequency = frequency  # Carrier frequency in Hz
        self.bandwidth = bandwidth  # Total bandwidth in Hz
        self.env = env
        self.qos_manager = qos_manager
        
        # Radio resources
        self.num_resource_blocks = 100  # Number of resource blocks
        self.resources = self._initialize_resources()
        
        # Connected UEs
        self.connected_ues: Dict[int, 'UserEquipment'] = {}
        
        # Scheduling parameters
        self.scheduling_interval = 0.001  # 1ms TTI (Transmission Time Interval)
        self.max_throughput = 1e9  # 1 Gbps theoretical max
        
        # Processing queue
        self.packet_queue = simpy.Store(env)
        
        # Statistics
        self.stats = {
            'packets_processed': 0,
            'total_delay': 0.0,
            'total_throughput': 0.0,
            'resource_utilization': 0.0
        }
        
        # Start gNB processes
        self.env.process(self._packet_processing())
        self.env.process(self._scheduling_process())
        
        logger.info(f"gNB {gnb_id} initialized at {position} with {coverage_radius}m coverage")

    def _initialize_resources(self) -> List[RadioResource]:
        """Initialize radio resource blocks"""
        resources = []
        rb_bandwidth = self.bandwidth / self.num_resource_blocks
        
        for i in range(self.num_resource_blocks):
            freq_start = self.frequency + i * rb_bandwidth
            freq_end = freq_start + rb_bandwidth
            
            resource = RadioResource(
                resource_id=i,
                frequency_start=freq_start,
                frequency_end=freq_end,
                bandwidth=rb_bandwidth
            )
            resources.append(resource)
            
        return resources

    def connect_ue(self, ue: 'UserEquipment') -> bool:
        """Connect a UE to this gNB"""
        if ue.ue_id not in self.connected_ues:
            self.connected_ues[ue.ue_id] = ue
            logger.info(f"UE {ue.ue_id} connected to gNB {self.gnb_id}")
            return True
        return False

    def disconnect_ue(self, ue_id: int) -> bool:
        """Disconnect a UE from this gNB"""
        if ue_id in self.connected_ues:
            # Release allocated resources
            self._release_ue_resources(ue_id)
            del self.connected_ues[ue_id]
            logger.info(f"UE {ue_id} disconnected from gNB {self.gnb_id}")
            return True
        return False

    def _release_ue_resources(self, ue_id: int):
        """Release radio resources allocated to a UE"""
        for resource in self.resources:
            if resource.allocated_to == ue_id:
                resource.allocated_to = None
                resource.qi_value = None

    def calculate_signal_strength(self, distance: float) -> float:
        """
        Calculate signal strength using simplified path loss model
        
        Args:
            distance: Distance from gNB in meters
            
        Returns:
            Signal strength in dBm
        """
        if distance <= 0:
            return 0.0
            
        # Free space path loss model
        # FSPL(dB) = 20*log10(d) + 20*log10(f) + 20*log10(4π/c)
        frequency_ghz = self.frequency / 1e9
        fspl_db = 20 * np.log10(distance) + 20 * np.log10(frequency_ghz) + 92.45
        
        # Assume transmit power of 46 dBm (40W)
        tx_power_dbm = 46
        signal_strength = tx_power_dbm - fspl_db
        
        return signal_strength

    def calculate_throughput(self, ue_id: int, signal_strength: float) -> float:
        """
        Calculate achievable throughput based on signal strength and QoS
        
        Args:
            ue_id: UE identifier
            signal_strength: Signal strength in dBm
            
        Returns:
            Achievable throughput in bps
        """
        # Convert signal strength to SINR (simplified)
        noise_floor = -174  # dBm/Hz
        sinr_db = signal_strength - noise_floor - 10 * np.log10(self.bandwidth)
        
        # Shannon capacity approximation
        sinr_linear = 10 ** (sinr_db / 10)
        capacity = self.bandwidth * np.log2(1 + sinr_linear)
        
        # Apply efficiency factor
        efficiency = 0.75  # 75% efficiency
        throughput = capacity * efficiency
        
        # Limit by resource allocation
        allocated_resources = sum(1 for r in self.resources if r.allocated_to == ue_id)
        resource_fraction = allocated_resources / self.num_resource_blocks
        throughput *= resource_fraction
        
        return min(throughput, self.max_throughput)

    def allocate_resources(self, ue_id: int, qi_value: int, required_bandwidth: float) -> int:
        """
        Allocate radio resources to UE based on QoS requirements
        
        Args:
            ue_id: UE identifier
            qi_value: 5QI value for QoS requirements
            required_bandwidth: Required bandwidth in Hz
            
        Returns:
            Number of allocated resource blocks
        """
        # Get QoS characteristics
        qos_char = self.qos_manager.get_flow_characteristics(qi_value)
        if not qos_char:
            return 0
            
        # Calculate required resource blocks
        rb_bandwidth = self.bandwidth / self.num_resource_blocks
        required_rbs = max(1, int(np.ceil(required_bandwidth / rb_bandwidth)))
        
        # Find available resources with priority consideration
        available_resources = [r for r in self.resources if r.allocated_to is None]
        
        # Sort by priority if resources are limited
        if len(available_resources) < required_rbs:
            # Try to preempt lower priority flows
            self._preempt_lower_priority(qos_char.priority_level, required_rbs - len(available_resources))
            available_resources = [r for r in self.resources if r.allocated_to is None]
        
        # Allocate resources
        allocated = 0
        for resource in available_resources[:required_rbs]:
            resource.allocated_to = ue_id
            resource.qi_value = qi_value
            allocated += 1
            
        logger.debug(f"Allocated {allocated} RBs to UE {ue_id} for 5QI {qi_value}")
        return allocated

    def _preempt_lower_priority(self, priority_level: int, needed_rbs: int):
        """Preempt lower priority resource allocations"""
        # Find resources allocated to lower priority flows
        preemptable = []
        for resource in self.resources:
            if (resource.allocated_to is not None and 
                resource.qi_value is not None):
                
                other_qos = self.qos_manager.get_flow_characteristics(resource.qi_value)
                if other_qos and other_qos.priority_level > priority_level:
                    preemptable.append(resource)
        
        # Preempt resources (higher priority_level value = lower priority)
        preemptable.sort(key=lambda r: self.qos_manager.get_flow_characteristics(r.qi_value).priority_level, 
                        reverse=True)
        
        preempted = 0
        for resource in preemptable:
            if preempted >= needed_rbs:
                break
            resource.allocated_to = None
            resource.qi_value = None
            preempted += 1

    def process_packet(self, packet: Dict[str, Any]):
        """Process a packet from UE"""
        return self._process_packet_internal(packet)

    def _process_packet_internal(self, packet: Dict[str, Any]):
        """Internal packet processing"""
        arrival_time = self.env.now
        
        # Add packet to processing queue
        yield self.packet_queue.put(packet)
        
        # Update statistics
        self.stats['packets_processed'] += 1

    def _packet_processing(self):
        """Main packet processing loop"""
        while True:
            # Get packet from queue
            packet = yield self.packet_queue.get()
            
            # Calculate processing delay based on QoS
            flow_id = packet.get('flow_id', 0)
            qos_char = self.qos_manager.get_flow_characteristics(flow_id)
            
            if qos_char:
                # Base processing delay
                base_delay = 0.001  # 1ms base processing
                
                # Adjust based on priority (lower priority_level = higher priority)
                priority_factor = qos_char.priority_level / 100
                processing_delay = base_delay * (1 + priority_factor)
                
                # Add some randomness
                processing_delay *= np.random.uniform(0.8, 1.2)
                
            else:
                processing_delay = 0.005  # 5ms for unknown QoS
            
            # Wait for processing
            yield self.env.timeout(processing_delay)
            
            # Record delay
            total_delay = self.env.now - packet['creation_time']
            self.stats['total_delay'] += total_delay
            packet['processing_time'] = self.env.now
            packet['total_delay'] = total_delay

    def _scheduling_process(self):
        """Resource scheduling process"""
        while True:
            # Update resource utilization
            allocated_resources = sum(1 for r in self.resources if r.allocated_to is not None)
            self.stats['resource_utilization'] = allocated_resources / self.num_resource_blocks
            
            # Wait for next scheduling interval
            yield self.env.timeout(self.scheduling_interval)

    def get_statistics(self) -> Dict[str, Any]:
        """Get gNB performance statistics"""
        stats = self.stats.copy()
        stats.update({
            'gnb_id': self.gnb_id,
            'connected_ues': len(self.connected_ues),
            'position': self.position,
            'coverage_radius': self.coverage_radius,
            'resource_blocks': self.num_resource_blocks,
            'allocated_resources': sum(1 for r in self.resources if r.allocated_to is not None)
        })
        
        # Calculate average delay
        if stats['packets_processed'] > 0:
            stats['average_delay'] = stats['total_delay'] / stats['packets_processed']
        else:
            stats['average_delay'] = 0.0
            
        return stats

    def is_in_coverage(self, position: tuple) -> bool:
        """Check if a position is within coverage"""
        distance = np.sqrt((position[0] - self.position[0])**2 + 
                          (position[1] - self.position[1])**2)
        return distance <= self.coverage_radius