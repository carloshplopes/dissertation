"""
Metrics collection and analysis for 5G NR simulations.

This module provides comprehensive metrics collection, analysis,
and result generation capabilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class SimulationResults:
    """Container for simulation results."""
    metrics_data: pd.DataFrame
    summary_statistics: Dict[str, Any]
    ue_statistics: Dict[int, Dict[str, Any]]
    gnb_statistics: Dict[int, Dict[str, Any]]
    handover_statistics: Dict[str, Any]
    execution_time: float = 0.0
    config: Optional[Any] = None


class MetricsCollector:
    """Collects and analyzes simulation metrics."""
    
    def __init__(self):
        self.measurements: List[Dict] = []
        self.time_series_data = {
            'throughput_dl': [],
            'throughput_ul': [],
            'handover_rate': [],
            'connection_rate': [],
            'resource_utilization': []
        }
    
    def add_measurement(self, measurement: Dict):
        """Add a measurement point."""
        self.measurements.append(measurement.copy())
        
        # Update time series data
        timestamp = measurement['timestamp']
        system_metrics = measurement.get('system_metrics', {})
        
        self.time_series_data['throughput_dl'].append({
            'timestamp': timestamp,
            'value': system_metrics.get('average_throughput_dl_mbps', 0)
        })
        
        self.time_series_data['throughput_ul'].append({
            'timestamp': timestamp,
            'value': system_metrics.get('average_throughput_ul_mbps', 0)
        })
        
        handover_stats = system_metrics.get('handover_statistics', {})
        self.time_series_data['handover_rate'].append({
            'timestamp': timestamp,
            'value': handover_stats.get('total_attempts', 0)
        })
        
        self.time_series_data['connection_rate'].append({
            'timestamp': timestamp,
            'value': system_metrics.get('connection_rate', 0)
        })
        
        # Average resource utilization across gNBs
        gnb_metrics = measurement.get('gnb_metrics', {})
        avg_utilization = np.mean([
            gnb.get('resource_utilization', 0) for gnb in gnb_metrics.values()
        ]) if gnb_metrics else 0
        
        self.time_series_data['resource_utilization'].append({
            'timestamp': timestamp,
            'value': avg_utilization
        })
    
    def generate_results(self) -> SimulationResults:
        """Generate comprehensive simulation results."""
        if not self.measurements:
            return SimulationResults(
                metrics_data=pd.DataFrame(),
                summary_statistics={},
                ue_statistics={},
                gnb_statistics={},
                handover_statistics={}
            )
        
        # Convert measurements to DataFrame
        df = self._create_dataframe()
        
        # Generate statistics
        summary_stats = self._calculate_summary_statistics(df)
        ue_stats = self._calculate_ue_statistics(df)
        gnb_stats = self._calculate_gnb_statistics(df)
        handover_stats = self._calculate_handover_statistics()
        
        return SimulationResults(
            metrics_data=df,
            summary_statistics=summary_stats,
            ue_statistics=ue_stats,
            gnb_statistics=gnb_stats,
            handover_statistics=handover_stats
        )
    
    def _create_dataframe(self) -> pd.DataFrame:
        """Create a pandas DataFrame from measurements."""
        rows = []
        
        for measurement in self.measurements:
            timestamp = measurement['timestamp']
            system_metrics = measurement.get('system_metrics', {})
            
            # System-level row
            row = {
                'timestamp': timestamp,
                'metric_type': 'system',
                'entity_id': 'system',
                'throughput_dl_mbps': system_metrics.get('average_throughput_dl_mbps', 0),
                'throughput_ul_mbps': system_metrics.get('average_throughput_ul_mbps', 0),
                'connection_rate': system_metrics.get('connection_rate', 0),
                'total_ues': system_metrics.get('total_ues', 0),
                'connected_ues': system_metrics.get('connected_ues', 0)
            }
            rows.append(row)
            
            # UE-level rows
            ue_metrics = measurement.get('ue_metrics', {})
            for ue_id, metrics in ue_metrics.items():
                row = {
                    'timestamp': timestamp,
                    'metric_type': 'ue',
                    'entity_id': ue_id,
                    'position_x': metrics.get('position', [0, 0])[0],
                    'position_y': metrics.get('position', [0, 0])[1],
                    'connected_gnb': metrics.get('connected_gnb'),
                    'speed': metrics.get('speed', 0),
                    'throughput_dl_mbps': metrics.get('throughput_dl_mbps', 0),
                    'throughput_ul_mbps': metrics.get('throughput_ul_mbps', 0)
                }
                
                # Add channel characteristics if available
                channel_char = metrics.get('channel_characteristics', {})
                row.update({
                    'distance': channel_char.get('distance', 0),
                    'path_loss': channel_char.get('path_loss', 0),
                    'sinr_db': channel_char.get('sinr_db', 0),
                    'bler': channel_char.get('bler', 0)
                })
                
                # Add best RSRP
                rsrp_measurements = metrics.get('rsrp_measurements', [])
                if rsrp_measurements:
                    row['best_rsrp_dbm'] = rsrp_measurements[0][1]
                
                rows.append(row)
            
            # gNB-level rows
            gnb_metrics = measurement.get('gnb_metrics', {})
            for gnb_id, metrics in gnb_metrics.items():
                row = {
                    'timestamp': timestamp,
                    'metric_type': 'gnb',
                    'entity_id': gnb_id,
                    'position_x': metrics.get('position', [0, 0])[0],
                    'position_y': metrics.get('position', [0, 0])[1],
                    'connected_ues': metrics.get('connected_ues', 0),
                    'resource_utilization': metrics.get('resource_utilization', 0),
                    'load': metrics.get('load', 0),
                    'handovers_in': metrics.get('handovers_in', 0),
                    'handovers_out': metrics.get('handovers_out', 0)
                }
                rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _calculate_summary_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics."""
        system_df = df[df['metric_type'] == 'system']
        ue_df = df[df['metric_type'] == 'ue']
        gnb_df = df[df['metric_type'] == 'gnb']
        
        if system_df.empty:
            return {}
        
        return {
            'simulation_duration': system_df['timestamp'].max(),
            'average_throughput_dl_mbps': system_df['throughput_dl_mbps'].mean(),
            'average_throughput_ul_mbps': system_df['throughput_ul_mbps'].mean(),
            'peak_throughput_dl_mbps': ue_df['throughput_dl_mbps'].max() if not ue_df.empty else 0,
            'peak_throughput_ul_mbps': ue_df['throughput_ul_mbps'].max() if not ue_df.empty else 0,
            'average_connection_rate': system_df['connection_rate'].mean(),
            'min_connection_rate': system_df['connection_rate'].min(),
            'average_resource_utilization': gnb_df['resource_utilization'].mean() if not gnb_df.empty else 0,
            'peak_resource_utilization': gnb_df['resource_utilization'].max() if not gnb_df.empty else 0,
            'total_measurements': len(self.measurements),
            'unique_ues': len(ue_df['entity_id'].unique()) if not ue_df.empty else 0,
            'unique_gnbs': len(gnb_df['entity_id'].unique()) if not gnb_df.empty else 0
        }
    
    def _calculate_ue_statistics(self, df: pd.DataFrame) -> Dict[int, Dict[str, Any]]:
        """Calculate per-UE statistics."""
        ue_df = df[df['metric_type'] == 'ue']
        ue_stats = {}
        
        for ue_id in ue_df['entity_id'].unique():
            ue_data = ue_df[ue_df['entity_id'] == ue_id]
            
            # Calculate distance traveled
            positions = ue_data[['position_x', 'position_y']].values
            total_distance = 0
            if len(positions) > 1:
                for i in range(1, len(positions)):
                    dist = np.sqrt((positions[i][0] - positions[i-1][0])**2 + 
                                 (positions[i][1] - positions[i-1][1])**2)
                    total_distance += dist
            
            # Handover count (simplified - count gNB changes)
            handover_count = 0
            gnb_connections = ue_data['connected_gnb'].dropna().values
            if len(gnb_connections) > 1:
                for i in range(1, len(gnb_connections)):
                    if gnb_connections[i] != gnb_connections[i-1]:
                        handover_count += 1
            
            ue_stats[ue_id] = {
                'average_throughput_dl_mbps': ue_data['throughput_dl_mbps'].mean(),
                'average_throughput_ul_mbps': ue_data['throughput_ul_mbps'].mean(),
                'peak_throughput_dl_mbps': ue_data['throughput_dl_mbps'].max(),
                'peak_throughput_ul_mbps': ue_data['throughput_ul_mbps'].max(),
                'average_speed': ue_data['speed'].mean(),
                'max_speed': ue_data['speed'].max(),
                'total_distance_traveled': total_distance,
                'handover_count': handover_count,
                'average_sinr_db': ue_data['sinr_db'].mean() if 'sinr_db' in ue_data.columns else 0,
                'average_rsrp_dbm': ue_data['best_rsrp_dbm'].mean() if 'best_rsrp_dbm' in ue_data.columns else 0,
                'connection_time_ratio': (ue_data['connected_gnb'].notna().sum() / len(ue_data)) if not ue_data.empty else 0
            }
        
        return ue_stats
    
    def _calculate_gnb_statistics(self, df: pd.DataFrame) -> Dict[int, Dict[str, Any]]:
        """Calculate per-gNB statistics."""
        gnb_df = df[df['metric_type'] == 'gnb']
        gnb_stats = {}
        
        for gnb_id in gnb_df['entity_id'].unique():
            gnb_data = gnb_df[gnb_df['entity_id'] == gnb_id]
            
            gnb_stats[gnb_id] = {
                'average_connected_ues': gnb_data['connected_ues'].mean(),
                'peak_connected_ues': gnb_data['connected_ues'].max(),
                'average_resource_utilization': gnb_data['resource_utilization'].mean(),
                'peak_resource_utilization': gnb_data['resource_utilization'].max(),
                'average_load': gnb_data['load'].mean(),
                'peak_load': gnb_data['load'].max(),
                'total_handovers_in': gnb_data['handovers_in'].iloc[-1] if not gnb_data.empty else 0,
                'total_handovers_out': gnb_data['handovers_out'].iloc[-1] if not gnb_data.empty else 0,
                'position': (gnb_data['position_x'].iloc[0], gnb_data['position_y'].iloc[0]) if not gnb_data.empty else (0, 0)
            }
        
        return gnb_stats
    
    def _calculate_handover_statistics(self) -> Dict[str, Any]:
        """Calculate handover statistics from the last measurement."""
        if not self.measurements:
            return {}
        
        last_measurement = self.measurements[-1]
        system_metrics = last_measurement.get('system_metrics', {})
        return system_metrics.get('handover_statistics', {})
    
    def export_results(self, results: SimulationResults, output_file: str):
        """Export results to file."""
        if output_file.endswith('.json'):
            self._export_json(results, output_file)
        elif output_file.endswith('.csv'):
            self._export_csv(results, output_file)
        elif output_file.endswith('.xlsx'):
            self._export_excel(results, output_file)
        else:
            raise ValueError(f"Unsupported file format: {output_file}")
    
    def _export_json(self, results: SimulationResults, filename: str):
        """Export results to JSON."""
        export_data = {
            'summary_statistics': results.summary_statistics,
            'ue_statistics': results.ue_statistics,
            'gnb_statistics': results.gnb_statistics,
            'handover_statistics': results.handover_statistics,
            'execution_time': results.execution_time
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    def _export_csv(self, results: SimulationResults, filename: str):
        """Export results to CSV."""
        results.metrics_data.to_csv(filename, index=False)
    
    def _export_excel(self, results: SimulationResults, filename: str):
        """Export results to Excel."""
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            results.metrics_data.to_excel(writer, sheet_name='Raw Data', index=False)
            
            # Summary statistics
            summary_df = pd.DataFrame([results.summary_statistics]).T
            summary_df.columns = ['Value']
            summary_df.to_excel(writer, sheet_name='Summary Statistics')
            
            # UE statistics
            if results.ue_statistics:
                ue_df = pd.DataFrame(results.ue_statistics).T
                ue_df.to_excel(writer, sheet_name='UE Statistics')
            
            # gNB statistics
            if results.gnb_statistics:
                gnb_df = pd.DataFrame(results.gnb_statistics).T
                gnb_df.to_excel(writer, sheet_name='gNB Statistics')
    
    def create_visualization(self, results: SimulationResults, output_dir: str = "./results/"):
        """Create visualization plots."""
        try:
            plt.style.use('seaborn-v0_8')
        except OSError:
            plt.style.use('default')
        
        # Time series plots
        self._plot_throughput_time_series(output_dir)
        self._plot_connection_rate_time_series(output_dir)
        self._plot_resource_utilization_time_series(output_dir)
        
        # Statistical plots
        self._plot_ue_performance_distribution(results, output_dir)
        self._plot_gnb_load_distribution(results, output_dir)
        
        # Network topology
        self._plot_network_topology(results, output_dir)
    
    def _plot_throughput_time_series(self, output_dir: str):
        """Plot throughput time series."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Downlink throughput
        dl_data = self.time_series_data['throughput_dl']
        timestamps = [d['timestamp'] for d in dl_data]
        values = [d['value'] for d in dl_data]
        ax1.plot(timestamps, values)
        ax1.set_title('Average Downlink Throughput Over Time')
        ax1.set_ylabel('Throughput (Mbps)')
        ax1.grid(True)
        
        # Uplink throughput
        ul_data = self.time_series_data['throughput_ul']
        timestamps = [d['timestamp'] for d in ul_data]
        values = [d['value'] for d in ul_data]
        ax2.plot(timestamps, values, color='orange')
        ax2.set_title('Average Uplink Throughput Over Time')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Throughput (Mbps)')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/throughput_time_series.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_connection_rate_time_series(self, output_dir: str):
        """Plot connection rate time series."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        conn_data = self.time_series_data['connection_rate']
        timestamps = [d['timestamp'] for d in conn_data]
        values = [d['value'] for d in conn_data]
        
        ax.plot(timestamps, values, linewidth=2)
        ax.set_title('UE Connection Rate Over Time')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Connection Rate')
        ax.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/connection_rate.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_resource_utilization_time_series(self, output_dir: str):
        """Plot resource utilization time series."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        util_data = self.time_series_data['resource_utilization']
        timestamps = [d['timestamp'] for d in util_data]
        values = [d['value'] for d in util_data]
        
        ax.plot(timestamps, values, color='green', linewidth=2)
        ax.set_title('Average Resource Utilization Over Time')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Resource Utilization')
        ax.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/resource_utilization.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_ue_performance_distribution(self, results: SimulationResults, output_dir: str):
        """Plot UE performance distributions."""
        if not results.ue_statistics:
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        ue_stats = results.ue_statistics
        
        # Throughput distributions
        dl_throughput = [stats['average_throughput_dl_mbps'] for stats in ue_stats.values()]
        ul_throughput = [stats['average_throughput_ul_mbps'] for stats in ue_stats.values()]
        
        ax1.hist(dl_throughput, bins=20, alpha=0.7, edgecolor='black')
        ax1.set_title('Distribution of Average DL Throughput per UE')
        ax1.set_xlabel('Throughput (Mbps)')
        ax1.set_ylabel('Number of UEs')
        
        ax2.hist(ul_throughput, bins=20, alpha=0.7, color='orange', edgecolor='black')
        ax2.set_title('Distribution of Average UL Throughput per UE')
        ax2.set_xlabel('Throughput (Mbps)')
        ax2.set_ylabel('Number of UEs')
        
        # Speed and handover distributions
        speeds = [stats['average_speed'] for stats in ue_stats.values()]
        handovers = [stats['handover_count'] for stats in ue_stats.values()]
        
        ax3.hist(speeds, bins=20, alpha=0.7, color='green', edgecolor='black')
        ax3.set_title('Distribution of Average Speed per UE')
        ax3.set_xlabel('Speed (m/s)')
        ax3.set_ylabel('Number of UEs')
        
        ax4.hist(handovers, bins=max(1, max(handovers)+1), alpha=0.7, color='red', edgecolor='black')
        ax4.set_title('Distribution of Handover Count per UE')
        ax4.set_xlabel('Number of Handovers')
        ax4.set_ylabel('Number of UEs')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/ue_performance_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_gnb_load_distribution(self, results: SimulationResults, output_dir: str):
        """Plot gNB load distribution."""
        if not results.gnb_statistics:
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        gnb_stats = results.gnb_statistics
        
        # Load distribution
        loads = [stats['average_load'] for stats in gnb_stats.values()]
        utilizations = [stats['average_resource_utilization'] for stats in gnb_stats.values()]
        
        ax1.bar(range(len(loads)), loads, alpha=0.7, edgecolor='black')
        ax1.set_title('Average Load per gNB')
        ax1.set_xlabel('gNB ID')
        ax1.set_ylabel('Load')
        ax1.set_xticks(range(len(loads)))
        
        ax2.bar(range(len(utilizations)), utilizations, alpha=0.7, color='orange', edgecolor='black')
        ax2.set_title('Average Resource Utilization per gNB')
        ax2.set_xlabel('gNB ID')
        ax2.set_ylabel('Resource Utilization')
        ax2.set_xticks(range(len(utilizations)))
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/gnb_load_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_network_topology(self, results: SimulationResults, output_dir: str):
        """Plot network topology."""
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Plot gNBs
        if results.gnb_statistics:
            gnb_positions = [stats['position'] for stats in results.gnb_statistics.values()]
            gnb_x = [pos[0] for pos in gnb_positions]
            gnb_y = [pos[1] for pos in gnb_positions]
            
            ax.scatter(gnb_x, gnb_y, c='red', s=200, marker='^', label='gNBs', edgecolors='black')
            
            # Add gNB IDs
            for i, (x, y) in enumerate(gnb_positions):
                ax.annotate(f'gNB {i}', (x, y), xytext=(5, 5), textcoords='offset points')
        
        # Plot UE final positions (from last measurement)
        if self.measurements:
            last_measurement = self.measurements[-1]
            ue_metrics = last_measurement.get('ue_metrics', {})
            
            ue_positions = [metrics.get('position', [0, 0]) for metrics in ue_metrics.values()]
            if ue_positions:
                ue_x = [pos[0] for pos in ue_positions]
                ue_y = [pos[1] for pos in ue_positions]
                
                ax.scatter(ue_x, ue_y, c='blue', s=50, alpha=0.6, label='UEs')
        
        ax.set_title('Network Topology')
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/network_topology.png", dpi=300, bbox_inches='tight')
        plt.close()