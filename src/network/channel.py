"""
Channel Model for 5G NR Simulation

This module implements various channel models for signal propagation
and interference calculation in 5G networks.
"""

import numpy as np
import logging
from typing import Tuple, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """Channel propagation environment types"""
    FREE_SPACE = "free_space"
    URBAN_MACRO = "urban_macro"
    URBAN_MICRO = "urban_micro"
    INDOOR = "indoor"
    RURAL_MACRO = "rural_macro"


class ChannelModel:
    """
    Channel propagation model for 5G NR simulation
    
    Implements various path loss models according to 3GPP TR 38.901
    """
    
    def __init__(self, channel_type: ChannelType = ChannelType.URBAN_MACRO,
                 frequency: float = 3.5e9, temperature: float = 290.0):
        self.channel_type = channel_type
        self.frequency = frequency  # Hz
        self.temperature = temperature  # Kelvin
        
        # Physical constants
        self.light_speed = 3e8  # m/s
        self.boltzmann = 1.38e-23  # J/K
        
        logger.info(f"Channel model initialized: {channel_type.value} at {frequency/1e9:.1f} GHz")

    def calculate_path_loss(self, distance: float, height_tx: float = 25.0,
                          height_rx: float = 1.5, indoor_loss: float = 0.0) -> float:
        """
        Calculate path loss based on channel type and distance
        
        Args:
            distance: Distance between transmitter and receiver (m)
            height_tx: Transmitter height (m)
            height_rx: Receiver height (m)
            indoor_loss: Additional indoor penetration loss (dB)
            
        Returns:
            Path loss in dB
        """
        if distance <= 0:
            return 0.0
            
        if self.channel_type == ChannelType.FREE_SPACE:
            return self._free_space_path_loss(distance)
        elif self.channel_type == ChannelType.URBAN_MACRO:
            return self._urban_macro_path_loss(distance, height_tx, height_rx) + indoor_loss
        elif self.channel_type == ChannelType.URBAN_MICRO:
            return self._urban_micro_path_loss(distance, height_tx, height_rx) + indoor_loss
        elif self.channel_type == ChannelType.INDOOR:
            return self._indoor_path_loss(distance) + indoor_loss
        elif self.channel_type == ChannelType.RURAL_MACRO:
            return self._rural_macro_path_loss(distance, height_tx, height_rx)
        else:
            return self._free_space_path_loss(distance)

    def _free_space_path_loss(self, distance: float) -> float:
        """Free space path loss model"""
        if distance < 1.0:
            distance = 1.0
            
        # FSPL(dB) = 20*log10(d) + 20*log10(f) + 20*log10(4π/c)
        frequency_ghz = self.frequency / 1e9
        fspl = (20 * np.log10(distance) + 
                20 * np.log10(frequency_ghz) + 
                92.45)
        
        return fspl

    def _urban_macro_path_loss(self, distance: float, h_bs: float, h_ut: float) -> float:
        """
        Urban Macro path loss model (3GPP TR 38.901)
        
        Args:
            distance: 3D distance (m)
            h_bs: Base station height (m)
            h_ut: User terminal height (m)
        """
        # Convert to 2D distance for calculation
        distance_2d = distance
        
        # Breakpoint distance
        h_e = 1.0  # Effective environment height
        h_bs_eff = h_bs - h_e
        h_ut_eff = h_ut - h_e
        
        d_bp = 4 * h_bs_eff * h_ut_eff * self.frequency / self.light_speed
        
        frequency_ghz = self.frequency / 1e9
        
        if distance_2d < d_bp:
            # Line of sight probability
            pl = (28.0 + 22 * np.log10(distance) + 
                  20 * np.log10(frequency_ghz))
        else:
            # Beyond breakpoint
            pl = (28.0 + 40 * np.log10(distance) + 
                  20 * np.log10(frequency_ghz) - 
                  9 * np.log10((d_bp**2 + (h_bs - h_ut)**2)))
        
        # Add shadow fading (log-normal)
        shadow_fading = np.random.normal(0, 4.0)  # 4 dB standard deviation
        
        return pl + shadow_fading

    def _urban_micro_path_loss(self, distance: float, h_bs: float, h_ut: float) -> float:
        """Urban Micro path loss model (3GPP TR 38.901)"""
        frequency_ghz = self.frequency / 1e9
        
        # Line of sight condition
        if distance < 18:
            pl = 32.4 + 21 * np.log10(distance) + 20 * np.log10(frequency_ghz)
        else:
            pl = (32.4 + 40 * np.log10(distance) + 
                  20 * np.log10(frequency_ghz) - 
                  9.5 * np.log10((distance**2 + (h_bs - h_ut)**2)))
        
        # Shadow fading
        shadow_fading = np.random.normal(0, 3.0)  # 3 dB standard deviation
        
        return pl + shadow_fading

    def _indoor_path_loss(self, distance: float) -> float:
        """Indoor path loss model"""
        frequency_ghz = self.frequency / 1e9
        
        # Indoor hotspot model
        if distance < 1.2:
            distance = 1.2
            
        pl = 32.4 + 17.3 * np.log10(distance) + 20 * np.log10(frequency_ghz)
        
        # Indoor specific shadow fading
        shadow_fading = np.random.normal(0, 3.0)
        
        return pl + shadow_fading

    def _rural_macro_path_loss(self, distance: float, h_bs: float, h_ut: float) -> float:
        """Rural Macro path loss model"""
        frequency_ghz = self.frequency / 1e9
        
        # Rural macro model
        pl = (20 * np.log10(40 * np.pi * distance * frequency_ghz / 3) + 
              min(0.03 * (1.72**0.8), 10) * (1.72 - 0.75) + 
              min(0.044 * (1.72**0.8), 14.77) - 0.78)
        
        # Shadow fading
        shadow_fading = np.random.normal(0, 6.0)  # 6 dB standard deviation
        
        return pl + shadow_fading

    def calculate_received_power(self, tx_power: float, distance: float,
                               tx_height: float = 25.0, rx_height: float = 1.5,
                               tx_gain: float = 15.0, rx_gain: float = 0.0) -> float:
        """
        Calculate received power
        
        Args:
            tx_power: Transmit power (dBm)
            distance: Distance (m)
            tx_height: Transmitter height (m)
            rx_height: Receiver height (m)
            tx_gain: Transmitter antenna gain (dBi)
            rx_gain: Receiver antenna gain (dBi)
            
        Returns:
            Received power (dBm)
        """
        path_loss = self.calculate_path_loss(distance, tx_height, rx_height)
        rx_power = tx_power + tx_gain + rx_gain - path_loss
        
        return rx_power

    def calculate_thermal_noise(self, bandwidth: float) -> float:
        """
        Calculate thermal noise power
        
        Args:
            bandwidth: Signal bandwidth (Hz)
            
        Returns:
            Thermal noise power (dBm)
        """
        # Thermal noise power = k * T * B (in Watts)
        noise_power_watts = self.boltzmann * self.temperature * bandwidth
        
        # Convert to dBm
        noise_power_dbm = 10 * np.log10(noise_power_watts * 1000)
        
        return noise_power_dbm

    def calculate_sinr(self, signal_power: float, interference_power: float,
                      bandwidth: float) -> float:
        """
        Calculate Signal-to-Interference-plus-Noise Ratio
        
        Args:
            signal_power: Signal power (dBm)
            interference_power: Interference power (dBm)
            bandwidth: Signal bandwidth (Hz)
            
        Returns:
            SINR (dB)
        """
        noise_power = self.calculate_thermal_noise(bandwidth)
        
        # Convert to linear scale for addition
        signal_linear = 10**(signal_power / 10)
        interference_linear = 10**(interference_power / 10)
        noise_linear = 10**(noise_power / 10)
        
        # Calculate SINR
        sinr_linear = signal_linear / (interference_linear + noise_linear)
        sinr_db = 10 * np.log10(sinr_linear)
        
        return sinr_db

    def calculate_capacity(self, sinr_db: float, bandwidth: float) -> float:
        """
        Calculate channel capacity using Shannon's theorem
        
        Args:
            sinr_db: SINR in dB
            bandwidth: Channel bandwidth (Hz)
            
        Returns:
            Channel capacity (bps)
        """
        sinr_linear = 10**(sinr_db / 10)
        capacity = bandwidth * np.log2(1 + sinr_linear)
        
        return capacity

    def add_fast_fading(self, signal_power: float, fading_type: str = "rayleigh") -> float:
        """
        Add fast fading effects
        
        Args:
            signal_power: Original signal power (dBm)
            fading_type: Type of fading ("rayleigh", "rician", "nakagami")
            
        Returns:
            Signal power with fading (dBm)
        """
        if fading_type == "rayleigh":
            # Rayleigh fading
            fading_db = 20 * np.log10(np.abs(np.random.normal(0, 1) + 1j * np.random.normal(0, 1)) / np.sqrt(2))
        elif fading_type == "rician":
            # Rician fading with K=10 dB
            k_linear = 10**(10/10)  # K factor
            los_component = np.sqrt(k_linear / (k_linear + 1))
            multipath_component = np.sqrt(1 / (k_linear + 1)) * (np.random.normal(0, 1) + 1j * np.random.normal(0, 1)) / np.sqrt(2)
            total_fading = los_component + multipath_component
            fading_db = 20 * np.log10(np.abs(total_fading))
        else:
            # No fading
            fading_db = 0
            
        return signal_power + fading_db

    def get_channel_state_info(self, distance: float, tx_height: float = 25.0,
                             rx_height: float = 1.5) -> Dict[str, Any]:
        """
        Get comprehensive channel state information
        
        Returns:
            Dictionary with channel parameters
        """
        path_loss = self.calculate_path_loss(distance, tx_height, rx_height)
        
        # Assume standard parameters
        tx_power = 46  # dBm (40W)
        bandwidth = 100e6  # 100 MHz
        
        rx_power = self.calculate_received_power(tx_power, distance, tx_height, rx_height)
        noise_power = self.calculate_thermal_noise(bandwidth)
        sinr = self.calculate_sinr(rx_power, -120, bandwidth)  # Assume -120 dBm interference
        capacity = self.calculate_capacity(sinr, bandwidth)
        
        return {
            'distance': distance,
            'path_loss_db': path_loss,
            'received_power_dbm': rx_power,
            'noise_power_dbm': noise_power,
            'sinr_db': sinr,
            'capacity_bps': capacity,
            'channel_type': self.channel_type.value,
            'frequency_ghz': self.frequency / 1e9
        }