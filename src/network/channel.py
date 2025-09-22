"""
Channel models for 5G NR simulations.

This module implements various propagation models and channel characteristics
for realistic 5G NR performance evaluation.
"""

import numpy as np
import math
from typing import Dict, Tuple, Optional
from enum import Enum
from ..mobility.user_equipment import Position


class PropagationModel(Enum):
    """Available propagation models."""
    FREE_SPACE = "free_space"
    URBAN_MACRO = "urban_macro"
    URBAN_MICRO = "urban_micro"
    INDOOR = "indoor"
    RURAL_MACRO = "rural_macro"


class ChannelCondition(Enum):
    """Channel conditions for modeling."""
    LOS = "line_of_sight"
    NLOS = "non_line_of_sight"


class ChannelModel:
    """Channel model for 5G NR simulations."""
    
    def __init__(self, propagation_model: PropagationModel = PropagationModel.URBAN_MACRO,
                 frequency: float = 3500.0, temperature: float = 290.0):
        self.propagation_model = propagation_model
        self.frequency = frequency  # MHz
        self.temperature = temperature  # Kelvin
        self.speed_of_light = 3e8  # m/s
        
        # Noise figure and thermal noise
        self.noise_figure = 7.0  # dB
        self.thermal_noise_density = -174.0  # dBm/Hz at 290K
    
    def calculate_path_loss(self, distance: float, tx_height: float = 35.0, 
                          rx_height: float = 1.5, condition: ChannelCondition = None) -> float:
        """
        Calculate path loss based on the propagation model.
        
        Args:
            distance: Distance in meters
            tx_height: Transmitter height in meters
            rx_height: Receiver height in meters
            condition: Channel condition (LOS/NLOS)
            
        Returns:
            Path loss in dB
        """
        if distance < 1.0:
            distance = 1.0  # Avoid division by zero
        
        if self.propagation_model == PropagationModel.FREE_SPACE:
            return self._free_space_path_loss(distance)
        
        elif self.propagation_model == PropagationModel.URBAN_MACRO:
            return self._urban_macro_path_loss(distance, tx_height, rx_height, condition)
        
        elif self.propagation_model == PropagationModel.URBAN_MICRO:
            return self._urban_micro_path_loss(distance, tx_height, rx_height, condition)
        
        elif self.propagation_model == PropagationModel.INDOOR:
            return self._indoor_path_loss(distance)
        
        elif self.propagation_model == PropagationModel.RURAL_MACRO:
            return self._rural_macro_path_loss(distance, tx_height, rx_height)
        
        else:
            return self._free_space_path_loss(distance)
    
    def _free_space_path_loss(self, distance: float) -> float:
        """Free space path loss model."""
        frequency_hz = self.frequency * 1e6
        return 20 * math.log10(4 * math.pi * distance * frequency_hz / self.speed_of_light)
    
    def _urban_macro_path_loss(self, distance: float, tx_height: float, 
                              rx_height: float, condition: ChannelCondition) -> float:
        """3GPP Urban Macro path loss model (38.901)."""
        distance_2d = distance  # Simplified to 2D
        distance_3d = math.sqrt(distance_2d**2 + (tx_height - rx_height)**2)
        
        # Determine if LOS or NLOS
        if condition is None:
            condition = self._determine_channel_condition(distance_2d, "urban_macro")
        
        frequency_ghz = self.frequency / 1000.0
        
        if condition == ChannelCondition.LOS:
            # LOS path loss
            pl1 = 28.0 + 22 * math.log10(distance_3d) + 20 * math.log10(frequency_ghz)
            pl2 = (28.0 + 40 * math.log10(distance_3d) + 20 * math.log10(frequency_ghz) 
                   - 9 * math.log10((tx_height - 1.5)**2 + (rx_height - 1.5)**2))
            
            breakpoint = 4 * tx_height * rx_height * frequency_ghz * 1e9 / self.speed_of_light
            
            if distance_3d < breakpoint:
                return pl1
            else:
                return pl2
        else:
            # NLOS path loss
            return (13.54 + 39.08 * math.log10(distance_3d) + 20 * math.log10(frequency_ghz) 
                    - 0.6 * (rx_height - 1.5))
    
    def _urban_micro_path_loss(self, distance: float, tx_height: float, 
                              rx_height: float, condition: ChannelCondition) -> float:
        """3GPP Urban Micro path loss model (38.901)."""
        distance_2d = distance
        distance_3d = math.sqrt(distance_2d**2 + (tx_height - rx_height)**2)
        
        if condition is None:
            condition = self._determine_channel_condition(distance_2d, "urban_micro")
        
        frequency_ghz = self.frequency / 1000.0
        
        if condition == ChannelCondition.LOS:
            pl1 = 32.4 + 21 * math.log10(distance_3d) + 20 * math.log10(frequency_ghz)
            pl2 = (32.4 + 40 * math.log10(distance_3d) + 20 * math.log10(frequency_ghz) 
                   - 9.5 * math.log10((tx_height - 1.5)**2 + (rx_height - 1.5)**2))
            
            breakpoint = 4 * tx_height * rx_height * frequency_ghz * 1e9 / self.speed_of_light
            
            if distance_3d < breakpoint:
                return pl1
            else:
                return pl2
        else:
            return (35.3 * math.log10(distance_3d) + 22.4 + 21.3 * math.log10(frequency_ghz) 
                    - 0.3 * (rx_height - 1.5))
    
    def _indoor_path_loss(self, distance: float) -> float:
        """Indoor path loss model."""
        frequency_ghz = self.frequency / 1000.0
        return 32.4 + 17.3 * math.log10(distance) + 20 * math.log10(frequency_ghz)
    
    def _rural_macro_path_loss(self, distance: float, tx_height: float, rx_height: float) -> float:
        """Rural Macro path loss model."""
        distance_3d = math.sqrt(distance**2 + (tx_height - rx_height)**2)
        frequency_ghz = self.frequency / 1000.0
        
        pl1 = 20 * math.log10(40 * math.pi * distance_3d * frequency_ghz / 3)
        pl2 = (20 * math.log10(40 * math.pi * distance_3d * frequency_ghz / 3) 
               + min(0.03 * 1.72**1.8, 10) * (math.log10(distance_3d))**1.8
               - min(0.044 * 1.72**1.8, 14.77) + 0.002 * math.log10(1.72) * distance_3d)
        
        breakpoint = 2 * math.pi * tx_height * rx_height * frequency_ghz * 1e9 / self.speed_of_light
        
        if distance_3d < breakpoint:
            return pl1
        else:
            return pl2
    
    def _determine_channel_condition(self, distance: float, scenario: str) -> ChannelCondition:
        """Determine if the channel is LOS or NLOS based on probability."""
        if scenario == "urban_macro":
            if distance <= 18:
                los_prob = 1.0
            else:
                los_prob = (18 / distance + np.exp(-distance / 36) * (1 - 18 / distance))
        elif scenario == "urban_micro":
            los_prob = min(18 / distance, 1.0) * (1 - np.exp(-distance / 36)) + np.exp(-distance / 36)
        else:
            los_prob = 0.5  # Default 50%
        
        return ChannelCondition.LOS if np.random.random() < los_prob else ChannelCondition.NLOS
    
    def add_shadowing(self, path_loss: float, shadow_std: float = 8.0) -> float:
        """
        Add log-normal shadowing to path loss.
        
        Args:
            path_loss: Path loss in dB
            shadow_std: Standard deviation of shadowing in dB
            
        Returns:
            Path loss with shadowing in dB
        """
        shadowing = np.random.normal(0, shadow_std)
        return path_loss + shadowing
    
    def add_fast_fading(self, signal_power: float, fading_model: str = "rayleigh") -> float:
        """
        Add fast fading to signal power.
        
        Args:
            signal_power: Signal power in dBm
            fading_model: Type of fading ("rayleigh", "rician", "nakagami")
            
        Returns:
            Signal power with fading in dBm
        """
        if fading_model == "rayleigh":
            # Rayleigh fading
            fading_linear = np.random.rayleigh(1/math.sqrt(2))
            fading_db = 20 * math.log10(fading_linear)
        elif fading_model == "rician":
            # Rician fading with K-factor = 10 dB
            k_factor_db = 10
            k_factor_linear = 10**(k_factor_db/10)
            
            # Generate Rician fading
            sigma = math.sqrt(1/(2*(k_factor_linear+1)))
            los_component = math.sqrt(k_factor_linear/(k_factor_linear+1))
            
            real_part = np.random.normal(los_component, sigma)
            imag_part = np.random.normal(0, sigma)
            
            fading_linear = math.sqrt(real_part**2 + imag_part**2)
            fading_db = 20 * math.log10(fading_linear)
        else:
            fading_db = 0  # No fading
        
        return signal_power + fading_db
    
    def calculate_thermal_noise_power(self, bandwidth_hz: float) -> float:
        """
        Calculate thermal noise power.
        
        Args:
            bandwidth_hz: Bandwidth in Hz
            
        Returns:
            Noise power in dBm
        """
        return self.thermal_noise_density + 10 * math.log10(bandwidth_hz)
    
    def calculate_sinr(self, signal_power_dbm: float, interference_power_dbm: float,
                      noise_power_dbm: float) -> float:
        """
        Calculate Signal-to-Interference-plus-Noise Ratio (SINR).
        
        Args:
            signal_power_dbm: Desired signal power in dBm
            interference_power_dbm: Interference power in dBm
            noise_power_dbm: Noise power in dBm
            
        Returns:
            SINR in dB
        """
        signal_linear = 10**(signal_power_dbm/10)
        interference_linear = 10**(interference_power_dbm/10)
        noise_linear = 10**(noise_power_dbm/10)
        
        sinr_linear = signal_linear / (interference_linear + noise_linear)
        return 10 * math.log10(sinr_linear)
    
    def calculate_channel_capacity(self, sinr_db: float, bandwidth_hz: float,
                                 mimo_factor: float = 1.0) -> float:
        """
        Calculate channel capacity using Shannon's theorem.
        
        Args:
            sinr_db: SINR in dB
            bandwidth_hz: Bandwidth in Hz
            mimo_factor: MIMO multiplexing factor
            
        Returns:
            Channel capacity in bps
        """
        sinr_linear = 10**(sinr_db/10)
        capacity = bandwidth_hz * math.log2(1 + sinr_linear) * mimo_factor
        return capacity
    
    def estimate_block_error_rate(self, sinr_db: float, modulation: str = "QPSK") -> float:
        """
        Estimate Block Error Rate (BLER) based on SINR.
        
        Args:
            sinr_db: SINR in dB
            modulation: Modulation scheme
            
        Returns:
            BLER (0 to 1)
        """
        # Simplified BLER curves for different modulations
        if modulation == "QPSK":
            # QPSK BLER curve approximation
            if sinr_db < -5:
                return 1.0
            elif sinr_db > 10:
                return 0.001
            else:
                return 0.5 * (1 - math.tanh((sinr_db - 2.5) / 2))
        
        elif modulation == "16QAM":
            if sinr_db < 5:
                return 1.0
            elif sinr_db > 20:
                return 0.001
            else:
                return 0.5 * (1 - math.tanh((sinr_db - 12.5) / 3))
        
        elif modulation == "64QAM":
            if sinr_db < 15:
                return 1.0
            elif sinr_db > 30:
                return 0.001
            else:
                return 0.5 * (1 - math.tanh((sinr_db - 22.5) / 3))
        
        else:
            return 0.1  # Default BLER
    
    def get_channel_characteristics(self, tx_pos: Position, rx_pos: Position,
                                  tx_power_dbm: float, bandwidth_hz: float,
                                  tx_height: float = 35.0, rx_height: float = 1.5) -> Dict:
        """
        Get comprehensive channel characteristics between two points.
        
        Args:
            tx_pos: Transmitter position
            rx_pos: Receiver position
            tx_power_dbm: Transmit power in dBm
            bandwidth_hz: Bandwidth in Hz
            tx_height: Transmitter height in meters
            rx_height: Receiver height in meters
            
        Returns:
            Dictionary with channel characteristics
        """
        distance = tx_pos.distance_to(rx_pos)
        
        # Path loss calculation
        path_loss = self.calculate_path_loss(distance, tx_height, rx_height)
        path_loss_with_shadowing = self.add_shadowing(path_loss)
        
        # Received signal power
        rx_power_dbm = tx_power_dbm - path_loss_with_shadowing
        rx_power_with_fading = self.add_fast_fading(rx_power_dbm)
        
        # Noise power
        noise_power_dbm = self.calculate_thermal_noise_power(bandwidth_hz) + self.noise_figure
        
        # SINR (assuming no interference for simplicity)
        sinr_db = self.calculate_sinr(rx_power_with_fading, -200, noise_power_dbm)  # -200 dBm = no interference
        
        # Channel capacity
        capacity_bps = self.calculate_channel_capacity(sinr_db, bandwidth_hz)
        
        # BLER
        bler = self.estimate_block_error_rate(sinr_db)
        
        return {
            'distance': distance,
            'path_loss': path_loss,
            'path_loss_with_shadowing': path_loss_with_shadowing,
            'rx_power_dbm': rx_power_dbm,
            'rx_power_with_fading': rx_power_with_fading,
            'noise_power_dbm': noise_power_dbm,
            'sinr_db': sinr_db,
            'capacity_bps': capacity_bps,
            'capacity_mbps': capacity_bps / 1e6,
            'bler': bler,
            'propagation_model': self.propagation_model.value
        }