"""
Quality of Service (QoS) module for 5G NR simulations.

This module implements the 3GPP 5QI (5G QoS Identifier) framework 
and QoS management functionality.
"""

from .qci_mapping import QCIMapping
from .qos_manager import QoSManager

__all__ = ['QCIMapping', 'QoSManager']