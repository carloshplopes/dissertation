"""
Main Simulation Engine for 5G NR QoS and Mobility Framework

This module implements the core discrete event simulation engine using SimPy.
"""

import simpy
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import asdict
import numpy as np

from ..network.gnb import gNB
from ..network.ue import UserEquipment
from ..mobility.mobility_models import MobilityManager
from ..utils.metrics import MetricsCollector
from .qos_manager import QoSManager
from .config import SimulationConfig

logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Main simulation engine coordinating all components
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.env = simpy.Environment()
        
        # Set random seed for reproducibility
        if config.random_seed is not None:
            np.random.seed(config.random_seed)
            
        # Initialize managers and collectors
        self.qos_manager = QoSManager()
        self.mobility_manager = MobilityManager(self.env)
        self.metrics = MetricsCollector()
        
        # Network components
        self.gnbs: List[gNB] = []
        self.ues: List[UserEquipment] = []
        
        # Simulation state
        self.running = False
        self.current_time = 0.0
        
        logger.info(f"Simulation engine initialized with {config.num_gnbs} gNBs and {config.num_ues} UEs")

    def setup_network(self):
        """Initialize network components (gNBs and UEs)"""
        logger.info("Setting up network topology")
        
        # Create gNBs
        for i in range(self.config.num_gnbs):
            # Position gNBs in a grid pattern
            if self.config.num_gnbs == 1:
                position = (0, 0)
            else:
                rows = int(np.ceil(np.sqrt(self.config.num_gnbs)))
                row = i // rows
                col = i % rows
                position = (col * 1000, row * 1000)  # 1km spacing
                
            gnb = gNB(
                gnb_id=i,
                position=position,
                coverage_radius=self.config.coverage_radius,
                frequency=self.config.carrier_frequency,
                bandwidth=self.config.bandwidth,
                env=self.env,
                qos_manager=self.qos_manager
            )
            self.gnbs.append(gnb)
            logger.info(f"Created gNB {i} at position {position}")

        # Create UEs
        for i in range(self.config.num_ues):
            # Use provided positions or generate random ones
            if self.config.initial_positions and i < len(self.config.initial_positions):
                position = self.config.initial_positions[i]
            else:
                # Random position within coverage of first gNB
                angle = np.random.uniform(0, 2 * np.pi)
                distance = np.random.uniform(0, self.config.coverage_radius * 0.8)
                position = (
                    self.gnbs[0].position[0] + distance * np.cos(angle),
                    self.gnbs[0].position[1] + distance * np.sin(angle)
                )
                
            ue = UserEquipment(
                ue_id=i,
                initial_position=position,
                mobility_model=self.config.mobility_model,
                speed=self.config.mobility_speed,
                env=self.env,
                qos_manager=self.qos_manager
            )
            self.ues.append(ue)
            logger.info(f"Created UE {i} at position {position}")

        # Setup initial connections
        self._setup_initial_connections()

    def _setup_initial_connections(self):
        """Establish initial connections between UEs and gNBs"""
        for ue in self.ues:
            # Find closest gNB
            best_gnb = None
            best_distance = float('inf')
            
            for gnb in self.gnbs:
                distance = ue.calculate_distance_to(gnb.position)
                if distance < gnb.coverage_radius and distance < best_distance:
                    best_distance = distance
                    best_gnb = gnb
                    
            if best_gnb:
                ue.connect_to_gnb(best_gnb)
                logger.info(f"UE {ue.ue_id} connected to gNB {best_gnb.gnb_id}")
            else:
                logger.warning(f"UE {ue.ue_id} could not connect to any gNB")

    def setup_traffic(self):
        """Setup traffic generators for UEs"""
        logger.info("Setting up traffic generators")
        
        for ue in self.ues:
            # Create QoS flow for each UE
            flow_id = ue.ue_id
            if self.qos_manager.create_flow(flow_id, self.config.qi_value):
                # Start traffic generation process
                self.env.process(self._generate_traffic(ue, flow_id))
                logger.info(f"Started traffic generation for UE {ue.ue_id} with 5QI {self.config.qi_value}")

    def _generate_traffic(self, ue: UserEquipment, flow_id: int):
        """Traffic generation process for a UE"""
        packet_id = 0
        
        while True:
            if ue.connected_gnb is not None:
                # Create packet
                packet = {
                    'id': packet_id,
                    'source_ue': ue.ue_id,
                    'flow_id': flow_id,
                    'size': self.config.packet_size,
                    'creation_time': self.env.now,
                    'qi_value': self.config.qi_value
                }
                
                # Send packet through UE
                yield ue.send_packet(packet)
                packet_id += 1
                
            # Wait for next packet interval
            yield self.env.timeout(self.config.packet_interval)

    def setup_mobility(self):
        """Initialize mobility for UEs"""
        logger.info("Setting up mobility models")
        
        for ue in self.ues:
            self.mobility_manager.add_ue(ue)
            
        # Start mobility update process
        self.env.process(self._mobility_update_process())

    def _mobility_update_process(self):
        """Process to periodically update UE positions and handle handovers"""
        update_interval = 0.1  # 100ms updates
        
        while True:
            self.mobility_manager.update_positions()
            
            # Check for handovers
            for ue in self.ues:
                if ue.connected_gnb:
                    current_distance = ue.calculate_distance_to(ue.connected_gnb.position)
                    
                    # Check if UE is out of coverage
                    if current_distance > ue.connected_gnb.coverage_radius:
                        # Find new gNB
                        new_gnb = self._find_best_gnb(ue)
                        if new_gnb and new_gnb != ue.connected_gnb:
                            self._perform_handover(ue, new_gnb)
                            
            yield self.env.timeout(update_interval)

    def _find_best_gnb(self, ue: UserEquipment) -> Optional[gNB]:
        """Find the best gNB for a UE based on distance and signal strength"""
        best_gnb = None
        best_signal = -float('inf')
        
        for gnb in self.gnbs:
            distance = ue.calculate_distance_to(gnb.position)
            if distance <= gnb.coverage_radius:
                # Simple path loss model (free space)
                signal_strength = gnb.calculate_signal_strength(distance)
                if signal_strength > best_signal:
                    best_signal = signal_strength
                    best_gnb = gnb
                    
        return best_gnb

    def _perform_handover(self, ue: UserEquipment, target_gnb: gNB):
        """Perform handover procedure"""
        old_gnb = ue.connected_gnb
        
        # Record handover event
        handover_event = {
            'time': self.env.now,
            'ue_id': ue.ue_id,
            'source_gnb': old_gnb.gnb_id if old_gnb else None,
            'target_gnb': target_gnb.gnb_id,
            'ue_position': ue.position
        }
        self.metrics.record_handover(handover_event)
        
        # Perform handover
        ue.connect_to_gnb(target_gnb)
        
        logger.info(f"Handover: UE {ue.ue_id} from gNB {old_gnb.gnb_id if old_gnb else 'None'} "
                   f"to gNB {target_gnb.gnb_id} at time {self.env.now:.2f}s")

    def run(self) -> Dict[str, Any]:
        """
        Run the simulation
        
        Returns:
            Dictionary containing simulation results and metrics
        """
        logger.info(f"Starting simulation for {self.config.simulation_time} seconds")
        
        # Setup simulation components
        self.setup_network()
        self.setup_traffic()
        self.setup_mobility()
        
        # Start metrics collection
        self.env.process(self.metrics.collection_process(self.env, self.ues, self.gnbs))
        
        # Run simulation
        self.running = True
        try:
            self.env.run(until=self.config.simulation_time)
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            raise
        finally:
            self.running = False
            
        logger.info("Simulation completed")
        
        # Collect and return results
        results = self._collect_results()
        return results

    def _collect_results(self) -> Dict[str, Any]:
        """Collect and compile simulation results"""
        results = {
            'config': asdict(self.config),
            'metrics': self.metrics.get_summary(),
            'qos_summary': self.qos_manager.get_flow_summary(),
            'network_summary': {
                'num_gnbs': len(self.gnbs),
                'num_ues': len(self.ues),
                'total_handovers': len(self.metrics.handover_events)
            }
        }
        
        return results

    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save simulation results to file"""
        if filename is None:
            filename = f"simulation_results_{int(self.env.now)}.json"
            
        filepath = f"{self.config.output_directory}/{filename}"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulation state"""
        return {
            'time': self.env.now,
            'running': self.running,
            'ue_positions': [(ue.ue_id, ue.position) for ue in self.ues],
            'connections': [(ue.ue_id, ue.connected_gnb.gnb_id if ue.connected_gnb else None) 
                          for ue in self.ues],
            'active_flows': self.qos_manager.get_active_flows_count()
        }