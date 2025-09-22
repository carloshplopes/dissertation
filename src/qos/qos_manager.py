"""
QoS Manager for handling Quality of Service in 5G NR simulations.

This module provides functionality to manage QoS flows, scheduling,
and resource allocation based on 5QI characteristics.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .qci_mapping import QCIMapping, QoSCharacteristics


@dataclass
class QoSFlow:
    """Represents a QoS flow with specific characteristics."""
    flow_id: int
    qci: int
    ue_id: int
    guaranteed_bitrate_ul: int = 0  # kbps
    guaranteed_bitrate_dl: int = 0  # kbps
    maximum_bitrate_ul: int = 0     # kbps
    maximum_bitrate_dl: int = 0     # kbps
    current_bitrate_ul: int = 0     # kbps
    current_bitrate_dl: int = 0     # kbps
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    total_delay: float = 0.0        # ms
    active: bool = True
    
    @property
    def qos_characteristics(self) -> QoSCharacteristics:
        """Get QoS characteristics for this flow."""
        return QCIMapping.get_qos_characteristics(self.qci)
    
    @property
    def packet_loss_rate(self) -> float:
        """Calculate current packet loss rate."""
        if self.packets_sent == 0:
            return 0.0
        return self.packets_lost / self.packets_sent
    
    @property
    def average_delay(self) -> float:
        """Calculate average packet delay."""
        if self.packets_received == 0:
            return 0.0
        return self.total_delay / self.packets_received


class QoSManager:
    """Manages QoS flows and resource allocation."""
    
    def __init__(self):
        self.flows: Dict[int, QoSFlow] = {}
        self.next_flow_id: int = 1
        self.total_ul_capacity: int = 100000  # kbps
        self.total_dl_capacity: int = 1000000  # kbps
        self.reserved_ul_capacity: int = 0     # kbps
        self.reserved_dl_capacity: int = 0     # kbps
    
    def create_flow(self, qci: int, ue_id: int, 
                   guaranteed_bitrate_ul: int = 0,
                   guaranteed_bitrate_dl: int = 0,
                   maximum_bitrate_ul: int = 0,
                   maximum_bitrate_dl: int = 0) -> QoSFlow:
        """Create a new QoS flow."""
        flow_id = self.next_flow_id
        self.next_flow_id += 1
        
        # Use default values from 5QI mapping if not specified
        qos_char = QCIMapping.get_qos_characteristics(qci)
        if guaranteed_bitrate_ul == 0 and qos_char.default_max_bitrate_ul > 0:
            guaranteed_bitrate_ul = qos_char.default_max_bitrate_ul
        if guaranteed_bitrate_dl == 0 and qos_char.default_max_bitrate_dl > 0:
            guaranteed_bitrate_dl = qos_char.default_max_bitrate_dl
        
        flow = QoSFlow(
            flow_id=flow_id,
            qci=qci,
            ue_id=ue_id,
            guaranteed_bitrate_ul=guaranteed_bitrate_ul,
            guaranteed_bitrate_dl=guaranteed_bitrate_dl,
            maximum_bitrate_ul=maximum_bitrate_ul or guaranteed_bitrate_ul * 2,
            maximum_bitrate_dl=maximum_bitrate_dl or guaranteed_bitrate_dl * 2
        )
        
        self.flows[flow_id] = flow
        
        # Reserve capacity for GBR flows
        if QCIMapping.is_gbr_service(qci):
            self.reserved_ul_capacity += guaranteed_bitrate_ul
            self.reserved_dl_capacity += guaranteed_bitrate_dl
        
        return flow
    
    def remove_flow(self, flow_id: int) -> bool:
        """Remove a QoS flow."""
        if flow_id not in self.flows:
            return False
        
        flow = self.flows[flow_id]
        
        # Release reserved capacity for GBR flows
        if QCIMapping.is_gbr_service(flow.qci):
            self.reserved_ul_capacity -= flow.guaranteed_bitrate_ul
            self.reserved_dl_capacity -= flow.guaranteed_bitrate_dl
        
        del self.flows[flow_id]
        return True
    
    def get_flow(self, flow_id: int) -> Optional[QoSFlow]:
        """Get a QoS flow by ID."""
        return self.flows.get(flow_id)
    
    def get_flows_by_ue(self, ue_id: int) -> List[QoSFlow]:
        """Get all flows for a specific UE."""
        return [flow for flow in self.flows.values() if flow.ue_id == ue_id]
    
    def calculate_scheduling_priority(self, flow_id: int) -> float:
        """Calculate scheduling priority for a flow (lower = higher priority)."""
        flow = self.flows.get(flow_id)
        if not flow:
            return float('inf')
        
        qos_char = flow.qos_characteristics
        
        # Base priority from 5QI
        priority = float(qos_char.priority_level)
        
        # Adjust based on current delay and error rate
        if flow.average_delay > qos_char.packet_delay_budget:
            priority -= 10.0  # Increase priority if delay budget exceeded
        
        if flow.packet_loss_rate > qos_char.packet_error_rate:
            priority -= 5.0   # Increase priority if error rate exceeded
        
        return priority
    
    def allocate_resources(self) -> Dict[int, Tuple[int, int]]:
        """Allocate UL/DL resources to flows based on priority and requirements."""
        allocations = {}
        
        # Sort flows by priority
        sorted_flows = sorted(
            self.flows.values(),
            key=lambda f: self.calculate_scheduling_priority(f.flow_id),
            reverse=False  # Lower priority value = higher priority
        )
        
        available_ul = self.total_ul_capacity - self.reserved_ul_capacity
        available_dl = self.total_dl_capacity - self.reserved_dl_capacity
        
        # First, allocate guaranteed resources for GBR flows
        for flow in sorted_flows:
            if QCIMapping.is_gbr_service(flow.qci):
                allocations[flow.flow_id] = (
                    flow.guaranteed_bitrate_ul,
                    flow.guaranteed_bitrate_dl
                )
        
        # Then, allocate remaining resources
        for flow in sorted_flows:
            if not QCIMapping.is_gbr_service(flow.qci):
                # For non-GBR flows, allocate based on available capacity
                ul_allocation = min(available_ul // len([f for f in sorted_flows if not QCIMapping.is_gbr_service(f.qci)]),
                                  flow.maximum_bitrate_ul)
                dl_allocation = min(available_dl // len([f for f in sorted_flows if not QCIMapping.is_gbr_service(f.qci)]),
                                  flow.maximum_bitrate_dl)
                
                allocations[flow.flow_id] = (ul_allocation, dl_allocation)
                available_ul -= ul_allocation
                available_dl -= dl_allocation
        
        return allocations
    
    def update_flow_statistics(self, flow_id: int, packets_sent: int = 0,
                             packets_received: int = 0, packets_lost: int = 0,
                             delay: float = 0.0):
        """Update flow statistics."""
        flow = self.flows.get(flow_id)
        if not flow:
            return
        
        flow.packets_sent += packets_sent
        flow.packets_received += packets_received
        flow.packets_lost += packets_lost
        flow.total_delay += delay
    
    def get_flow_metrics(self, flow_id: int) -> Dict:
        """Get comprehensive metrics for a flow."""
        flow = self.flows.get(flow_id)
        if not flow:
            return {}
        
        qos_char = flow.qos_characteristics
        
        return {
            'flow_id': flow.flow_id,
            'qci': flow.qci,
            'ue_id': flow.ue_id,
            'qos_characteristics': qos_char._asdict(),
            'guaranteed_bitrate_ul': flow.guaranteed_bitrate_ul,
            'guaranteed_bitrate_dl': flow.guaranteed_bitrate_dl,
            'current_bitrate_ul': flow.current_bitrate_ul,
            'current_bitrate_dl': flow.current_bitrate_dl,
            'packet_loss_rate': flow.packet_loss_rate,
            'average_delay': flow.average_delay,
            'delay_budget_violation': flow.average_delay > qos_char.packet_delay_budget,
            'error_rate_violation': flow.packet_loss_rate > qos_char.packet_error_rate,
            'packets_sent': flow.packets_sent,
            'packets_received': flow.packets_received,
            'packets_lost': flow.packets_lost
        }
    
    def get_system_metrics(self) -> Dict:
        """Get system-wide QoS metrics."""
        total_flows = len(self.flows)
        active_flows = len([f for f in self.flows.values() if f.active])
        gbr_flows = len([f for f in self.flows.values() if QCIMapping.is_gbr_service(f.qci)])
        
        if total_flows == 0:
            return {
                'total_flows': 0,
                'active_flows': 0,
                'gbr_flows': 0,
                'ul_capacity_utilization': 0.0,
                'dl_capacity_utilization': 0.0,
                'average_delay': 0.0,
                'average_packet_loss_rate': 0.0
            }
        
        total_delay = sum(f.average_delay for f in self.flows.values())
        total_packet_loss = sum(f.packet_loss_rate for f in self.flows.values())
        
        return {
            'total_flows': total_flows,
            'active_flows': active_flows,
            'gbr_flows': gbr_flows,
            'ul_capacity_utilization': self.reserved_ul_capacity / self.total_ul_capacity,
            'dl_capacity_utilization': self.reserved_dl_capacity / self.total_dl_capacity,
            'average_delay': total_delay / total_flows,
            'average_packet_loss_rate': total_packet_loss / total_flows
        }