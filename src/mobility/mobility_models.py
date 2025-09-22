"""
Mobility Models for 5G NR Simulation

This module implements various mobility models for User Equipment (UE)
movement simulation in 5G networks.
"""

import simpy
import numpy as np
import logging
from typing import List, Tuple, Dict, Any
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MobilityType(Enum):
    """Types of mobility models"""
    STATIONARY = "stationary"
    RANDOM_WALK = "random_walk"
    RANDOM_WAYPOINT = "random_waypoint"
    LINEAR = "linear"
    CIRCULAR = "circular"
    MANHATTAN = "manhattan"


class MobilityModel(ABC):
    """Abstract base class for mobility models"""
    
    def __init__(self, ue_id: int, initial_position: Tuple[float, float],
                 speed: float, env: simpy.Environment):
        self.ue_id = ue_id
        self.position = initial_position
        self.speed = speed  # m/s
        self.env = env
        self.direction = np.random.uniform(0, 2 * np.pi)
        self.target_position = None
        
    @abstractmethod
    def get_next_position(self, dt: float) -> Tuple[float, float]:
        """Calculate next position after time dt"""
        pass
    
    @abstractmethod
    def update_parameters(self):
        """Update model-specific parameters"""
        pass


class StationaryModel(MobilityModel):
    """Stationary mobility model - UE doesn't move"""
    
    def get_next_position(self, dt: float) -> Tuple[float, float]:
        return self.position
    
    def update_parameters(self):
        pass


class RandomWalkModel(MobilityModel):
    """Random walk mobility model"""
    
    def __init__(self, ue_id: int, initial_position: Tuple[float, float],
                 speed: float, env: simpy.Environment, 
                 direction_change_prob: float = 0.1):
        super().__init__(ue_id, initial_position, speed, env)
        self.direction_change_prob = direction_change_prob
        
    def get_next_position(self, dt: float) -> Tuple[float, float]:
        # Change direction with some probability
        if np.random.random() < self.direction_change_prob:
            self.direction += np.random.normal(0, np.pi/4)  # ±45° variation
            
        # Calculate displacement
        dx = self.speed * dt * np.cos(self.direction)
        dy = self.speed * dt * np.sin(self.direction)
        
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        
        return (new_x, new_y)
    
    def update_parameters(self):
        # Occasionally change direction
        if np.random.random() < 0.05:  # 5% chance
            self.direction = np.random.uniform(0, 2 * np.pi)


class RandomWaypointModel(MobilityModel):
    """Random waypoint mobility model"""
    
    def __init__(self, ue_id: int, initial_position: Tuple[float, float],
                 speed: float, env: simpy.Environment,
                 area_bounds: Tuple[float, float, float, float] = (-1000, 1000, -1000, 1000),
                 pause_time: float = 0.0):
        super().__init__(ue_id, initial_position, speed, env)
        self.area_bounds = area_bounds  # (min_x, max_x, min_y, max_y)
        self.pause_time = pause_time
        self.pause_remaining = 0.0
        self.target_position = self._generate_waypoint()
        
    def _generate_waypoint(self) -> Tuple[float, float]:
        """Generate random waypoint within area bounds"""
        min_x, max_x, min_y, max_y = self.area_bounds
        x = np.random.uniform(min_x, max_x)
        y = np.random.uniform(min_y, max_y)
        return (x, y)
    
    def get_next_position(self, dt: float) -> Tuple[float, float]:
        # Handle pause time
        if self.pause_remaining > 0:
            self.pause_remaining -= dt
            return self.position
            
        # Move towards target waypoint
        if self.target_position is None:
            self.target_position = self._generate_waypoint()
            
        dx = self.target_position[0] - self.position[0]
        dy = self.target_position[1] - self.position[1]
        distance_to_target = np.sqrt(dx**2 + dy**2)
        
        # Check if reached target
        if distance_to_target <= self.speed * dt:
            # Reached waypoint
            new_position = self.target_position
            self.target_position = self._generate_waypoint()
            self.pause_remaining = self.pause_time
        else:
            # Move towards target
            unit_dx = dx / distance_to_target
            unit_dy = dy / distance_to_target
            
            new_x = self.position[0] + self.speed * dt * unit_dx
            new_y = self.position[1] + self.speed * dt * unit_dy
            new_position = (new_x, new_y)
            
        return new_position
    
    def update_parameters(self):
        # Generate new waypoint if reached current one
        if self.target_position is None:
            self.target_position = self._generate_waypoint()


class LinearModel(MobilityModel):
    """Linear mobility model - straight line movement"""
    
    def get_next_position(self, dt: float) -> Tuple[float, float]:
        dx = self.speed * dt * np.cos(self.direction)
        dy = self.speed * dt * np.sin(self.direction)
        
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        
        return (new_x, new_y)
    
    def update_parameters(self):
        pass


class CircularModel(MobilityModel):
    """Circular mobility model"""
    
    def __init__(self, ue_id: int, initial_position: Tuple[float, float],
                 speed: float, env: simpy.Environment,
                 center: Tuple[float, float] = (0, 0), radius: float = 100):
        super().__init__(ue_id, initial_position, speed, env)
        self.center = center
        self.radius = radius
        self.angular_velocity = speed / radius
        
    def get_next_position(self, dt: float) -> Tuple[float, float]:
        # Current angle
        current_angle = np.arctan2(self.position[1] - self.center[1], 
                                 self.position[0] - self.center[0])
        
        # New angle
        new_angle = current_angle + self.angular_velocity * dt
        
        # New position
        new_x = self.center[0] + self.radius * np.cos(new_angle)
        new_y = self.center[1] + self.radius * np.sin(new_angle)
        
        return (new_x, new_y)
    
    def update_parameters(self):
        pass


