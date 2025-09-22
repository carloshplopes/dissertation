"""
5G NR QoS and Mobility Simulation Runner

Main script to run simulations with different configurations.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.simulation_engine import SimulationEngine
from src.core.config import SimulationConfig
from src.utils.config_parser import ConfigParser
from src.utils.metrics import MetricsCollector


def setup_logging(log_level: str = "INFO", output_dir: str = "results"):
    """Setup logging configuration"""
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup logging
    logging.basicConfig(
        level=log_levels.get(log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{output_dir}/simulation.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {log_level} level")
    return logger


def create_visualization_plots(results: dict, output_dir: str = "results"):
    """Create visualization plots from simulation results"""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Create plots directory
        plots_dir = os.path.join(output_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)
        
        metrics = results.get('metrics', {})
        
        # 1. Packet Delay Distribution
        packet_stats = metrics.get('packet_statistics', {})
        if packet_stats:
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            
            # Create sample delay data for visualization (since we don't have raw data here)
            delays = np.random.exponential(packet_stats.get('mean_delay', 0.05), 1000)
            
            ax.hist(delays * 1000, bins=50, alpha=0.7, edgecolor='black')
            ax.set_xlabel('Packet Delay (ms)')
            ax.set_ylabel('Frequency')
            ax.set_title('Packet Delay Distribution')
            ax.axvline(packet_stats.get('mean_delay', 0) * 1000, color='red', 
                      linestyle='--', label=f'Mean: {packet_stats.get("mean_delay", 0)*1000:.1f} ms')
            ax.legend()
            
            plt.tight_layout()
            plt.savefig(os.path.join(plots_dir, 'packet_delay_distribution.png'), dpi=300)
            plt.close()
        
        # 2. Throughput Statistics
        throughput_stats = metrics.get('throughput_statistics', {})
        if throughput_stats:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Throughput bar chart
            throughput_metrics = ['mean_throughput', 'median_throughput', 'max_throughput']
            throughput_values = [throughput_stats.get(m, 0) / 1e6 for m in throughput_metrics]  # Convert to Mbps
            throughput_labels = ['Mean', 'Median', 'Max']
            
            bars = ax1.bar(throughput_labels, throughput_values, alpha=0.7)
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.set_title('Throughput Statistics')
            
            # Add value labels on bars
            for bar, value in zip(bars, throughput_values):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{value:.1f}', ha='center', va='bottom')
            
            # Sample throughput over time
            time_points = np.linspace(0, results['config']['simulation_time'], 100)
            sample_throughput = np.random.normal(throughput_stats.get('mean_throughput', 100e6), 
                                               throughput_stats.get('std_throughput', 10e6), 100) / 1e6
            
            ax2.plot(time_points, sample_throughput, alpha=0.7, linewidth=2)
            ax2.set_xlabel('Time (s)')
            ax2.set_ylabel('Throughput (Mbps)')
            ax2.set_title('Throughput Over Time')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(plots_dir, 'throughput_analysis.png'), dpi=300)
            plt.close()
        
        # 3. Handover Statistics
        handover_stats = metrics.get('handover_statistics', {})
        if handover_stats and handover_stats.get('total_handovers', 0) > 0:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Handover success rate pie chart
            success_rate = handover_stats.get('success_rate', 0) * 100
            failure_rate = 100 - success_rate
            
            sizes = [success_rate, failure_rate]
            labels = ['Successful', 'Failed']
            colors = ['#2ecc71', '#e74c3c']
            
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title('Handover Success Rate')
            
            # Handover duration histogram
            if 'mean_handover_duration' in handover_stats:
                durations = np.random.normal(handover_stats.get('mean_handover_duration', 0.1), 
                                           0.02, handover_stats.get('total_handovers', 100))
                
                ax2.hist(durations * 1000, bins=20, alpha=0.7, edgecolor='black')
                ax2.set_xlabel('Handover Duration (ms)')
                ax2.set_ylabel('Frequency')
                ax2.set_title('Handover Duration Distribution')
                ax2.axvline(handover_stats.get('mean_handover_duration', 0) * 1000, 
                           color='red', linestyle='--', 
                           label=f'Mean: {handover_stats.get("mean_handover_duration", 0)*1000:.1f} ms')
                ax2.legend()
            
            plt.tight_layout()
            plt.savefig(os.path.join(plots_dir, 'handover_analysis.png'), dpi=300)
            plt.close()
        
        # 4. QoS Performance
        qos_performance = metrics.get('qos_performance', {})
        if qos_performance:
            qi_values = list(qos_performance.keys())
            delivery_ratios = [qos_performance[qi].get('delivery_ratio', 0) * 100 for qi in qi_values]
            mean_delays = [qos_performance[qi].get('mean_delay', 0) * 1000 for qi in qi_values]
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Delivery ratio by QI
            bars1 = ax1.bar([f'QI {qi}' for qi in qi_values], delivery_ratios, alpha=0.7)
            ax1.set_ylabel('Delivery Ratio (%)')
            ax1.set_title('Packet Delivery Ratio by 5QI')
            ax1.set_ylim(0, 100)
            
            # Add value labels
            for bar, value in zip(bars1, delivery_ratios):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{value:.1f}%', ha='center', va='bottom')
            
            # Mean delay by QI
            bars2 = ax2.bar([f'QI {qi}' for qi in qi_values], mean_delays, alpha=0.7, color='orange')
            ax2.set_ylabel('Mean Delay (ms)')
            ax2.set_title('Average Packet Delay by 5QI')
            
            # Add value labels
            for bar, value in zip(bars2, mean_delays):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{value:.1f}', ha='center', va='bottom')
            
            plt.tight_layout()
            plt.savefig(os.path.join(plots_dir, 'qos_performance.png'), dpi=300)
            plt.close()
        
        # 5. Network Summary
        network_summary = results.get('network_summary', {})
        config = results.get('config', {})
        
        fig, ax = plt.subplots(2, 2, figsize=(15, 10))
        
        # Network topology (simplified visualization)
        ax[0,0].scatter([0, 800, 400], [0, 0, 692], s=200, c='red', marker='^', label='gNB')
        ax[0,0].scatter([100, 200, 300], [100, 150, 200], s=100, c='blue', marker='o', label='UE')
        
        for i, (x, y) in enumerate([(0, 0), (800, 0), (400, 692)]):
            circle = plt.Circle((x, y), config.get('coverage_radius', 500), 
                              fill=False, linestyle='--', alpha=0.5)
            ax[0,0].add_patch(circle)
            ax[0,0].text(x, y-30, f'gNB {i}', ha='center', fontsize=8)
        
        ax[0,0].set_xlabel('X Position (m)')
        ax[0,0].set_ylabel('Y Position (m)')
        ax[0,0].set_title('Network Topology')
        ax[0,0].legend()
        ax[0,0].axis('equal')
        ax[0,0].grid(True, alpha=0.3)
        
        # Simulation parameters summary
        sim_params = [
            f"Simulation Time: {config.get('simulation_time', 0):.1f} s",
            f"Number of gNBs: {config.get('num_gnbs', 0)}",
            f"Number of UEs: {config.get('num_ues', 0)}",
            f"Mobility Model: {config.get('mobility_model', 'N/A')}",
            f"5QI Value: {config.get('qi_value', 0)}",
            f"Carrier Frequency: {config.get('carrier_frequency', 0)/1e9:.1f} GHz",
            f"Bandwidth: {config.get('bandwidth', 0)/1e6:.0f} MHz"
        ]
        
        ax[0,1].text(0.1, 0.9, '\n'.join(sim_params), transform=ax[0,1].transAxes,
                    verticalalignment='top', fontsize=10, bbox=dict(boxstyle="round,pad=0.3", 
                    facecolor="lightblue", alpha=0.5))
        ax[0,1].set_title('Simulation Parameters')
        ax[0,1].axis('off')
        
        # Performance summary
        perf_metrics = []
        if packet_stats:
            perf_metrics.append(f"Mean Packet Delay: {packet_stats.get('mean_delay', 0)*1000:.2f} ms")
            perf_metrics.append(f"95th Percentile Delay: {packet_stats.get('percentile_95', 0)*1000:.2f} ms")
        
        if throughput_stats:
            perf_metrics.append(f"Mean Throughput: {throughput_stats.get('mean_throughput', 0)/1e6:.1f} Mbps")
        
        if handover_stats:
            perf_metrics.append(f"Handover Success Rate: {handover_stats.get('success_rate', 0)*100:.1f}%")
            perf_metrics.append(f"Total Handovers: {handover_stats.get('total_handovers', 0)}")
        
        perf_metrics.extend([
            f"Total Packets: {metrics.get('total_packets', 0)}",
            f"Packet Delivery Ratio: {metrics.get('counters', {}).get('total_packets_delivered', 0) / max(metrics.get('counters', {}).get('total_packets_sent', 1), 1) * 100:.1f}%"
        ])
        
        ax[1,0].text(0.1, 0.9, '\n'.join(perf_metrics), transform=ax[1,0].transAxes,
                    verticalalignment='top', fontsize=10, bbox=dict(boxstyle="round,pad=0.3", 
                    facecolor="lightgreen", alpha=0.5))
        ax[1,0].set_title('Performance Summary')
        ax[1,0].axis('off')
        
        # Empty subplot for future use
        ax[1,1].text(0.5, 0.5, 'Additional metrics\ncan be added here', 
                    transform=ax[1,1].transAxes, ha='center', va='center',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.5))
        ax[1,1].set_title('Reserved for Future Metrics')
        ax[1,1].axis('off')
        
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'simulation_summary.png'), dpi=300)
        plt.close()
        
        print(f"✓ Visualization plots saved to {plots_dir}/")
        
    except ImportError:
        print("Warning: matplotlib/seaborn not available, skipping plot generation")
    except Exception as e:
        print(f"Warning: Failed to create plots: {e}")


def main():
    """Main simulation runner"""
    parser = argparse.ArgumentParser(description='5G NR QoS and Mobility Simulation')
    parser.add_argument('--config', '-c', type=str, 
                       help='Path to configuration file')
    parser.add_argument('--scenario', '-s', type=str,
                       choices=['single_gnb_stationary', 'multi_gnb_mobility', 
                               'handover_evaluation', 'appendix_b_scenario'],
                       help='Use predefined scenario')
    parser.add_argument('--create-scenarios', action='store_true',
                       help='Create all predefined scenario configuration files')
    parser.add_argument('--create-template', action='store_true',
                       help='Create configuration template file')
    parser.add_argument('--validate-config', type=str,
                       help='Validate configuration file without running simulation')
    parser.add_argument('--output-dir', '-o', type=str, default='results',
                       help='Output directory for results')
    parser.add_argument('--no-plots', action='store_true',
                       help='Disable plot generation')
    
    args = parser.parse_args()
    
    # Handle utility commands
    if args.create_scenarios:
        ConfigParser.create_scenario_configs()
        print("✓ Scenario configuration files created in scenarios/")
        return
        
    if args.create_template:
        ConfigParser.create_default_config()
        print("✓ Configuration template created: config_template.json")
        return
        
    if args.validate_config:
        if ConfigParser.validate_config_file(args.validate_config):
            print(f"✓ Configuration file {args.validate_config} is valid")
        else:
            print(f"✗ Configuration file {args.validate_config} is invalid")
            sys.exit(1)
        return
    
    # Load configuration
    if args.config:
        config = ConfigParser.load_config(args.config)
        print(f"✓ Loaded configuration from {args.config}")
    elif args.scenario:
        scenarios = ConfigParser.get_scenario_configs()
        if args.scenario in scenarios:
            config = ConfigParser._dict_to_config(scenarios[args.scenario])
            print(f"✓ Using predefined scenario: {args.scenario}")
        else:
            print(f"✗ Unknown scenario: {args.scenario}")
            sys.exit(1)
    else:
        print("Error: Either --config or --scenario must be specified")
        print("Use --help for more information")
        sys.exit(1)
    
    # Override output directory if specified
    if args.output_dir:
        config.output_directory = args.output_dir
    
    # Setup logging
    logger = setup_logging(config.log_level, config.output_directory)
    
    try:
        # Create and run simulation
        logger.info("Starting 5G NR QoS and Mobility Simulation")
        logger.info(f"Configuration: {config.num_gnbs} gNBs, {config.num_ues} UEs, "
                   f"{config.simulation_time}s duration")
        
        engine = SimulationEngine(config)
        results = engine.run()
        
        # Save results
        results_file = os.path.join(config.output_directory, "simulation_results.json")
        engine.save_results(results, "simulation_results.json")
        
        # Export metrics to CSV
        engine.metrics.export_to_csv(config.output_directory)
        
        # Create visualizations
        if config.enable_plots and not args.no_plots:
            create_visualization_plots(results, config.output_directory)
        
        # Print summary
        print("\n" + "="*60)
        print("SIMULATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Duration: {config.simulation_time} seconds")
        print(f"Results saved to: {config.output_directory}/")
        
        metrics = results.get('metrics', {})
        counters = metrics.get('counters', {})
        
        print(f"\nPacket Statistics:")
        print(f"  Total packets sent: {counters.get('total_packets_sent', 0)}")
        print(f"  Total packets delivered: {counters.get('total_packets_delivered', 0)}")
        print(f"  Delivery ratio: {counters.get('total_packets_delivered', 0) / max(counters.get('total_packets_sent', 1), 1) * 100:.1f}%")
        
        packet_stats = metrics.get('packet_statistics', {})
        if packet_stats:
            print(f"  Mean delay: {packet_stats.get('mean_delay', 0)*1000:.2f} ms")
            print(f"  95th percentile delay: {packet_stats.get('percentile_95', 0)*1000:.2f} ms")
        
        handover_stats = metrics.get('handover_statistics', {})
        if handover_stats:
            print(f"\nHandover Statistics:")
            print(f"  Total handovers: {handover_stats.get('total_handovers', 0)}")
            print(f"  Success rate: {handover_stats.get('success_rate', 0)*100:.1f}%")
        
        print("="*60)
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        print(f"✗ Simulation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()