"""
Metrics Collection System for 5G NR Simulation

This module implements comprehensive metrics collection and analysis
for simulation performance evaluation.
"""

import simpy
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class PacketMetric:
    """Individual packet metrics"""
    packet_id: int
    ue_id: int
    flow_id: int
    creation_time: float
    transmission_time: float
    processing_time: float
    size: int
    qi_value: int
    end_to_end_delay: float
    success: bool


@dataclass
class ThroughputMetric:
    """Throughput measurement"""
    timestamp: float
    ue_id: int
    gnb_id: int
    throughput_bps: float
    signal_strength: float


@dataclass
class HandoverMetric:
    """Handover event metrics"""
    timestamp: float
    ue_id: int
    source_gnb: Optional[int]
    target_gnb: int
    duration: float
    success: bool
    cause: str


class MetricsCollector:
    """
    Comprehensive metrics collection system for simulation analysis
    """
    
    def __init__(self):
        # Packet-level metrics
        self.packet_metrics: List[PacketMetric] = []
        
        # Throughput metrics
        self.throughput_metrics: List[ThroughputMetric] = []
        
        # Handover metrics
        self.handover_events: List[HandoverMetric] = []
        
        # System-level metrics
        self.system_metrics: Dict[float, Dict] = {}  # timestamp -> metrics
        
        # Performance counters
        self.counters = {
            'total_packets_sent': 0,
            'total_packets_delivered': 0,
            'total_packets_dropped': 0,
            'total_handovers': 0,
            'successful_handovers': 0,
            'failed_handovers': 0
        }
        
        # Time series data
        self.time_series = defaultdict(list)  # metric_name -> [(time, value), ...]
        
        logger.info("Metrics Collector initialized")

    def record_packet(self, packet_info: Dict[str, Any]):
        """Record packet transmission metrics"""
        metric = PacketMetric(
            packet_id=packet_info.get('id', 0),
            ue_id=packet_info.get('source_ue', 0),
            flow_id=packet_info.get('flow_id', 0),
            creation_time=packet_info.get('creation_time', 0.0),
            transmission_time=packet_info.get('transmission_time', 0.0),
            processing_time=packet_info.get('processing_time', 0.0),
            size=packet_info.get('size', 0),
            qi_value=packet_info.get('qi_value', 0),
            end_to_end_delay=packet_info.get('total_delay', 0.0),
            success=packet_info.get('success', True)
        )
        
        self.packet_metrics.append(metric)
        
        # Update counters
        self.counters['total_packets_sent'] += 1
        if metric.success:
            self.counters['total_packets_delivered'] += 1
        else:
            self.counters['total_packets_dropped'] += 1

    def record_throughput(self, timestamp: float, ue_id: int, gnb_id: int,
                         throughput: float, signal_strength: float):
        """Record throughput measurement"""
        metric = ThroughputMetric(
            timestamp=timestamp,
            ue_id=ue_id,
            gnb_id=gnb_id,
            throughput_bps=throughput,
            signal_strength=signal_strength
        )
        
        self.throughput_metrics.append(metric)
        
        # Add to time series
        self.time_series['throughput'].append((timestamp, throughput))

    def record_handover(self, handover_info: Dict[str, Any]):
        """Record handover event"""
        metric = HandoverMetric(
            timestamp=handover_info.get('time', 0.0),
            ue_id=handover_info.get('ue_id', 0),
            source_gnb=handover_info.get('source_gnb'),
            target_gnb=handover_info.get('target_gnb', 0),
            duration=handover_info.get('duration', 0.0),
            success=handover_info.get('success', True),
            cause=handover_info.get('cause', 'unknown')
        )
        
        self.handover_events.append(metric)
        
        # Update counters
        self.counters['total_handovers'] += 1
        if metric.success:
            self.counters['successful_handovers'] += 1
        else:
            self.counters['failed_handovers'] += 1

    def record_system_snapshot(self, timestamp: float, ues: List, gnbs: List):
        """Record system-wide metrics snapshot"""
        # UE metrics
        ue_metrics = {}
        for ue in ues:
            ue_stats = ue.get_statistics()
            ue_metrics[ue.ue_id] = {
                'position': ue_stats['position'],
                'connected_gnb': ue_stats['connected_gnb'],
                'signal_strength': ue_stats['signal_strength'],
                'packets_sent': ue_stats['packets_sent'],
                'delivery_ratio': ue_stats['delivery_ratio']
            }
        
        # gNB metrics
        gnb_metrics = {}
        for gnb in gnbs:
            gnb_stats = gnb.get_statistics()
            gnb_metrics[gnb.gnb_id] = {
                'connected_ues': gnb_stats['connected_ues'],
                'packets_processed': gnb_stats['packets_processed'],
                'resource_utilization': gnb_stats['resource_utilization'],
                'average_delay': gnb_stats['average_delay']
            }
        
        # Store snapshot
        self.system_metrics[timestamp] = {
            'ues': ue_metrics,
            'gnbs': gnb_metrics,
            'network_load': sum(len(gnb.connected_ues) for gnb in gnbs),
            'active_connections': sum(1 for ue in ues if ue.is_connected())
        }

    def collection_process(self, env: simpy.Environment, ues: List, gnbs: List):
        """Periodic metrics collection process"""
        collection_interval = 1.0  # 1 second
        
        while True:
            # Record system snapshot
            self.record_system_snapshot(env.now, ues, gnbs)
            
            # Calculate and record aggregate metrics
            self._update_aggregate_metrics(env.now, ues, gnbs)
            
            yield env.timeout(collection_interval)

    def _update_aggregate_metrics(self, timestamp: float, ues: List, gnbs: List):
        """Update aggregate performance metrics"""
        # Calculate network-wide throughput
        total_throughput = 0.0
        active_ues = 0
        
        for ue in ues:
            if ue.is_connected() and ue.connected_gnb:
                # Estimate current throughput (simplified)
                distance = ue.get_distance_to_gnb()
                if distance:
                    throughput = ue.connected_gnb.calculate_throughput(
                        ue.ue_id, ue.connection_quality)
                    total_throughput += throughput
                    active_ues += 1
                    
                    # Record individual throughput
                    self.record_throughput(
                        timestamp, ue.ue_id, ue.connected_gnb.gnb_id,
                        throughput, ue.connection_quality)
        
        # Add to time series
        self.time_series['network_throughput'].append((timestamp, total_throughput))
        self.time_series['active_ues'].append((timestamp, active_ues))
        
        # Calculate average signal strength
        signal_strengths = [ue.connection_quality for ue in ues if ue.is_connected()]
        avg_signal = np.mean(signal_strengths) if signal_strengths else 0.0
        self.time_series['average_signal_strength'].append((timestamp, avg_signal))
        
        # Calculate resource utilization
        total_utilization = 0.0
        for gnb in gnbs:
            stats = gnb.get_statistics()
            total_utilization += stats['resource_utilization']
        
        avg_utilization = total_utilization / len(gnbs) if gnbs else 0.0
        self.time_series['resource_utilization'].append((timestamp, avg_utilization))

    def get_packet_delay_statistics(self) -> Dict[str, float]:
        """Calculate packet delay statistics"""
        if not self.packet_metrics:
            return {}
            
        delays = [p.end_to_end_delay for p in self.packet_metrics if p.success]
        
        if not delays:
            return {}
            
        return {
            'mean_delay': np.mean(delays),
            'median_delay': np.median(delays),
            'min_delay': np.min(delays),
            'max_delay': np.max(delays),
            'std_delay': np.std(delays),
            'percentile_95': np.percentile(delays, 95),
            'percentile_99': np.percentile(delays, 99)
        }

    def get_throughput_statistics(self) -> Dict[str, float]:
        """Calculate throughput statistics"""
        if not self.throughput_metrics:
            return {}
            
        throughputs = [t.throughput_bps for t in self.throughput_metrics]
        
        return {
            'mean_throughput': np.mean(throughputs),
            'median_throughput': np.median(throughputs),
            'min_throughput': np.min(throughputs),
            'max_throughput': np.max(throughputs),
            'std_throughput': np.std(throughputs),
            'total_data_volume': sum(throughputs) * len(throughputs)  # Simplified
        }

    def get_handover_statistics(self) -> Dict[str, Any]:
        """Calculate handover statistics"""
        if not self.handover_events:
            return {}
            
        successful_handovers = [h for h in self.handover_events if h.success]
        failed_handovers = [h for h in self.handover_events if not h.success]
        
        stats = {
            'total_handovers': len(self.handover_events),
            'successful_handovers': len(successful_handovers),
            'failed_handovers': len(failed_handovers),
            'success_rate': len(successful_handovers) / len(self.handover_events) if self.handover_events else 0.0
        }
        
        if successful_handovers:
            durations = [h.duration for h in successful_handovers]
            stats.update({
                'mean_handover_duration': np.mean(durations),
                'median_handover_duration': np.median(durations),
                'max_handover_duration': np.max(durations),
                'min_handover_duration': np.min(durations)
            })
        
        return stats

    def get_qos_performance(self) -> Dict[int, Dict[str, Any]]:
        """Get QoS performance per 5QI value"""
        qos_stats = defaultdict(lambda: {
            'packets_sent': 0,
            'packets_delivered': 0,
            'delays': [],
            'delivery_ratio': 0.0
        })
        
        for packet in self.packet_metrics:
            qi = packet.qi_value
            qos_stats[qi]['packets_sent'] += 1
            
            if packet.success:
                qos_stats[qi]['packets_delivered'] += 1
                qos_stats[qi]['delays'].append(packet.end_to_end_delay)
        
        # Calculate final statistics
        result = {}
        for qi, stats in qos_stats.items():
            if stats['packets_sent'] > 0:
                stats['delivery_ratio'] = stats['packets_delivered'] / stats['packets_sent']
            
            if stats['delays']:
                stats['mean_delay'] = np.mean(stats['delays'])
                stats['percentile_95_delay'] = np.percentile(stats['delays'], 95)
            else:
                stats['mean_delay'] = 0.0
                stats['percentile_95_delay'] = 0.0
            
            # Remove raw delays list for cleaner output
            del stats['delays']
            result[qi] = stats
        
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive simulation summary"""
        summary = {
            'simulation_duration': max([t for t, _ in self.time_series['network_throughput']], default=0.0),
            'counters': self.counters.copy(),
            'packet_statistics': self.get_packet_delay_statistics(),
            'throughput_statistics': self.get_throughput_statistics(),
            'handover_statistics': self.get_handover_statistics(),
            'qos_performance': self.get_qos_performance(),
            'total_packets': len(self.packet_metrics),
            'total_throughput_samples': len(self.throughput_metrics),
            'total_handover_events': len(self.handover_events)
        }
        
        return summary

    def export_to_csv(self, output_dir: str = "results"):
        """Export metrics to CSV files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Export packet metrics
        if self.packet_metrics:
            packet_df = pd.DataFrame([asdict(p) for p in self.packet_metrics])
            packet_df.to_csv(f"{output_dir}/packet_metrics.csv", index=False)
            
        # Export throughput metrics
        if self.throughput_metrics:
            throughput_df = pd.DataFrame([asdict(t) for t in self.throughput_metrics])
            throughput_df.to_csv(f"{output_dir}/throughput_metrics.csv", index=False)
            
        # Export handover metrics
        if self.handover_events:
            handover_df = pd.DataFrame([asdict(h) for h in self.handover_events])
            handover_df.to_csv(f"{output_dir}/handover_metrics.csv", index=False)
            
        # Export time series data
        for metric_name, data in self.time_series.items():
            if data:
                ts_df = pd.DataFrame(data, columns=['timestamp', metric_name])
                ts_df.to_csv(f"{output_dir}/timeseries_{metric_name}.csv", index=False)
        
        logger.info(f"Metrics exported to {output_dir}/")

    def save_summary_json(self, filename: str = "simulation_summary.json"):
        """Save summary to JSON file"""
        summary = self.get_summary()
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
            
        logger.info(f"Summary saved to {filename}")

    def reset(self):
        """Reset all collected metrics"""
        self.packet_metrics.clear()
        self.throughput_metrics.clear()
        self.handover_events.clear()
        self.system_metrics.clear()
        self.time_series.clear()
        
        self.counters = {
            'total_packets_sent': 0,
            'total_packets_delivered': 0,
            'total_packets_dropped': 0,
            'total_handovers': 0,
            'successful_handovers': 0,
            'failed_handovers': 0
        }
        
        logger.info("Metrics collector reset")