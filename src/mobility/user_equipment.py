"""
User Equipment (UE) mobility models for 5G NR simulations.

This module provides various mobility patterns including stationary,
linear movement, and random walk models.
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum
import math


class MobilityModel(Enum):
    """Available mobility models for UE."""
    STATIONARY = "stationary"
    LINEAR = "linear"
    RANDOM_WALK = "random_walk"
    CIRCULAR = "circular"
    HIGHWAY = "highway"


@dataclass
class Position:
    """2D position with coordinates."""
    x: float
    y: float
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __add__(self, other: 'Position') -> 'Position':
        return Position(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Position') -> 'Position':
        return Position(self.x - other.x, self.y - other.y)


@dataclass
class Velocity:
    """2D velocity vector."""
    vx: float  # m/s
    vy: float  # m/s
    
    @property
    def speed(self) -> float:
        """Get speed magnitude."""
        return math.sqrt(self.vx**2 + self.vy**2)
    
    @property
    def direction(self) -> float:
        """Get direction in radians."""
        return math.atan2(self.vy, self.vx)


class UserEquipment:
    """User Equipment with mobility capabilities."""
    
    def __init__(self, ue_id: int, initial_position: Position, 
                 mobility_model: MobilityModel = MobilityModel.STATIONARY,
                 **mobility_params):
        self.ue_id = ue_id
        self.current_position = initial_position
        self.initial_position = initial_position
        self.mobility_model = mobility_model
        self.velocity = Velocity(0.0, 0.0)
        self.trajectory: List[Position] = [initial_position]
        self.connected_gnb_id: Optional[int] = None
        self.rsrp_measurements: List[Tuple[int, float]] = []  # (gNB_id, RSRP)
        
        # Mobility-specific parameters
        self.mobility_params = mobility_params
        self._initialize_mobility_params()
    
    def _initialize_mobility_params(self):
        """Initialize mobility-specific parameters."""
        if self.mobility_model == MobilityModel.LINEAR:
            self.velocity = Velocity(
                self.mobility_params.get('speed', 10.0) * math.cos(self.mobility_params.get('direction', 0.0)),
                self.mobility_params.get('speed', 10.0) * math.sin(self.mobility_params.get('direction', 0.0))
            )
        elif self.mobility_model == MobilityModel.RANDOM_WALK:
            self.max_speed = self.mobility_params.get('max_speed', 5.0)
            self.direction_change_probability = self.mobility_params.get('direction_change_prob', 0.1)
        elif self.mobility_model == MobilityModel.CIRCULAR:
            self.center = Position(
                self.mobility_params.get('center_x', self.initial_position.x),
                self.mobility_params.get('center_y', self.initial_position.y)
            )
            self.radius = self.mobility_params.get('radius', 100.0)
            self.angular_speed = self.mobility_params.get('angular_speed', 0.1)  # rad/s
            self.current_angle = math.atan2(
                self.initial_position.y - self.center.y,
                self.initial_position.x - self.center.x
            )
        elif self.mobility_model == MobilityModel.HIGHWAY:
            self.lane_width = self.mobility_params.get('lane_width', 3.5)
            self.lane_number = self.mobility_params.get('lane_number', 0)
            self.highway_speed = self.mobility_params.get('highway_speed', 30.0)  # m/s (108 km/h)
            self.velocity = Velocity(self.highway_speed, 0.0)
    
    def update_position(self, time_step: float):
        """Update position based on mobility model."""
        if self.mobility_model == MobilityModel.STATIONARY:
            # No movement
            pass
        
        elif self.mobility_model == MobilityModel.LINEAR:
            # Constant velocity movement
            self.current_position.x += self.velocity.vx * time_step
            self.current_position.y += self.velocity.vy * time_step
        
        elif self.mobility_model == MobilityModel.RANDOM_WALK:
            # Random walk with occasional direction changes
            if np.random.random() < self.direction_change_probability:
                # Change direction and speed
                new_direction = np.random.uniform(0, 2 * math.pi)
                new_speed = np.random.uniform(0, self.max_speed)
                self.velocity = Velocity(
                    new_speed * math.cos(new_direction),
                    new_speed * math.sin(new_direction)
                )
            
            self.current_position.x += self.velocity.vx * time_step
            self.current_position.y += self.velocity.vy * time_step
        
        elif self.mobility_model == MobilityModel.CIRCULAR:
            # Circular movement around a center point
            self.current_angle += self.angular_speed * time_step
            self.current_position.x = self.center.x + self.radius * math.cos(self.current_angle)
            self.current_position.y = self.center.y + self.radius * math.sin(self.current_angle)
            
            # Update velocity for circular motion
            self.velocity = Velocity(
                -self.radius * self.angular_speed * math.sin(self.current_angle),
                self.radius * self.angular_speed * math.cos(self.current_angle)
            )
        
        elif self.mobility_model == MobilityModel.HIGHWAY:
            # Highway movement with lane changes
            self.current_position.x += self.velocity.vx * time_step
            
            # Occasional lane changes
            if np.random.random() < 0.01:  # 1% chance per time step
                lane_change = np.random.choice([-1, 0, 1])
                new_lane = max(0, min(3, self.lane_number + lane_change))  # 4 lanes (0-3)
                if new_lane != self.lane_number:
                    self.lane_number = new_lane
                    target_y = self.initial_position.y + (self.lane_number - 1.5) * self.lane_width
                    self.current_position.y = target_y
        
        # Store position in trajectory
        self.trajectory.append(Position(self.current_position.x, self.current_position.y))
    
    def get_distance_to_gnb(self, gnb_position: Position) -> float:
        """Calculate distance to a gNB."""
        return self.current_position.distance_to(gnb_position)
    
    def calculate_rsrp(self, gnb_position: Position, tx_power: float = 46.0) -> float:
        """
        Calculate Reference Signal Received Power (RSRP) from a gNB.
        
        Args:
            gnb_position: Position of the gNB
            tx_power: Transmit power in dBm
            
        Returns:
            RSRP in dBm
        """
        distance = self.get_distance_to_gnb(gnb_position)
        
        # Simple path loss model (free space + log-normal shadowing)
        # Path loss = 20*log10(4*pi*d*f/c) + shadowing
        frequency = 3.5e9  # 3.5 GHz
        c = 3e8  # Speed of light
        
        if distance < 1.0:
            distance = 1.0  # Avoid division by zero
        
        # Free space path loss
        fspl = 20 * math.log10(4 * math.pi * distance * frequency / c)
        
        # Add log-normal shadowing (0-mean, 8dB std)
        shadowing = np.random.normal(0, 8)
        
        # Calculate RSRP
        rsrp = tx_power - fspl - shadowing
        
        return rsrp
    
    def update_rsrp_measurements(self, gnb_positions: dict, tx_power: float = 46.0):
        """Update RSRP measurements for all gNBs."""
        self.rsrp_measurements.clear()
        for gnb_id, position in gnb_positions.items():
            rsrp = self.calculate_rsrp(position, tx_power)
            self.rsrp_measurements.append((gnb_id, rsrp))
        
        # Sort by RSRP (descending order - best first)
        self.rsrp_measurements.sort(key=lambda x: x[1], reverse=True)
    
    def get_best_serving_gnb(self) -> Optional[int]:
        """Get the gNB with the best RSRP."""
        if not self.rsrp_measurements:
            return None
        return self.rsrp_measurements[0][0]
    
    def get_rsrp_for_gnb(self, gnb_id: int) -> Optional[float]:
        """Get RSRP measurement for a specific gNB."""
        for measured_gnb_id, rsrp in self.rsrp_measurements:
            if measured_gnb_id == gnb_id:
                return rsrp
        return None
    
    def should_trigger_handover(self, hysteresis: float = 3.0, 
                               time_to_trigger: int = 160) -> bool:
        """
        Check if handover should be triggered.
        
        Args:
            hysteresis: Hysteresis margin in dB
            time_to_trigger: Time to trigger in ms
            
        Returns:
            True if handover should be triggered
        """
        if len(self.rsrp_measurements) < 2:
            return False
        
        serving_rsrp = self.rsrp_measurements[0][1]
        best_neighbor_rsrp = self.rsrp_measurements[1][1]
        
        # Simple A3 event: Neighbor becomes offset better than serving
        return best_neighbor_rsrp > serving_rsrp + hysteresis
    
    def get_trajectory(self) -> List[Position]:
        """Get the complete trajectory of the UE."""
        return self.trajectory.copy()
    
    def get_current_speed(self) -> float:
        """Get current speed in m/s."""
        return self.velocity.speed
    
    def get_statistics(self) -> dict:
        """Get UE mobility statistics."""
        total_distance = 0.0
        if len(self.trajectory) > 1:
            for i in range(1, len(self.trajectory)):
                total_distance += self.trajectory[i].distance_to(self.trajectory[i-1])
        
        return {
            'ue_id': self.ue_id,
            'mobility_model': self.mobility_model.value,
            'current_position': (self.current_position.x, self.current_position.y),
            'current_speed': self.get_current_speed(),
            'total_distance_traveled': total_distance,
            'trajectory_length': len(self.trajectory),
            'connected_gnb_id': self.connected_gnb_id,
            'best_rsrp': self.rsrp_measurements[0][1] if self.rsrp_measurements else None
        }