"""
Main simulation engine for 5G NR QoS and mobility simulations.

This module coordinates all simulation components and manages the simulation loop.
"""

import time
from typing import Dict, List, Optional, Any
import numpy as np
from dataclasses import dataclass

from ..mobility.user_equipment import UserEquipment, Position, MobilityModel
from ..mobility.handover import HandoverManager
from ..network.gnb import GNodeB
from ..network.channel import ChannelModel, PropagationModel
from .metrics import MetricsCollector


@dataclass
class SimulationConfig:
    """Configuration parameters for the simulation."""
    simulation_time: float = 60.0  # seconds
    time_step: float = 0.1  # seconds
    
    # Network configuration
    num_gnbs: int = 3
    gnb_positions: Optional[List[tuple]] = None
    gnb_tx_power: float = 46.0  # dBm
    frequency: float = 3500.0  # MHz
    bandwidth: float = 100.0  # MHz
    
    # UE configuration
    num_ues: int = 10
    ue_positions: Optional[List[tuple]] = None
    mobility_models: Optional[List[str]] = None
    mobility_params: Optional[List[Dict]] = None
    
    # Channel configuration
    propagation_model: str = "urban_macro"
    enable_shadowing: bool = True
    enable_fast_fading: bool = True
    
    # QoS configuration
    default_qci: int = 9
    qos_flows: Optional[List[Dict]] = None
    
    # Output configuration
    output_file: Optional[str] = None
    enable_visualization: bool = False


