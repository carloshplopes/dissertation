"""
Visualization utilities for 5G NR simulations.

This module provides advanced visualization capabilities for simulation results.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import seaborn as sns
from ..simulation.metrics import SimulationResults
from ..mobility.user_equipment import Position


class NetworkVisualizer:
    """Advanced visualization for 5G NR simulation results."""
    
    def __init__(self, style: str = 'seaborn-v0_8'):
        try:
            plt.style.use(style)
        except OSError:
            # Fallback to default if seaborn style not available
            plt.style.use('default')
        self.colors = plt.cm.Set3(np.linspace(0, 1, 12))
        
    def create_comprehensive_report(self, results: SimulationResults, output_dir: str = "./results/"):
        """Create a comprehensive visualization report."""
        # Create individual plots
        self.plot_network_performance_overview(results, output_dir)
        self.plot_qos_analysis(results, output_dir)
        self.plot_mobility_analysis(results, output_dir)
        self.plot_handover_analysis(results, output_dir)
        self.plot_coverage_heatmap(results, output_dir)
        
        print(f"Comprehensive visualization report created in {output_dir}")
    
    def plot_network_performance_overview(self, results: SimulationResults, output_dir: str):
        """Create network performance overview plot."""
        fig = plt.figure(figsize=(16, 12))
        
        # Create a grid layout
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # System throughput over time
        ax1 = fig.add_subplot(gs[0, :2])
        system_data = results.metrics_data[results.metrics_data['metric_type'] == 'system']
        if not system_data.empty:
            ax1.plot(system_data['timestamp'], system_data['throughput_dl_mbps'], 
                    label='Downlink', linewidth=2)
            ax1.plot(system_data['timestamp'], system_data['throughput_ul_mbps'], 
                    label='Uplink', linewidth=2)
            ax1.set_title('System Throughput Over Time', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # Connection rate over time
        ax2 = fig.add_subplot(gs[0, 2:])
        if not system_data.empty:
            ax2.plot(system_data['timestamp'], system_data['connection_rate'], 
                    color='green', linewidth=2)
            ax2.set_title('UE Connection Rate Over Time', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Time (s)')
            ax2.set_ylabel('Connection Rate')
            ax2.grid(True, alpha=0.3)
        
        # UE throughput distribution
        ax3 = fig.add_subplot(gs[1, :2])
        if results.ue_statistics:
            dl_throughput = [stats['average_throughput_dl_mbps'] for stats in results.ue_statistics.values()]
            ul_throughput = [stats['average_throughput_ul_mbps'] for stats in results.ue_statistics.values()]
            
            ax3.hist(dl_throughput, bins=15, alpha=0.7, label='Downlink', edgecolor='black')
            ax3.hist(ul_throughput, bins=15, alpha=0.7, label='Uplink', edgecolor='black')
            ax3.set_title('UE Throughput Distribution', fontsize=14, fontweight='bold')
            ax3.set_xlabel('Average Throughput (Mbps)')
            ax3.set_ylabel('Number of UEs')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # gNB load comparison
        ax4 = fig.add_subplot(gs[1, 2:])
        if results.gnb_statistics:
            gnb_ids = list(results.gnb_statistics.keys())
            loads = [results.gnb_statistics[gid]['average_load'] for gid in gnb_ids]
            utilizations = [results.gnb_statistics[gid]['average_resource_utilization'] for gid in gnb_ids]
            
            x = np.arange(len(gnb_ids))
            width = 0.35
            
            ax4.bar(x - width/2, loads, width, label='Load', alpha=0.8)
            ax4.bar(x + width/2, utilizations, width, label='Resource Utilization', alpha=0.8)
            ax4.set_title('gNB Load and Resource Utilization', fontsize=14, fontweight='bold')
            ax4.set_xlabel('gNB ID')
            ax4.set_ylabel('Ratio')
            ax4.set_xticks(x)
            ax4.set_xticklabels([f'gNB {gid}' for gid in gnb_ids])
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        # Network topology
        ax5 = fig.add_subplot(gs[2, :])
        self._plot_network_topology_on_axis(results, ax5)
        
        plt.suptitle('5G NR Network Performance Overview', fontsize=16, fontweight='bold')
        plt.savefig(f"{output_dir}/network_performance_overview.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_qos_analysis(self, results: SimulationResults, output_dir: str):
        """Create QoS analysis plots."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        ue_data = results.metrics_data[results.metrics_data['metric_type'] == 'ue']
        
        if not ue_data.empty:
            # SINR distribution
            if 'sinr_db' in ue_data.columns:
                sinr_values = ue_data['sinr_db'].dropna()
                ax1.hist(sinr_values, bins=30, alpha=0.7, edgecolor='black')
                ax1.axvline(sinr_values.mean(), color='red', linestyle='--', 
                           label=f'Mean: {sinr_values.mean():.1f} dB')
                ax1.set_title('SINR Distribution')
                ax1.set_xlabel('SINR (dB)')
                ax1.set_ylabel('Frequency')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
            
            # RSRP distribution
            if 'best_rsrp_dbm' in ue_data.columns:
                rsrp_values = ue_data['best_rsrp_dbm'].dropna()
                ax2.hist(rsrp_values, bins=30, alpha=0.7, color='orange', edgecolor='black')
                ax2.axvline(rsrp_values.mean(), color='red', linestyle='--',
                           label=f'Mean: {rsrp_values.mean():.1f} dBm')
                ax2.set_title('RSRP Distribution')
                ax2.set_xlabel('RSRP (dBm)')
                ax2.set_ylabel('Frequency')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
            
            # Throughput vs SINR scatter plot
            if 'sinr_db' in ue_data.columns and 'throughput_dl_mbps' in ue_data.columns:
                ax3.scatter(ue_data['sinr_db'], ue_data['throughput_dl_mbps'], 
                           alpha=0.6, s=20)
                ax3.set_title('Throughput vs SINR')
                ax3.set_xlabel('SINR (dB)')
                ax3.set_ylabel('DL Throughput (Mbps)')
                ax3.grid(True, alpha=0.3)
            
            # Distance vs throughput
            if 'distance' in ue_data.columns and 'throughput_dl_mbps' in ue_data.columns:
                ax4.scatter(ue_data['distance'], ue_data['throughput_dl_mbps'], 
                           alpha=0.6, s=20, color='green')
                ax4.set_title('Throughput vs Distance')
                ax4.set_xlabel('Distance (m)')
                ax4.set_ylabel('DL Throughput (Mbps)')
                ax4.grid(True, alpha=0.3)
        
        plt.suptitle('QoS Performance Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/qos_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_mobility_analysis(self, results: SimulationResults, output_dir: str):
        """Create mobility analysis plots."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        if results.ue_statistics:
            # Speed distribution
            speeds = [stats['average_speed'] for stats in results.ue_statistics.values()]
            ax1.hist(speeds, bins=20, alpha=0.7, edgecolor='black')
            ax1.set_title('UE Speed Distribution')
            ax1.set_xlabel('Average Speed (m/s)')
            ax1.set_ylabel('Number of UEs')
            ax1.grid(True, alpha=0.3)
            
            # Distance traveled distribution
            distances = [stats['total_distance_traveled'] for stats in results.ue_statistics.values()]
            ax2.hist(distances, bins=20, alpha=0.7, color='orange', edgecolor='black')
            ax2.set_title('Total Distance Traveled Distribution')
            ax2.set_xlabel('Distance (m)')
            ax2.set_ylabel('Number of UEs')
            ax2.grid(True, alpha=0.3)
            
            # Speed vs throughput correlation
            dl_throughput = [stats['average_throughput_dl_mbps'] for stats in results.ue_statistics.values()]
            ax3.scatter(speeds, dl_throughput, alpha=0.7, s=50)
            ax3.set_title('Speed vs Throughput Correlation')
            ax3.set_xlabel('Average Speed (m/s)')
            ax3.set_ylabel('Average DL Throughput (Mbps)')
            ax3.grid(True, alpha=0.3)
            
            # Handovers vs speed
            handovers = [stats['handover_count'] for stats in results.ue_statistics.values()]
            ax4.scatter(speeds, handovers, alpha=0.7, s=50, color='red')
            ax4.set_title('Handovers vs Speed')
            ax4.set_xlabel('Average Speed (m/s)')
            ax4.set_ylabel('Number of Handovers')
            ax4.grid(True, alpha=0.3)
        
        plt.suptitle('Mobility Performance Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/mobility_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_handover_analysis(self, results: SimulationResults, output_dir: str):
        """Create handover analysis plots."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        ho_stats = results.handover_statistics
        
        if ho_stats:
            # Handover success rate
            total_attempts = ho_stats.get('total_attempts', 0)
            successful = ho_stats.get('successful_handovers', 0)
            failed = ho_stats.get('failed_handovers', 0)
            
            if total_attempts > 0:
                labels = ['Successful', 'Failed']
                sizes = [successful, failed]
                colors = ['lightgreen', 'lightcoral']
                
                ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax1.set_title(f'Handover Success Rate\n(Total: {total_attempts})')
            
            # Handover timing statistics
            avg_duration = ho_stats.get('average_handover_duration', 0)
            avg_interruption = ho_stats.get('average_interruption_time', 0)
            
            metrics = ['Avg Duration', 'Avg Interruption']
            values = [avg_duration, avg_interruption]
            
            ax2.bar(metrics, values, color=['skyblue', 'lightcoral'], alpha=0.8)
            ax2.set_title('Handover Timing Metrics')
            ax2.set_ylabel('Time (ms)')
            ax2.grid(True, alpha=0.3)
        
        # UE handover distribution
        if results.ue_statistics:
            handover_counts = [stats['handover_count'] for stats in results.ue_statistics.values()]
            ax3.hist(handover_counts, bins=max(1, max(handover_counts)+1), 
                    alpha=0.7, edgecolor='black')
            ax3.set_title('Handover Count Distribution per UE')
            ax3.set_xlabel('Number of Handovers')
            ax3.set_ylabel('Number of UEs')
            ax3.grid(True, alpha=0.3)
        
        # gNB handover traffic
        if results.gnb_statistics:
            gnb_ids = list(results.gnb_statistics.keys())
            handovers_in = [results.gnb_statistics[gid]['total_handovers_in'] for gid in gnb_ids]
            handovers_out = [results.gnb_statistics[gid]['total_handovers_out'] for gid in gnb_ids]
            
            x = np.arange(len(gnb_ids))
            width = 0.35
            
            ax4.bar(x - width/2, handovers_in, width, label='Handovers In', alpha=0.8)
            ax4.bar(x + width/2, handovers_out, width, label='Handovers Out', alpha=0.8)
            ax4.set_title('gNB Handover Traffic')
            ax4.set_xlabel('gNB ID')
            ax4.set_ylabel('Number of Handovers')
            ax4.set_xticks(x)
            ax4.set_xticklabels([f'gNB {gid}' for gid in gnb_ids])
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.suptitle('Handover Performance Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/handover_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_coverage_heatmap(self, results: SimulationResults, output_dir: str):
        """Create coverage heatmap based on RSRP measurements."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        ue_data = results.metrics_data[results.metrics_data['metric_type'] == 'ue']
        
        if not ue_data.empty and 'position_x' in ue_data.columns:
            # Get position bounds
            x_min, x_max = ue_data['position_x'].min(), ue_data['position_x'].max()
            y_min, y_max = ue_data['position_y'].min(), ue_data['position_y'].max()
            
            # Expand bounds slightly
            x_range = x_max - x_min
            y_range = y_max - y_min
            margin = 0.1
            
            x_min -= margin * x_range
            x_max += margin * x_range
            y_min -= margin * y_range
            y_max += margin * y_range
            
            # Create grid for interpolation
            grid_size = 50
            x_grid = np.linspace(x_min, x_max, grid_size)
            y_grid = np.linspace(y_min, y_max, grid_size)
            X, Y = np.meshgrid(x_grid, y_grid)
            
            # RSRP heatmap
            if 'best_rsrp_dbm' in ue_data.columns:
                rsrp_data = ue_data[['position_x', 'position_y', 'best_rsrp_dbm']].dropna()
                if not rsrp_data.empty:
                    from scipy.interpolate import griddata
                    points = rsrp_data[['position_x', 'position_y']].values
                    values = rsrp_data['best_rsrp_dbm'].values
                    
                    Z_rsrp = griddata(points, values, (X, Y), method='cubic', fill_value=values.min())
                    
                    im1 = ax1.contourf(X, Y, Z_rsrp, levels=20, cmap='RdYlBu_r')
                    ax1.set_title('RSRP Coverage Heatmap')
                    ax1.set_xlabel('X Position (m)')
                    ax1.set_ylabel('Y Position (m)')
                    plt.colorbar(im1, ax=ax1, label='RSRP (dBm)')
            
            # SINR heatmap
            if 'sinr_db' in ue_data.columns:
                sinr_data = ue_data[['position_x', 'position_y', 'sinr_db']].dropna()
                if not sinr_data.empty:
                    from scipy.interpolate import griddata
                    points = sinr_data[['position_x', 'position_y']].values
                    values = sinr_data['sinr_db'].values
                    
                    Z_sinr = griddata(points, values, (X, Y), method='cubic', fill_value=values.min())
                    
                    im2 = ax2.contourf(X, Y, Z_sinr, levels=20, cmap='viridis')
                    ax2.set_title('SINR Coverage Heatmap')
                    ax2.set_xlabel('X Position (m)')
                    ax2.set_ylabel('Y Position (m)')
                    plt.colorbar(im2, ax=ax2, label='SINR (dB)')
            
            # Throughput heatmap
            if 'throughput_dl_mbps' in ue_data.columns:
                thr_data = ue_data[['position_x', 'position_y', 'throughput_dl_mbps']].dropna()
                if not thr_data.empty:
                    from scipy.interpolate import griddata
                    points = thr_data[['position_x', 'position_y']].values
                    values = thr_data['throughput_dl_mbps'].values
                    
                    Z_thr = griddata(points, values, (X, Y), method='cubic', fill_value=values.min())
                    
                    im3 = ax3.contourf(X, Y, Z_thr, levels=20, cmap='plasma')
                    ax3.set_title('Throughput Coverage Heatmap')
                    ax3.set_xlabel('X Position (m)')
                    ax3.set_ylabel('Y Position (m)')
                    plt.colorbar(im3, ax=ax3, label='DL Throughput (Mbps)')
            
            # Add gNB positions to all heatmaps
            if results.gnb_statistics:
                for ax in [ax1, ax2, ax3]:
                    for gnb_id, stats in results.gnb_statistics.items():
                        pos = stats['position']
                        ax.scatter(pos[0], pos[1], c='white', s=200, marker='^', 
                                 edgecolors='black', linewidth=2, zorder=10)
                        ax.annotate(f'gNB {gnb_id}', (pos[0], pos[1]), 
                                   xytext=(5, 5), textcoords='offset points',
                                   color='white', fontweight='bold', zorder=11)
        
        # Network topology
        self._plot_network_topology_on_axis(results, ax4)
        
        plt.suptitle('Coverage Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/coverage_heatmap.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_network_topology_on_axis(self, results: SimulationResults, ax):
        """Plot network topology on given axis."""
        # Plot gNBs
        if results.gnb_statistics:
            gnb_positions = [stats['position'] for stats in results.gnb_statistics.values()]
            gnb_x = [pos[0] for pos in gnb_positions]
            gnb_y = [pos[1] for pos in gnb_positions]
            
            ax.scatter(gnb_x, gnb_y, c='red', s=300, marker='^', 
                      label='gNBs', edgecolors='black', linewidth=2)
            
            # Add gNB IDs
            for i, (x, y) in enumerate(gnb_positions):
                ax.annotate(f'gNB {i}', (x, y), xytext=(10, 10), 
                           textcoords='offset points', fontweight='bold')
        
        # Plot UE final positions
        ue_data = results.metrics_data[results.metrics_data['metric_type'] == 'ue']
        if not ue_data.empty:
            # Get last positions for each UE
            last_positions = ue_data.groupby('entity_id').tail(1)
            
            ax.scatter(last_positions['position_x'], last_positions['position_y'], 
                      c='blue', s=50, alpha=0.7, label='UEs')
        
        ax.set_title('Network Topology', fontweight='bold')
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
    
    def create_animated_simulation(self, results: SimulationResults, output_file: str = "simulation.gif"):
        """Create animated visualization of the simulation."""
        ue_data = results.metrics_data[results.metrics_data['metric_type'] == 'ue']
        
        if ue_data.empty:
            print("No UE data available for animation")
            return
        
        # Setup figure
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Get bounds
        x_min, x_max = ue_data['position_x'].min(), ue_data['position_x'].max()
        y_min, y_max = ue_data['position_y'].min(), ue_data['position_y'].max()
        
        # Expand bounds
        margin = 0.1 * max(x_max - x_min, y_max - y_min)
        ax.set_xlim(x_min - margin, x_max + margin)
        ax.set_ylim(y_min - margin, y_max + margin)
        
        # Plot gNBs (static)
        if results.gnb_statistics:
            for gnb_id, stats in results.gnb_statistics.items():
                pos = stats['position']
                ax.scatter(pos[0], pos[1], c='red', s=300, marker='^', 
                          edgecolors='black', linewidth=2, zorder=10)
                ax.annotate(f'gNB {gnb_id}', (pos[0], pos[1]), 
                           xytext=(10, 10), textcoords='offset points',
                           fontweight='bold', zorder=11)
        
        # Initialize UE scatter plot
        scat = ax.scatter([], [], c='blue', s=50, alpha=0.7)
        time_text = ax.text(0.02, 0.98, '', transform=ax.transAxes, 
                           verticalalignment='top', fontsize=12, 
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.set_title('5G NR Network Simulation Animation')
        ax.grid(True, alpha=0.3)
        
        # Animation function
        def animate(frame):
            timestamp = ue_data['timestamp'].unique()[frame]
            frame_data = ue_data[ue_data['timestamp'] == timestamp]
            
            if not frame_data.empty:
                positions = np.column_stack((frame_data['position_x'], frame_data['position_y']))
                scat.set_offsets(positions)
                
                # Color by throughput if available
                if 'throughput_dl_mbps' in frame_data.columns:
                    colors = frame_data['throughput_dl_mbps']
                    scat.set_array(colors)
                
            time_text.set_text(f'Time: {timestamp:.1f}s')
            return scat, time_text
        
        # Create animation
        frames = len(ue_data['timestamp'].unique())
        anim = animation.FuncAnimation(fig, animate, frames=frames, 
                                     interval=100, blit=True, repeat=True)
        
        # Save animation
        try:
            anim.save(output_file, writer='pillow', fps=10)
            print(f"Animation saved as {output_file}")
        except Exception as e:
            print(f"Error saving animation: {e}")
        
        plt.close()
    
    def export_summary_report(self, results: SimulationResults, output_file: str):
        """Export a summary report with key metrics."""
        report = []
        report.append("5G NR SIMULATION SUMMARY REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Simulation configuration
        if results.config:
            report.append("SIMULATION CONFIGURATION:")
            report.append(f"  Simulation Time: {results.config.simulation_time}s")
            report.append(f"  Time Step: {results.config.time_step}s")
            report.append(f"  Number of gNBs: {results.config.num_gnbs}")
            report.append(f"  Number of UEs: {results.config.num_ues}")
            report.append(f"  Frequency: {results.config.frequency} MHz")
            report.append(f"  Bandwidth: {results.config.bandwidth} MHz")
            report.append("")
        
        # Summary statistics
        if results.summary_statistics:
            report.append("PERFORMANCE SUMMARY:")
            stats = results.summary_statistics
            report.append(f"  Average DL Throughput: {stats.get('average_throughput_dl_mbps', 0):.2f} Mbps")
            report.append(f"  Average UL Throughput: {stats.get('average_throughput_ul_mbps', 0):.2f} Mbps")
            report.append(f"  Peak DL Throughput: {stats.get('peak_throughput_dl_mbps', 0):.2f} Mbps")
            report.append(f"  Peak UL Throughput: {stats.get('peak_throughput_ul_mbps', 0):.2f} Mbps")
            report.append(f"  Average Connection Rate: {stats.get('average_connection_rate', 0):.3f}")
            report.append(f"  Average Resource Utilization: {stats.get('average_resource_utilization', 0):.3f}")
            report.append("")
        
        # Handover statistics
        if results.handover_statistics:
            report.append("HANDOVER STATISTICS:")
            ho_stats = results.handover_statistics
            report.append(f"  Total Attempts: {ho_stats.get('total_attempts', 0)}")
            report.append(f"  Successful: {ho_stats.get('successful_handovers', 0)}")
            report.append(f"  Failed: {ho_stats.get('failed_handovers', 0)}")
            report.append(f"  Success Rate: {ho_stats.get('success_rate', 0):.3f}")
            report.append(f"  Average Duration: {ho_stats.get('average_handover_duration', 0):.2f} ms")
            report.append("")
        
        # Execution information
        report.append("EXECUTION INFORMATION:")
        report.append(f"  Execution Time: {results.execution_time:.2f} seconds")
        report.append(f"  Total Measurements: {results.summary_statistics.get('total_measurements', 0)}")
        
        # Write report to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(report))
        
        print(f"Summary report saved to {output_file}")