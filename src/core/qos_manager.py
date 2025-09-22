"""
5QI QoS Management System

Implements the 3GPP 5QI (5G QoS Identifier) framework for mapping
QoS requirements to network parameters.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Resource allocation types according to 3GPP TS 23.501"""
    GBR = "Guaranteed Bit Rate"
    NON_GBR = "Non-Guaranteed Bit Rate"
    DELAY_CRITICAL_GBR = "Delay Critical GBR"


@dataclass
class QoSCharacteristics:
    """QoS characteristics for a 5QI value"""
    priority_level: int
    packet_delay_budget_ms: int
    packet_error_rate: float
    default_max_data_burst: Optional[int]
    default_averaging_window: Optional[int]
    resource_type: ResourceType


class FiveQI:
    """
    5G QoS Identifier (5QI) implementation based on 3GPP TS 23.501 Table 5.7.4-1
    """
    
    # Standardized 5QI values with their characteristics
    QI_MAPPING = {
        # GBR Resource Types
        1: QoSCharacteristics(20, 100, 1e-2, 1354, 2000, ResourceType.GBR),  # Conversational Voice
        2: QoSCharacteristics(40, 150, 1e-3, 1354, 2000, ResourceType.GBR),  # Conversational Video
        3: QoSCharacteristics(30, 50, 1e-3, 1354, 2000, ResourceType.GBR),   # Real-time Gaming
        4: QoSCharacteristics(50, 300, 1e-6, 1354, 2000, ResourceType.GBR),  # Non-conversational Video
        65: QoSCharacteristics(7, 75, 1e-2, 1354, 2000, ResourceType.GBR),   # Mission Critical Voice
        66: QoSCharacteristics(20, 100, 1e-2, 1354, 2000, ResourceType.GBR), # Non-mission Critical Voice
        67: QoSCharacteristics(15, 100, 1e-3, 1354, 2000, ResourceType.GBR), # Mission Critical Video
        75: QoSCharacteristics(25, 50, 1e-2, 1354, 2000, ResourceType.GBR),  # V2X Messages
        
        # Delay Critical GBR
        82: QoSCharacteristics(19, 10, 1e-4, 255, 2000, ResourceType.DELAY_CRITICAL_GBR), # Discrete Automation
        83: QoSCharacteristics(22, 10, 1e-4, 1354, 2000, ResourceType.DELAY_CRITICAL_GBR), # Discrete Automation
        84: QoSCharacteristics(24, 30, 1e-5, 2000, 2000, ResourceType.DELAY_CRITICAL_GBR), # Intelligent Transport
        85: QoSCharacteristics(21, 5, 1e-5, 255, 2000, ResourceType.DELAY_CRITICAL_GBR),  # Electricity Distribution
        
        # Non-GBR Resource Types
        5: QoSCharacteristics(10, 100, 1e-6, None, None, ResourceType.NON_GBR), # IMS Signaling
        6: QoSCharacteristics(60, 300, 1e-6, None, None, ResourceType.NON_GBR), # Video (buffered)
        7: QoSCharacteristics(70, 100, 1e-3, None, None, ResourceType.NON_GBR), # Voice, Interactive Gaming
        8: QoSCharacteristics(80, 300, 1e-6, None, None, ResourceType.NON_GBR), # Video (buffered)
        9: QoSCharacteristics(90, 300, 1e-6, None, None, ResourceType.NON_GBR), # Video (buffered)
        69: QoSCharacteristics(5, 60, 1e-6, None, None, ResourceType.NON_GBR),  # Mission Critical delay sensitive
        70: QoSCharacteristics(55, 200, 1e-6, None, None, ResourceType.NON_GBR), # Mission Critical data
        79: QoSCharacteristics(65, 50, 1e-2, None, None, ResourceType.NON_GBR),  # V2X Messages
        80: QoSCharacteristics(68, 10, 1e-6, None, None, ResourceType.NON_GBR),  # Low Latency eMBB
    }

    @classmethod
    def get_qos_characteristics(cls, qi_value: int) -> Optional[QoSCharacteristics]:
        """Get QoS characteristics for a given 5QI value"""
        return cls.QI_MAPPING.get(qi_value)

    @classmethod
    def is_gbr(cls, qi_value: int) -> bool:
        """Check if 5QI requires guaranteed bit rate"""
        qos = cls.get_qos_characteristics(qi_value)
        return qos is not None and qos.resource_type in [ResourceType.GBR, ResourceType.DELAY_CRITICAL_GBR]

    @classmethod
    def get_all_qi_values(cls) -> list:
        """Get all available 5QI values"""
        return list(cls.QI_MAPPING.keys())


class QoSManager:
    """
    QoS Manager for handling 5QI-based QoS operations in the simulation
    """
    
    def __init__(self):
        self.active_flows: Dict[int, QoSCharacteristics] = {}
        logger.info("QoS Manager initialized")

    def create_flow(self, flow_id: int, qi_value: int) -> bool:
        """
        Create a new QoS flow with specified 5QI
        
        Args:
            flow_id: Unique flow identifier
            qi_value: 5QI value (1-9, 65-70, 75, 79-85)
            
        Returns:
            True if flow created successfully, False otherwise
        """
        qos_char = FiveQI.get_qos_characteristics(qi_value)
        if qos_char is None:
            logger.error(f"Invalid 5QI value: {qi_value}")
            return False
            
        self.active_flows[flow_id] = qos_char
        logger.info(f"Created QoS flow {flow_id} with 5QI {qi_value}")
        return True

    def get_flow_characteristics(self, flow_id: int) -> Optional[QoSCharacteristics]:
        """Get QoS characteristics for an active flow"""
        return self.active_flows.get(flow_id)

    def remove_flow(self, flow_id: int) -> bool:
        """Remove a QoS flow"""
        if flow_id in self.active_flows:
            del self.active_flows[flow_id]
            logger.info(f"Removed QoS flow {flow_id}")
            return True
        return False

    def get_priority_level(self, flow_id: int) -> Optional[int]:
        """Get priority level for a flow (lower values = higher priority)"""
        qos = self.get_flow_characteristics(flow_id)
        return qos.priority_level if qos else None

    def get_packet_delay_budget(self, flow_id: int) -> Optional[int]:
        """Get packet delay budget in milliseconds"""
        qos = self.get_flow_characteristics(flow_id)
        return qos.packet_delay_budget_ms if qos else None

    def get_packet_error_rate(self, flow_id: int) -> Optional[float]:
        """Get target packet error rate"""
        qos = self.get_flow_characteristics(flow_id)
        return qos.packet_error_rate if qos else None

    def is_gbr_flow(self, flow_id: int) -> bool:
        """Check if flow requires guaranteed bit rate"""
        qos = self.get_flow_characteristics(flow_id)
        return qos is not None and qos.resource_type in [ResourceType.GBR, ResourceType.DELAY_CRITICAL_GBR]

    def get_active_flows_count(self) -> int:
        """Get number of active flows"""
        return len(self.active_flows)

    def get_flow_summary(self) -> Dict:
        """Get summary of all active flows"""
        summary = {
            'total_flows': len(self.active_flows),
            'gbr_flows': sum(1 for qos in self.active_flows.values() 
                           if qos.resource_type in [ResourceType.GBR, ResourceType.DELAY_CRITICAL_GBR]),
            'non_gbr_flows': sum(1 for qos in self.active_flows.values() 
                               if qos.resource_type == ResourceType.NON_GBR),
            'delay_critical_flows': sum(1 for qos in self.active_flows.values() 
                                      if qos.resource_type == ResourceType.DELAY_CRITICAL_GBR)
        }
        return summary