class SimulationEngine:
    """Main simulation engine for 5G NR simulations."""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.current_time = 0.0
        
        # Initialize components
        self.gnbs: Dict[int, GNodeB] = {}
        self.ues: Dict[int, UserEquipment] = {}
        self.channel_model = ChannelModel(
            PropagationModel(config.propagation_model),
            config.frequency
        )
        self.handover_manager = HandoverManager()
        self.metrics_collector = MetricsCollector()
        
        # Initialize network
        self._initialize_gnbs()
        self._initialize_ues()
        self._initial_ue_attachment()
        
        # Simulation state
        self.running = False
        self.time_steps = int(config.simulation_time / config.time_step)
        self.current_step = 0
    
    def _initialize_gnbs(self):
        """Initialize gNBs based on configuration."""
        if self.config.gnb_positions:
            positions = self.config.gnb_positions
        else:
            # Default positions for multi-gNB scenario
            if self.config.num_gnbs == 1:
                positions = [(0, 0)]
            elif self.config.num_gnbs == 2:
                positions = [(-500, 0), (500, 0)]
            elif self.config.num_gnbs == 3:
                positions = [(-500, 0), (500, 0), (0, 866)]  # Triangular layout
            else:
                # Random positions for more gNBs
                positions = [(np.random.uniform(-1000, 1000), np.random.uniform(-1000, 1000)) 
                           for _ in range(self.config.num_gnbs)]
        
        for i, (x, y) in enumerate(positions[:self.config.num_gnbs]):
            gnb = GNodeB(
                gnb_id=i,
                position=Position(x, y),
                tx_power=self.config.gnb_tx_power,
                frequency=self.config.frequency,
                bandwidth=self.config.bandwidth
            )
            self.gnbs[i] = gnb
    
    def _initialize_ues(self):
        """Initialize UEs based on configuration."""
        if self.config.ue_positions:
            positions = self.config.ue_positions[:self.config.num_ues]
        else:
            # Random positions within coverage area
            positions = [(np.random.uniform(-1500, 1500), np.random.uniform(-1500, 1500)) 
                        for _ in range(self.config.num_ues)]
        
        # Default mobility models
        if self.config.mobility_models:
            mobility_models = self.config.mobility_models[:self.config.num_ues]
        else:
            mobility_models = ["stationary"] * (self.config.num_ues // 2) + \
                            ["random_walk"] * (self.config.num_ues - self.config.num_ues // 2)
        
        # Default mobility parameters
        if self.config.mobility_params:
            mobility_params = self.config.mobility_params[:self.config.num_ues]
        else:
            mobility_params = [{"max_speed": 5.0, "direction_change_prob": 0.1} 
                             for _ in range(self.config.num_ues)]
        
        for i in range(self.config.num_ues):
            x, y = positions[i]
            model_str = mobility_models[i % len(mobility_models)]
            params = mobility_params[i % len(mobility_params)]
            
            mobility_model = MobilityModel(model_str)
            
            ue = UserEquipment(
                ue_id=i,
                initial_position=Position(x, y),
                mobility_model=mobility_model,
                **params
            )
            self.ues[i] = ue
    
    def _initial_ue_attachment(self):
        """Perform initial UE attachment to gNBs."""
        for ue_id, ue in self.ues.items():
            # Update RSRP measurements
            gnb_positions = {gnb_id: gnb.position for gnb_id, gnb in self.gnbs.items()}
            ue.update_rsrp_measurements(gnb_positions, self.config.gnb_tx_power)
            
            # Attach to best gNB
            best_gnb_id = ue.get_best_serving_gnb()
            if best_gnb_id is not None and best_gnb_id in self.gnbs:
                success = self.gnbs[best_gnb_id].add_ue(ue_id, self.config.default_qci)
                if success:
                    ue.connected_gnb_id = best_gnb_id
                    print(f"UE {ue_id} attached to gNB {best_gnb_id}")
    
    def _update_ue_mobility(self):
        """Update UE positions based on mobility models."""
        for ue in self.ues.values():
            ue.update_position(self.config.time_step)
    
    def _update_rsrp_measurements(self):
        """Update RSRP measurements for all UEs."""
        gnb_positions = {gnb_id: gnb.position for gnb_id, gnb in self.gnbs.items()}
        
        for ue in self.ues.values():
            ue.update_rsrp_measurements(gnb_positions, self.config.gnb_tx_power)
    
    def _process_handovers(self):
        """Process handover procedures."""
        # Check for handover triggers
        for ue_id, ue in self.ues.items():
            if ue.connected_gnb_id is None or ue.connected_gnb_id not in self.gnbs:
                continue
            
            # Evaluate handover conditions
            target_result = self.handover_manager.evaluate_handover_conditions(
                ue_id, ue.rsrp_measurements, ue.connected_gnb_id
            )
            
            if target_result:
                target_gnb_id, cause = target_result
                
                # Check if handover is not already ongoing
                if ue_id not in self.handover_manager.ongoing_handovers:
                    success = self.handover_manager.initiate_handover(
                        ue_id, ue.connected_gnb_id, target_gnb_id, cause, self.current_time * 1000
                    )
                    if success:
                        print(f"Handover initiated: UE {ue_id} from gNB {ue.connected_gnb_id} to gNB {target_gnb_id}")
        
        # Process ongoing handovers
        completed_handovers = self.handover_manager.process_handover_procedures(self.current_time * 1000)
        
        for ue_id, source_gnb_id, target_gnb_id in completed_handovers:
            # Update UE connection
            if ue_id in self.ues:
                # Remove from source gNB
                if source_gnb_id in self.gnbs:
                    self.gnbs[source_gnb_id].remove_ue(ue_id)
                
                # Add to target gNB
                if target_gnb_id in self.gnbs:
                    context = {'initial_qci': self.config.default_qci}
                    success = self.gnbs[target_gnb_id].handover_reception(ue_id, source_gnb_id, context)
                    if success:
                        self.ues[ue_id].connected_gnb_id = target_gnb_id
                        print(f"Handover completed: UE {ue_id} now served by gNB {target_gnb_id}")
    
    def _allocate_resources(self):
        """Allocate resources for all gNBs."""
        for gnb in self.gnbs.values():
            allocations = gnb.allocate_resources()
            # Resource allocations are handled internally by gNB
    
    def _calculate_performance_metrics(self):
        """Calculate performance metrics for current time step."""
        metrics = {
            'timestamp': self.current_time,
            'ue_metrics': {},
            'gnb_metrics': {},
            'system_metrics': {}
        }
        
        # UE metrics
        for ue_id, ue in self.ues.items():
            ue_metrics = {
                'position': (ue.current_position.x, ue.current_position.y),
                'connected_gnb': ue.connected_gnb_id,
                'speed': ue.get_current_speed(),
                'rsrp_measurements': ue.rsrp_measurements.copy()
            }
            
            # Calculate throughput if connected
            if ue.connected_gnb_id is not None and ue.connected_gnb_id in self.gnbs:
                gnb = self.gnbs[ue.connected_gnb_id]
                ul_thr, dl_thr = gnb.calculate_throughput(ue_id, ue.current_position)
                ue_metrics['throughput_ul_mbps'] = ul_thr
                ue_metrics['throughput_dl_mbps'] = dl_thr
                
                # Get channel characteristics
                channel_char = self.channel_model.get_channel_characteristics(
                    gnb.position, ue.current_position,
                    self.config.gnb_tx_power, self.config.bandwidth * 1e6
                )
                ue_metrics['channel_characteristics'] = channel_char
            
            metrics['ue_metrics'][ue_id] = ue_metrics
        
        # gNB metrics
        for gnb_id, gnb in self.gnbs.items():
            gnb.update_statistics(self.config.time_step)
            metrics['gnb_metrics'][gnb_id] = gnb.get_statistics()
        
        # System metrics
        total_ues = len(self.ues)
        connected_ues = sum(1 for ue in self.ues.values() if ue.connected_gnb_id is not None)
        avg_throughput_dl = np.mean([
            m.get('throughput_dl_mbps', 0) for m in metrics['ue_metrics'].values()
        ])
        avg_throughput_ul = np.mean([
            m.get('throughput_ul_mbps', 0) for m in metrics['ue_metrics'].values()
        ])
        
        handover_stats = self.handover_manager.get_handover_statistics()
        
        metrics['system_metrics'] = {
            'total_ues': total_ues,
            'connected_ues': connected_ues,
            'connection_rate': connected_ues / total_ues if total_ues > 0 else 0,
            'average_throughput_dl_mbps': avg_throughput_dl,
            'average_throughput_ul_mbps': avg_throughput_ul,
            'handover_statistics': handover_stats
        }
        
        self.metrics_collector.add_measurement(metrics)
    
    def run_simulation(self) -> 'SimulationResults':
        """Run the complete simulation."""
        print(f"Starting 5G NR simulation...")
        print(f"Configuration: {self.config.num_gnbs} gNBs, {self.config.num_ues} UEs")
        print(f"Simulation time: {self.config.simulation_time}s, Time step: {self.config.time_step}s")
        
        self.running = True
        start_time = time.time()
        
        try:
            for step in range(self.time_steps):
                self.current_step = step
                self.current_time = step * self.config.time_step
                
                # Simulation steps
                self._update_ue_mobility()
                self._update_rsrp_measurements()
                self._process_handovers()
                self._allocate_resources()
                self._calculate_performance_metrics()
                
                # Progress reporting
                if step % 100 == 0 or step == self.time_steps - 1:
                    progress = (step + 1) / self.time_steps * 100
                    print(f"Simulation progress: {progress:.1f}% (Step {step + 1}/{self.time_steps})")
        
        except KeyboardInterrupt:
            print("Simulation interrupted by user")
        
        finally:
            self.running = False
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"Simulation completed in {execution_time:.2f} seconds")
        
        # Generate results
        results = self.metrics_collector.generate_results()
        results.execution_time = execution_time
        results.config = self.config
        
        return results
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulation state."""
        return {
            'current_time': self.current_time,
            'current_step': self.current_step,
            'total_steps': self.time_steps,
            'progress': self.current_step / self.time_steps if self.time_steps > 0 else 0,
            'running': self.running,
            'gnbs': {gnb_id: gnb.get_statistics() for gnb_id, gnb in self.gnbs.items()},
            'ues': {ue_id: ue.get_statistics() for ue_id, ue in self.ues.items()},
            'handover_stats': self.handover_manager.get_handover_statistics()
        }