"""
3GPP 5QI (5G QoS Identifier) mapping implementation.

This module provides the standardized mapping between 5QI values 
and QoS characteristics according to 3GPP TS 23.501.
"""

from typing import Dict, NamedTuple
from enum import Enum


class ResourceType(Enum):
    """Resource types for 5QI."""
    GBR = "GBR"  # Guaranteed Bit Rate
    NON_GBR = "Non-GBR"  # Non-Guaranteed Bit Rate
    DELAY_CRITICAL_GBR = "Delay Critical GBR"


class QoSCharacteristics(NamedTuple):
    """QoS characteristics for a 5QI."""
    resource_type: ResourceType
    priority_level: int
    packet_delay_budget: int  # milliseconds
    packet_error_rate: float
    default_max_bitrate_ul: int  # kbps (for GBR)
    default_max_bitrate_dl: int  # kbps (for GBR)
    description: str


class QCIMapping:
    """3GPP 5QI to QoS characteristics mapping."""
    
    # Standard 5QI values and their characteristics according to 3GPP TS 23.501
    _5QI_MAPPING = {
        1: QoSCharacteristics(
            ResourceType.GBR, 20, 100, 1e-2, 0, 0,
            "Conversational Voice"
        ),
        2: QoSCharacteristics(
            ResourceType.GBR, 40, 150, 1e-3, 0, 0,
            "Conversational Video (Live Streaming)"
        ),
        3: QoSCharacteristics(
            ResourceType.GBR, 30, 50, 1e-3, 0, 0,
            "Real Time Gaming"
        ),
        4: QoSCharacteristics(
            ResourceType.GBR, 50, 300, 1e-6, 0, 0,
            "Non-Conversational Video (Buffered Streaming)"
        ),
        5: QoSCharacteristics(
            ResourceType.NON_GBR, 10, 100, 1e-6, 0, 0,
            "IMS Signalling"
        ),
        6: QoSCharacteristics(
            ResourceType.NON_GBR, 60, 300, 1e-6, 0, 0,
            "Video (Buffered Streaming) TCP-based (e.g., www, e-mail, chat, ftp, p2p file sharing, progressive video, etc.)"
        ),
        7: QoSCharacteristics(
            ResourceType.NON_GBR, 70, 100, 1e-3, 0, 0,
            "Voice, Video (Live Streaming), Interactive Gaming"
        ),
        8: QoSCharacteristics(
            ResourceType.NON_GBR, 80, 300, 1e-6, 0, 0,
            "Video (Buffered Streaming) TCP-based (e.g., www, e-mail, chat, ftp, p2p file sharing, progressive video, etc.)"
        ),
        9: QoSCharacteristics(
            ResourceType.NON_GBR, 90, 300, 1e-6, 0, 0,
            "Video (Buffered Streaming) TCP-based (e.g., www, e-mail, chat, ftp, p2p file sharing, progressive video, etc.)"
        ),
        65: QoSCharacteristics(
            ResourceType.GBR, 7, 75, 1e-2, 0, 0,
            "Mission Critical User Plane Push To Talk voice (e.g., MCPTT)"
        ),
        66: QoSCharacteristics(
            ResourceType.GBR, 20, 100, 1e-2, 0, 0,
            "Non-Mission-Critical User Plane Push To Talk voice"
        ),
        67: QoSCharacteristics(
            ResourceType.GBR, 15, 100, 1e-3, 0, 0,
            "Mission Critical Video User Plane"
        ),
        # High bitrate video streaming (custom for dissertation)
        75: QoSCharacteristics(
            ResourceType.GBR, 25, 80, 1e-4, 50000, 100000,
            "High-bitrate uplink video streaming"
        ),
    }
    
    @classmethod
    def get_qos_characteristics(cls, qci: int) -> QoSCharacteristics:
        """Get QoS characteristics for a given 5QI value."""
        if qci not in cls._5QI_MAPPING:
            raise ValueError(f"Unknown 5QI value: {qci}")
        return cls._5QI_MAPPING[qci]
    
    @classmethod
    def get_supported_qcis(cls) -> list[int]:
        """Get list of supported 5QI values."""
        return list(cls._5QI_MAPPING.keys())
    
    @classmethod
    def is_gbr_service(cls, qci: int) -> bool:
        """Check if a 5QI corresponds to a GBR service."""
        characteristics = cls.get_qos_characteristics(qci)
        return characteristics.resource_type in [ResourceType.GBR, ResourceType.DELAY_CRITICAL_GBR]
    
    @classmethod
    def get_priority_level(cls, qci: int) -> int:
        """Get priority level for a given 5QI."""
        return cls.get_qos_characteristics(qci).priority_level
    
    @classmethod
    def get_packet_delay_budget(cls, qci: int) -> int:
        """Get packet delay budget in milliseconds for a given 5QI."""
        return cls.get_qos_characteristics(qci).packet_delay_budget
    
    @classmethod
    def get_packet_error_rate(cls, qci: int) -> float:
        """Get packet error rate for a given 5QI."""
        return cls.get_qos_characteristics(qci).packet_error_rate