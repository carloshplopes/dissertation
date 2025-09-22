"""
User Equipment (UE) Implementation for 5G NR Simulation

This module implements the UE with mobility support, QoS flow management,
and connection handling.
"""

import simpy
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class UserEquipment:
    """
    5G User Equipment (UE) Implementation
    
    Features:
    - Position tracking and mobility
    - Connection management with gNBs
    - QoS flow handling
    - Packet transmission simulation
    """
    
    def __init__(self, ue_id: int, initial_position: Tuple[float, float],
                 mobility_model: str, speed: float, env: simpy.Environment,
                 qos_manager):
        self.ue_id = ue_id
        self.position = initial_position
        self.mobility_model = mobility_model
        self.speed = speed  # m/s
        self.env = env
        self.qos_manager = qos_manager
        
        # Connection state
        self.connected_gnb: Optional['gNB'] = None
        self.connection_quality = 0.0  # Signal strength
        
        # Mobility parameters
        self.direction = np.random.uniform(0, 2 * np.pi)  # Random initial direction
        self.mobility_update_interval = 0.1  # 100ms
        
        # Traffic and QoS
        self.active_flows: Dict[int, Dict] = {}
        self.packet_buffer = simpy.Store(env)
        
        # Statistics
        self.stats = {
            'packets_sent': 0,
            'packets_delivered': 0,
            'total_delay': 0.0,
            'handovers': 0,
            'connection_time': 0.0,
            'disconnection_events': 0
        }
        
        # Movement history for analysis
        self.position_history = [(0.0, initial_position)]
        
        logger.info(f"UE {ue_id} initialized at position {initial_position}")

    def connect_to_gnb(self, gnb: 'gNB') -> bool:
        """
        Connect to a gNB
        
        Args:
            gnb: Target gNB to connect to
            
        Returns:
            True if connection successful
        """
        # Disconnect from current gNB if any
        if self.connected_gnb:
            self.connected_gnb.disconnect_ue(self.ue_id)
            self.stats['handovers'] += 1
            
        # Check if UE is in coverage
        distance = self.calculate_distance_to(gnb.position)
        if distance > gnb.coverage_radius:
            logger.warning(f"UE {self.ue_id} cannot connect to gNB {gnb.gnb_id} - out of coverage")
            return False
            
        # Establish connection
        if gnb.connect_ue(self):
            self.connected_gnb = gnb
            self.connection_quality = gnb.calculate_signal_strength(distance)
            logger.info(f"UE {self.ue_id} connected to gNB {gnb.gnb_id} with signal {self.connection_quality:.1f} dBm")
            return True
            
        return False

    def disconnect_from_gnb(self):
        """Disconnect from current gNB"""
        if self.connected_gnb:
            self.connected_gnb.disconnect_ue(self.ue_id)
            logger.info(f"UE {self.ue_id} disconnected from gNB {self.connected_gnb.gnb_id}")
            self.connected_gnb = None
            self.connection_quality = 0.0
            self.stats['disconnection_events'] += 1

    def calculate_distance_to(self, target_position: Tuple[float, float]) -> float:
        """Calculate Euclidean distance to target position"""
        return np.sqrt((self.position[0] - target_position[0])**2 + 
                      (self.position[1] - target_position[1])**2)

    def update_position(self, new_position: Tuple[float, float]):
        """Update UE position and record in history"""
        self.position = new_position
        self.position_history.append((self.env.now, new_position))
        
        # Update connection quality if connected
        if self.connected_gnb:
            distance = self.calculate_distance_to(self.connected_gnb.position)
            self.connection_quality = self.connected_gnb.calculate_signal_strength(distance)

    def move_random_walk(self) -> Tuple[float, float]:
        """
        Random walk mobility model
        
        Returns:
            New position after movement
        """
        # Change direction occasionally
        if np.random.random() < 0.1:  # 10% chance to change direction
            self.direction += np.random.normal(0, np.pi/4)  # ±45° variation
            
        # Calculate displacement
        dt = self.mobility_update_interval
        dx = self.speed * dt * np.cos(self.direction)
        dy = self.speed * dt * np.sin(self.direction)
        
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        
        return (new_x, new_y)

    def move_linear(self) -> Tuple[float, float]:
        """
        Linear mobility model (straight line movement)
        
        Returns:
            New position after movement
        """
        dt = self.mobility_update_interval
        dx = self.speed * dt * np.cos(self.direction)
        dy = self.speed * dt * np.sin(self.direction)
        
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        
        return (new_x, new_y)

    def move_circular(self) -> Tuple[float, float]:
        """
        Circular mobility model
        
        Returns:
            New position after movement
        """
        # Circular movement around initial position
        center = (0, 0)  # Assume circular movement around origin
        radius = 100  # 100m radius
        
        # Angular velocity based on speed
        angular_velocity = self.speed / radius
        
        # Update angle
        current_angle = np.arctan2(self.position[1] - center[1], 
                                 self.position[0] - center[0])
        new_angle = current_angle + angular_velocity * self.mobility_update_interval
        
        new_x = center[0] + radius * np.cos(new_angle)
        new_y = center[1] + radius * np.sin(new_angle)
        
        return (new_x, new_y)

    def get_next_position(self) -> Tuple[float, float]:
        """Get next position based on mobility model"""
        if self.mobility_model == "random_walk":
            return self.move_random_walk()
        elif self.mobility_model == "linear":
            return self.move_linear()
        elif self.mobility_model == "circular":
            return self.move_circular()
        elif self.mobility_model == "stationary":
            return self.position
        else:
            logger.warning(f"Unknown mobility model: {self.mobility_model}, using stationary")
            return self.position

    def send_packet(self, packet: Dict[str, Any]) -> simpy.Event:
        """Send packet through connected gNB"""
        return self.env.process(self._send_packet_internal(packet))

    def _send_packet_internal(self, packet: Dict[str, Any]):
        """Internal packet sending process"""
        if not self.connected_gnb:
            logger.warning(f"UE {self.ue_id} cannot send packet - not connected")
            return
            
        # Add UE-specific information to packet
        packet['transmission_time'] = self.env.now
        packet['ue_position'] = self.position
        packet['signal_strength'] = self.connection_quality
        
        # Calculate transmission delay based on packet size and connection quality
        transmission_delay = self._calculate_transmission_delay(packet)
        
        # Wait for transmission delay
        yield self.env.timeout(transmission_delay)
        
        # Send to gNB for processing
        yield from self.connected_gnb.process_packet(packet)
        
        # Update statistics
        self.stats['packets_sent'] += 1
        
        # Check if packet was successfully delivered (simplified)
        if np.random.random() < self._calculate_success_probability():
            self.stats['packets_delivered'] += 1
            if 'total_delay' in packet:
                self.stats['total_delay'] += packet['total_delay']

    def _calculate_transmission_delay(self, packet: Dict[str, Any]) -> float:
        """Calculate transmission delay based on connection quality and packet size"""
        if not self.connected_gnb:
            return float('inf')
            
        # Calculate distance and path loss
        distance = self.calculate_distance_to(self.connected_gnb.position)
        
        # Get achievable throughput
        throughput = self.connected_gnb.calculate_throughput(self.ue_id, self.connection_quality)
        
        if throughput <= 0:
            return 0.1  # 100ms default delay for poor connection
            
        # Calculate transmission time
        packet_size_bits = packet['size'] * 8
        transmission_time = packet_size_bits / throughput
        
        # Add propagation delay (speed of light)
        propagation_delay = distance / 3e8  # seconds
        
        total_delay = transmission_time + propagation_delay
        
        return max(total_delay, 0.001)  # Minimum 1ms delay

    def _calculate_success_probability(self) -> float:
        """Calculate packet success probability based on connection quality"""
        if not self.connected_gnb:
            return 0.0
            
        # Simple model: better signal = higher success rate
        if self.connection_quality > -80:  # dBm
            return 0.99  # 99% success rate
        elif self.connection_quality > -100:
            return 0.95  # 95% success rate
        elif self.connection_quality > -120:
            return 0.85  # 85% success rate
        else:
            return 0.5   # 50% success rate for very poor signal

    def create_qos_flow(self, flow_id: int, qi_value: int) -> bool:
        """Create a QoS flow for this UE"""
        if self.qos_manager.create_flow(flow_id, qi_value):
            self.active_flows[flow_id] = {
                'qi_value': qi_value,
                'creation_time': self.env.now,
                'packets_sent': 0
            }
            logger.info(f"UE {self.ue_id} created QoS flow {flow_id} with 5QI {qi_value}")
            return True
        return False

    def remove_qos_flow(self, flow_id: int) -> bool:
        """Remove a QoS flow"""
        if flow_id in self.active_flows:
            del self.active_flows[flow_id]
            return self.qos_manager.remove_flow(flow_id)
        return False

    def get_signal_quality_category(self) -> str:
        """Get signal quality category"""
        if self.connection_quality > -80:
            return "Excellent"
        elif self.connection_quality > -90:
            return "Good"
        elif self.connection_quality > -100:
            return "Fair"
        elif self.connection_quality > -110:
            return "Poor"
        else:
            return "Very Poor"

    def get_statistics(self) -> Dict[str, Any]:
        """Get UE performance statistics"""
        stats = self.stats.copy()
        stats.update({
            'ue_id': self.ue_id,
            'position': self.position,
            'connected_gnb': self.connected_gnb.gnb_id if self.connected_gnb else None,
            'signal_strength': self.connection_quality,
            'signal_quality': self.get_signal_quality_category(),
            'active_flows': len(self.active_flows),
            'mobility_model': self.mobility_model,
            'speed': self.speed
        })
        
        # Calculate delivery ratio
        if stats['packets_sent'] > 0:
            stats['delivery_ratio'] = stats['packets_delivered'] / stats['packets_sent']
        else:
            stats['delivery_ratio'] = 0.0
            
        # Calculate average delay
        if stats['packets_delivered'] > 0:
            stats['average_delay'] = stats['total_delay'] / stats['packets_delivered']
        else:
            stats['average_delay'] = 0.0
            
        return stats

    def get_position_history(self) -> List[Tuple[float, Tuple[float, float]]]:
        """Get position history for visualization"""
        return self.position_history

    def is_connected(self) -> bool:
        """Check if UE is connected to a gNB"""
        return self.connected_gnb is not None

    def get_distance_to_gnb(self) -> Optional[float]:
        """Get distance to connected gNB"""
        if self.connected_gnb:
            return self.calculate_distance_to(self.connected_gnb.position)
        return None