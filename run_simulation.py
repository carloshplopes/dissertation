#!/usr/bin/env python3
"""
Main simulation runner for 5G NR QoS and Mobility Simulation Framework.

This script runs 5G NR simulations with configurable scenarios and generates
comprehensive results and visualizations.

Usage:
    python run_simulation.py --config scenarios/basic_scenario.json
    python run_simulation.py --scenario mobility --output results/my_results.json
    python run_simulation.py --help
"""

import argparse
import sys
import os
from pathlib import Path
import traceback

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.simulation.engine import SimulationEngine
from src.utils.config import ConfigManager
from src.utils.visualization import NetworkVisualizer
from src.simulation.metrics import MetricsCollector


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='5G NR QoS and Mobility Simulation Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config scenarios/basic_scenario.json
  %(prog)s --scenario mobility
  %(prog)s --scenario video_streaming --output results/video_results.json
  %(prog)s --create-scenario basic --config-output scenarios/my_scenario.json
        """
    )
    
    # Main execution modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--config', '-c', type=str,
                      help='Configuration file path (JSON or YAML)')
    group.add_argument('--scenario', '-s', type=str,
                      choices=['basic', 'mobility', 'video_streaming'],
                      help='Use predefined scenario')
    group.add_argument('--create-scenario', type=str,
                      choices=['basic', 'mobility', 'video_streaming'],
                      help='Create a new scenario configuration file')
    
    # Optional parameters
    parser.add_argument('--output', '-o', type=str,
                       help='Output file for results (overrides config)')
    parser.add_argument('--results-dir', type=str, default='results',
                       help='Directory for results and visualizations')
    parser.add_argument('--config-output', type=str,
                       help='Output path for created scenario (used with --create-scenario)')
    parser.add_argument('--no-visualization', action='store_true',
                       help='Disable visualization generation')
    parser.add_argument('--animation', action='store_true',
                       help='Create animated visualization (may take longer)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    return parser.parse_args()


def setup_results_directory(results_dir: str):
    """Create results directory if it doesn't exist."""
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    print(f"Results will be saved to: {results_dir}")


def run_simulation_from_config(config_file: str, args):
    """Run simulation from configuration file."""
    print(f"Loading configuration from: {config_file}")
    
    try:
        config = ConfigManager.load_config(config_file)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return False
    
    # Override output file if specified
    if args.output:
        config.output_file = args.output
    
    # Override visualization setting
    if args.no_visualization:
        config.enable_visualization = False
    
    return run_simulation_with_config(config, args)


def run_simulation_from_scenario(scenario: str, args):
    """Run simulation from predefined scenario."""
    print(f"Using predefined scenario: {scenario}")
    
    # Create temporary config file
    temp_config_file = f"/tmp/{scenario}_scenario.json"
    ConfigManager.create_default_config(temp_config_file, scenario)
    
    # Load and modify config
    config = ConfigManager.load_config(temp_config_file)
    
    # Override settings from args
    if args.output:
        config.output_file = args.output
    if args.no_visualization:
        config.enable_visualization = False
    
    # Clean up temp file
    os.remove(temp_config_file)
    
    return run_simulation_with_config(config, args)


def run_simulation_with_config(config, args):
    """Run simulation with given configuration."""
    print("\n" + "="*60)
    print("5G NR QoS AND MOBILITY SIMULATION FRAMEWORK")
    print("="*60)
    
    if args.verbose:
        print(f"Configuration:")
        print(f"  Simulation time: {config.simulation_time}s")
        print(f"  Time step: {config.time_step}s")
        print(f"  gNBs: {config.num_gnbs}")
        print(f"  UEs: {config.num_ues}")
        print(f"  Frequency: {config.frequency} MHz")
        print(f"  Bandwidth: {config.bandwidth} MHz")
        print(f"  Propagation model: {config.propagation_model}")
        print()
    
    try:
        # Create simulation engine
        engine = SimulationEngine(config)
        
        # Run simulation
        results = engine.run_simulation()
        
        print("\n" + "-"*50)
        print("SIMULATION COMPLETED SUCCESSFULLY")
        print("-"*50)
        
        # Print summary statistics
        if results.summary_statistics:
            stats = results.summary_statistics
            print(f"Average DL Throughput: {stats.get('average_throughput_dl_mbps', 0):.2f} Mbps")
            print(f"Average UL Throughput: {stats.get('average_throughput_ul_mbps', 0):.2f} Mbps")
            print(f"Peak DL Throughput: {stats.get('peak_throughput_dl_mbps', 0):.2f} Mbps")
            print(f"Average Connection Rate: {stats.get('average_connection_rate', 0):.3f}")
            
            if results.handover_statistics:
                ho_stats = results.handover_statistics
                print(f"Handovers: {ho_stats.get('total_attempts', 0)} attempts, "
                      f"{ho_stats.get('success_rate', 0):.3f} success rate")
        
        print(f"Execution time: {results.execution_time:.2f} seconds")
        
        # Save results
        if config.output_file:
            output_path = os.path.join(args.results_dir, os.path.basename(config.output_file))
            MetricsCollector().export_results(results, output_path)
            print(f"Results saved to: {output_path}")
        
        # Generate visualizations
        if config.enable_visualization and not args.no_visualization:
            print("\nGenerating visualizations...")
            visualizer = NetworkVisualizer()
            
            try:
                visualizer.create_comprehensive_report(results, args.results_dir)
                
                # Create animation if requested
                if args.animation:
                    print("Creating animated visualization...")
                    animation_file = os.path.join(args.results_dir, "simulation_animation.gif")
                    visualizer.create_animated_simulation(results, animation_file)
                
                # Create summary report
                summary_file = os.path.join(args.results_dir, "simulation_summary.txt")
                visualizer.export_summary_report(results, summary_file)
                
                print(f"Visualizations created in: {args.results_dir}")
                
            except Exception as e:
                print(f"Warning: Error generating visualizations: {e}")
                if args.verbose:
                    traceback.print_exc()
        
        print("\n" + "="*60)
        return True
        
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        return False
    except Exception as e:
        print(f"Error running simulation: {e}")
        if args.verbose:
            traceback.print_exc()
        return False


def create_scenario_config(scenario: str, args):
    """Create a new scenario configuration file."""
    output_file = args.config_output or f"scenarios/{scenario}_scenario_new.json"
    
    print(f"Creating {scenario} scenario configuration...")
    
    try:
        ConfigManager.create_default_config(output_file, scenario)
        print(f"Configuration created: {output_file}")
        print("You can now modify this file and run it with:")
        print(f"  python run_simulation.py --config {output_file}")
        return True
    except Exception as e:
        print(f"Error creating configuration: {e}")
        return False


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Setup results directory
    setup_results_directory(args.results_dir)
    
    # Execute based on arguments
    if args.create_scenario:
        success = create_scenario_config(args.create_scenario, args)
    elif args.config:
        success = run_simulation_from_config(args.config, args)
    elif args.scenario:
        success = run_simulation_from_scenario(args.scenario, args)
    else:
        print("Error: No execution mode specified")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()