class ManhattanModel(MobilityModel):
    """Manhattan mobility model - grid-based movement"""
    
    def __init__(self, ue_id: int, initial_position: Tuple[float, float],
                 speed: float, env: simpy.Environment,
                 block_size: float = 100, direction_change_prob: float = 0.1):
        super().__init__(ue_id, initial_position, speed, env)
        self.block_size = block_size
        self.direction_change_prob = direction_change_prob
        self.allowed_directions = [0, np.pi/2, np.pi, 3*np.pi/2]  # N, E, S, W
        self.direction = np.random.choice(self.allowed_directions)
        
    def get_next_position(self, dt: float) -> Tuple[float, float]:
        # Change direction at intersections or randomly
        if (abs(self.position[0] % self.block_size) < 1 and 
            abs(self.position[1] % self.block_size) < 1) or \
           np.random.random() < self.direction_change_prob:
            self.direction = np.random.choice(self.allowed_directions)
            
        dx = self.speed * dt * np.cos(self.direction)
        dy = self.speed * dt * np.sin(self.direction)
        
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        
        return (new_x, new_y)
    
    def update_parameters(self):
        # Change direction occasionally
        if np.random.random() < 0.1:
            self.direction = np.random.choice(self.allowed_directions)


class MobilityManager:
    """
    Mobility Manager for coordinating UE movement in the simulation
    """
    
    def __init__(self, env: simpy.Environment, update_interval: float = 0.1):
        self.env = env
        self.update_interval = update_interval  # seconds
        self.mobility_models: Dict[int, MobilityModel] = {}
        self.ue_list: List['UserEquipment'] = []
        
        logger.info("Mobility Manager initialized")
    
    def add_ue(self, ue: 'UserEquipment'):
        """Add UE to mobility management"""
        mobility_model = self._create_mobility_model(ue)
        self.mobility_models[ue.ue_id] = mobility_model
        self.ue_list.append(ue)
        
        logger.info(f"Added UE {ue.ue_id} with {ue.mobility_model} mobility model")
    
    def _create_mobility_model(self, ue: 'UserEquipment') -> MobilityModel:
        """Create appropriate mobility model for UE"""
        model_type = ue.mobility_model.lower()
        
        if model_type == "stationary":
            return StationaryModel(ue.ue_id, ue.position, ue.speed, self.env)
        elif model_type == "random_walk":
            return RandomWalkModel(ue.ue_id, ue.position, ue.speed, self.env)
        elif model_type == "random_waypoint":
            return RandomWaypointModel(ue.ue_id, ue.position, ue.speed, self.env)
        elif model_type == "linear":
            return LinearModel(ue.ue_id, ue.position, ue.speed, self.env)
        elif model_type == "circular":
            return CircularModel(ue.ue_id, ue.position, ue.speed, self.env)
        elif model_type == "manhattan":
            return ManhattanModel(ue.ue_id, ue.position, ue.speed, self.env)
        else:
            logger.warning(f"Unknown mobility model: {model_type}, using stationary")
            return StationaryModel(ue.ue_id, ue.position, ue.speed, self.env)
    
    def update_positions(self):
        """Update positions of all UEs"""
        for ue in self.ue_list:
            if ue.ue_id in self.mobility_models:
                model = self.mobility_models[ue.ue_id]
                
                # Get new position from mobility model
                new_position = model.get_next_position(self.update_interval)
                
                # Update model's position
                model.position = new_position
                
                # Update UE's position
                ue.update_position(new_position)
                
                # Update model parameters
                model.update_parameters()
    
    def get_ue_positions(self) -> Dict[int, Tuple[float, float]]:
        """Get current positions of all UEs"""
        return {ue.ue_id: ue.position for ue in self.ue_list}
    
    def get_ue_velocities(self) -> Dict[int, Tuple[float, float]]:
        """Get velocities of all UEs"""
        velocities = {}
        for ue in self.ue_list:
            if ue.ue_id in self.mobility_models:
                model = self.mobility_models[ue.ue_id]
                vx = model.speed * np.cos(model.direction)
                vy = model.speed * np.sin(model.direction)
                velocities[ue.ue_id] = (vx, vy)
            else:
                velocities[ue.ue_id] = (0.0, 0.0)
        return velocities
    
    def set_ue_speed(self, ue_id: int, new_speed: float):
        """Set new speed for a UE"""
        if ue_id in self.mobility_models:
            self.mobility_models[ue_id].speed = new_speed
            # Also update UE object
            for ue in self.ue_list:
                if ue.ue_id == ue_id:
                    ue.speed = new_speed
                    break
    
    def set_ue_direction(self, ue_id: int, new_direction: float):
        """Set new direction for a UE (in radians)"""
        if ue_id in self.mobility_models:
            self.mobility_models[ue_id].direction = new_direction
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mobility statistics"""
        total_ues = len(self.ue_list)
        moving_ues = sum(1 for model in self.mobility_models.values() 
                        if not isinstance(model, StationaryModel))
        
        speeds = [model.speed for model in self.mobility_models.values()]
        
        return {
            'total_ues': total_ues,
            'moving_ues': moving_ues,
            'stationary_ues': total_ues - moving_ues,
            'average_speed': np.mean(speeds) if speeds else 0.0,
            'max_speed': np.max(speeds) if speeds else 0.0,
            'min_speed': np.min(speeds) if speeds else 0.0,
            'mobility_models': {type(model).__name__: 1 for model in self.mobility_models.values()}
        }