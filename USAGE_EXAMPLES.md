# 5G NR QoS and Mobility Simulation Framework - Usage Examples

This document provides practical examples of how to use the simulation framework for your Master's thesis research.

## Quick Start

### 1. Basic Static Network Analysis
```bash
# Run a basic scenario with 3 gNBs and 10 stationary UEs
python run_simulation.py --scenario basic

# With custom output location
python run_simulation.py --scenario basic --results-dir results/my_basic_test
```

### 2. Mobility and Handover Analysis
```bash
# Run mobility scenario with various movement patterns
python run_simulation.py --scenario mobility

# Without visualizations for faster execution
python run_simulation.py --scenario mobility --no-visualization
```

### 3. High-Bitrate Video Streaming Analysis
```bash
# Simulate GBR video streaming services
python run_simulation.py --scenario video_streaming
```

### 4. Custom Configuration
```bash
# Create a custom scenario configuration
python run_simulation.py --create-scenario basic --config-output my_scenario.json

# Run with custom configuration
python run_simulation.py --config my_scenario.json
```

## Typical Results

### Basic Scenario Performance
- **Average DL Throughput**: 3.7-3.8 Mbps
- **Average UL Throughput**: 2.6-2.7 Mbps  
- **Handover Success Rate**: >95%
- **Connection Reliability**: 100%

### Mobility Scenario Performance
- **UEs**: 15 with mixed mobility patterns
- **Handover Events**: ~2500 attempts in 60s
- **Success Rate**: 95.2%
- **Throughput**: Maintained during mobility

### Video Streaming Scenario Performance  
- **Average DL Throughput**: 345.96 Mbps
- **Average UL Throughput**: 242.17 Mbps
- **Peak DL Throughput**: 422.74 Mbps
- **GBR Service**: 50 Mbps UL / 100 Mbps DL guaranteed

## Key Research Applications

### 1. QoS Analysis
- Compare performance across different 5QI values
- Analyze GBR vs Non-GBR service performance
- Study packet delay and error rate compliance

### 2. Mobility Impact Studies
- Evaluate handover performance vs speed
- Analyze service continuity during movement
- Study ping-pong handover prevention

### 3. Network Planning
- Optimize gNB placement for coverage
- Analyze resource utilization patterns
- Study load balancing effectiveness

### 4. Service Quality Validation
- Validate video streaming QoS requirements
- Analyze emergency service priority handling
- Study interference and capacity planning

## Generated Outputs

### Metrics and Data
- **JSON Results**: Detailed simulation metrics
- **CSV Export**: Time-series data for analysis
- **Excel Reports**: Summary statistics and per-UE data

### Visualizations
- **Network Topology**: gNB and UE positions
- **Performance Overview**: Throughput and connection rates
- **QoS Analysis**: SINR, RSRP distributions
- **Mobility Analysis**: Speed vs performance correlations
- **Handover Analysis**: Success rates and timing
- **Coverage Heatmaps**: Signal quality maps

## Configuration Examples

### Custom Mobility Patterns
```json
{
  "ues": {
    "num_ues": 10,
    "mobility_models": ["linear", "circular", "random_walk"],
    "mobility_params": [
      {"speed": 20.0, "direction": 0.0},
      {"radius": 300.0, "angular_speed": 0.03},
      {"max_speed": 10.0, "direction_change_prob": 0.05}
    ]
  }
}
```

### High-Priority Emergency Services
```json
{
  "qos": {
    "qos_flows": [
      {"ue_id": 0, "qci": 1, "guaranteed_bitrate_ul": 64, "guaranteed_bitrate_dl": 64},
      {"ue_id": 1, "qci": 5}
    ]
  }
}
```

## Performance Tips

1. **Faster Execution**: Use `--no-visualization` for batch runs
2. **Memory Efficiency**: Reduce simulation time for large UE counts
3. **Detailed Analysis**: Enable all visualizations for presentation
4. **Batch Processing**: Script multiple scenarios for comparison

## Integration with Research

### Statistical Analysis
```python
import pandas as pd
import json

# Load simulation results
with open('results/my_results.json', 'r') as f:
    results = json.load(f)

# Convert to DataFrame for analysis
df = pd.DataFrame(results['ue_statistics'])
df = df.T  # Transpose for UE-based analysis

# Calculate confidence intervals, perform statistical tests
mean_throughput = df['average_throughput_dl_mbps'].mean()
throughput_std = df['average_throughput_dl_mbps'].std()
```

### Publication-Ready Plots
The framework generates publication-ready visualizations in PNG format at 300 DPI, suitable for academic papers and presentations.

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure all dependencies are installed (`pip install -r requirements.txt`)
2. **Visualization Issues**: Install seaborn if plots fail (`pip install seaborn`)
3. **Memory Issues**: Reduce simulation time or number of UEs for large scenarios
4. **Configuration Errors**: Validate JSON syntax and required fields

### Performance Optimization
- Use shorter time steps (0.05s) only for detailed analysis
- Disable fast fading for computational efficiency if not needed
- Use appropriate propagation models for your scenario (urban_macro for most cases)

## Citation

When using this framework in your research, please cite:

```
@software{5g_nr_simulation_framework,
  title={5G NR QoS and Mobility Simulation Framework},
  author={Carlos H. P. Lopes},
  year={2024},
  url={https://github.com/carloshplopes/dissertation}
}
```

## Support

For technical questions or research collaboration:
- Create an issue on GitHub
- Email: [your.email@university.edu]
- Documentation: See README.md for detailed API reference