// Integrated Simulation: Stadium Scenario + Handover + Data Transmission
// Based on working cap5-05.7 file + handover elements from cap5-05.6
// 


 #include "ns3/antenna-module.h"
 #include "ns3/applications-module.h"
 #include "ns3/buildings-module.h"
 #include "ns3/config-store-module.h"
 #include "ns3/core-module.h"
 #include "ns3/flow-monitor-module.h"
 #include "ns3/internet-apps-module.h"
 #include "ns3/internet-module.h"
 #include "ns3/mobility-module.h"
 #include "ns3/nr-module.h"
 #include "ns3/point-to-point-module.h"
 #include "ns3/netanim-module.h"
 #include <fstream>
 #include <map>
 #include <set>
 #include <limits>
 #include <iomanip>
 
 /*
  * Use, always, the namespace ns3. All the NR classes are inside such namespace.
  */
 using namespace ns3;
 
 /*
  * With this line, we will be able to see the logs of the file by enabling the
  * component "CttcNrDemo".
  * Further information on how logging works can be found in the ns-3 documentation [3].
  */
 NS_LOG_COMPONENT_DEFINE("StadiumHandoverDemo");

// ========== OUTPUT FILES FOR HANDOVER AND TRACKING ==========
std::ofstream flowStatsFile;
std::ofstream handoverFile;
std::ofstream positionFile;
std::ofstream powerFile;

// ========== GLOBAL VARIABLES FOR HANDOVER TRACKING ==========
std::map<FlowId, FlowMonitor::FlowStats> lastFlowStats;
std::map<uint32_t, uint32_t> previousServingCell;
std::map<uint32_t, Vector> lastUePositions;
std::map<uint32_t, double> lastRefereeActivityTime;
std::set<uint32_t> refereeNodeIds;
bool flowStatsHeaderWritten = false;
bool handoverHeaderWritten = false;
bool positionHeaderWritten = false;
bool powerHeaderWritten = false;
uint32_t handoverCount = 0;
uint32_t manualHandoverCount = 0;

// Statistics structure (based on reference file)
struct SimulationStats {
    uint32_t handovers = 0;
    uint32_t connectionEstablishments = 0;
    uint32_t connectionReconfiguration = 0;
} simStats;

// ========== STADIUM PARAMETERS ==========
const double CATWALK_RADIUS = 120.0;   // Radius of catwalk where gNBs are located
const double CATWALK_HEIGHT = 25.0;    // Height of gNBs on catwalk  
const double CAMPO_RADIUS = 60.0;      // Radius of field where referees move
const double ARBITRO_HEIGHT = 1.7;     // Height of referees
const double ARBITRO_SPEED = 5.0;      // Speed of referees (m/s) - at 15s of simulation the referees will be able to move 75 meters

// ========== REFEREE CIRCULAR MOVEMENT FUNCTION ==========
void MoveArbitroCircular(Ptr<Node> ue, uint32_t ueId)
{
    Ptr<MobilityModel> mobility = ue->GetObject<MobilityModel>();
    
    // Maintain unique angles for each referee
    static std::map<uint32_t, double> ueAngles;
    if (ueAngles.find(ueId) == ueAngles.end())
    {
        // Initially distribute referees
        ueAngles[ueId] = (ueId * 2.0 * M_PI) / 4.0;
    }
    
    // Calculate angle increment based on speed
    double deltaAngle = (ARBITRO_SPEED * 0.5) / CAMPO_RADIUS; // 0.5s interval
    ueAngles[ueId] += deltaAngle;
    
    // Calculate new circular position
    double newX = CAMPO_RADIUS * cos(ueAngles[ueId]);
    double newY = CAMPO_RADIUS * sin(ueAngles[ueId]);
    
    // Update position maintaining height
    mobility->SetPosition(Vector(newX, newY, ARBITRO_HEIGHT));
    
    // Schedule next movement if simulation is still running
    // Correção: Escalonar atualizações para evitar sobrecarga simultânea do scheduler
    if (Simulator::Now().GetSeconds() < 14.5)
    {
        // Cada árbitro atualiza em momentos diferentes (offset de 125ms entre eles)
        Simulator::Schedule(MilliSeconds(500), &MoveArbitroCircular, ue, ueId);
    }
}

// ========== POSITION TRACKING FUNCTION FOR REFEREES ==========
void TrackUePosition(Ptr<Node> ue, uint32_t ueId)
{
    if (!positionFile.is_open())
    {
        positionFile.open("ue_positions_stadium.csv");
        positionFile << "Time,UE_ID,X,Y,Z,Speed_ms" << std::endl;
    }
    
    Ptr<MobilityModel> mobility = ue->GetObject<MobilityModel>();
    Vector pos = mobility->GetPosition();
    Vector vel = mobility->GetVelocity();
    double speed = std::sqrt(vel.x*vel.x + vel.y*vel.y + vel.z*vel.z);
    
    positionFile << std::fixed << std::setprecision(3)
                << Simulator::Now().GetSeconds() << ","
                << ueId << ","
                << pos.x << ","
                << pos.y << ","
                << pos.z << ","
                << speed << std::endl;
    
    // Correção: Reschedule com offset específico para cada UE para evitar sobrecarga
    if (Simulator::Now().GetSeconds() < 14.5)
    {
        double offset = (ueId % 5) * 0.1;  // Offset de 0-0.4s baseado no ID do UE
        Simulator::Schedule(Seconds(0.5 + offset), &TrackUePosition, ue, ueId);
    }
}

// ========== PERIODIC POSITION AND HANDOVER REPORT ==========
void PeriodicPositionReport(NodeContainer ueNodes)
{
    double currentTime = Simulator::Now().GetSeconds();
    
    // Readable time format (fixed to avoid exponential notation)
    std::cout << std::fixed << std::setprecision(1) << "\n📍 [" << currentTime << "s] Position Report:" << std::endl;
    
    for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
    {
        Ptr<MobilityModel> mobility = ueNodes.Get(i)->GetObject<MobilityModel>();
        Vector pos = mobility->GetPosition();
        Vector vel = mobility->GetVelocity();
        double speed = std::sqrt(vel.x*vel.x + vel.y*vel.y + vel.z*vel.z);
        
        std::cout << std::fixed << std::setprecision(1)
                  << "   Camera " << i << ": ("
                  << pos.x << ", " << pos.y << ", " << pos.z
                  << ") - Speed: " << std::setprecision(2) << speed << " m/s" << std::endl;
    }
    
    // Schedule next report
    if (currentTime < 14.5)
    {
        Simulator::Schedule(Seconds(0.5), &PeriodicPositionReport, ueNodes);
    }
}


// ========== POWER MEASUREMENT AND HANDOVER DETECTION FUNCTION ==========
void LogPowerAndHandover(Ptr<Node> ue, uint32_t ueId, NodeContainer gnbNodes)
{
    if (!powerFile.is_open())
    {
        powerFile.open("power_measurements_stadium.csv");
        powerFile << "Time,UE_ID,Best_gNB_ID,RSRP_dBm,Distance_m,Handover_Event" << std::endl;
    }
    
    Ptr<MobilityModel> ueMobility = ue->GetObject<MobilityModel>();
    Vector uePos = ueMobility->GetPosition();
    
    double bestRsrp = -150.0;
    uint32_t bestGnbId = 0;
    double bestDistance = 0.0;
    
    // Find the gNB with best RSRP
    for (uint32_t gnbId = 0; gnbId < gnbNodes.GetN(); ++gnbId)
    {
        Ptr<Node> gnbNode = gnbNodes.Get(gnbId);
        Ptr<MobilityModel> gnbMobility = gnbNode->GetObject<MobilityModel>();
        Vector gnbPos = gnbMobility->GetPosition();
            
            // Calculate 3D distance
            double distance = std::sqrt(
                std::pow(uePos.x - gnbPos.x, 2) +
                std::pow(uePos.y - gnbPos.y, 2) +
                std::pow(uePos.z - gnbPos.z, 2)
            );
            
            // Simplified RSRP model (3GPP UMi)
            double pathLoss = 32.4 + 21.0 * log10(distance) + 20.0 * log10(3.7);
            double rsrp = 35.0 - pathLoss; // 35 dBm gNB power
            
            if (rsrp > bestRsrp)
            {
                bestRsrp = rsrp;
                bestGnbId = gnbId;
                bestDistance = distance;
            }
        }
        
        // Detect cell change (handover)
        bool handoverDetected = false;
        if (previousServingCell.find(ueId) != previousServingCell.end())
        {
            if (previousServingCell[ueId] != bestGnbId)
            {
                handoverDetected = true;
                handoverCount++;
                manualHandoverCount++;
                simStats.handovers++;
                
               
                
                // Detailed handover log
                if (!handoverFile.is_open())
                {
                    handoverFile.open("handover_log_stadium.txt");
                }
                
                handoverFile << std::fixed << std::setprecision(6)
                           << "[" << Simulator::Now().GetSeconds() << "s] "
                           << "HANDOVER: Referee_" << ueId 
                           << " gNB_" << previousServingCell[ueId] << " -> gNB_" << bestGnbId
                           << " (RSRP: " << std::setprecision(1) << bestRsrp << " dBm)"
                           << " (Dist: " << std::setprecision(1) << bestDistance << " m)"
                           << " [Total_HOs: " << handoverCount << "]" << std::endl;
                
                std::cout << "[HANDOVER] T=" << std::setprecision(3) << Simulator::Now().GetSeconds() 
                         << "s Referee_" << ueId << ": gNB_" << previousServingCell[ueId] 
                         << " -> gNB_" << bestGnbId 
                         << " (RSRP=" << std::setprecision(1) << bestRsrp << "dBm)" << std::endl;
            }
        }
        
    previousServingCell[ueId] = bestGnbId;
    
    // Save measurement to CSV file (readable time format)
    double currentTime = Simulator::Now().GetSeconds();
    powerFile << std::fixed << std::setprecision(1)
             << currentTime << ","
             << ueId << ","
             << bestGnbId << ","
             << std::setprecision(1) << bestRsrp << ","
             << std::setprecision(1) << bestDistance << ","
             << (handoverDetected ? "YES" : "NO") << std::endl;
    
    // Reschedule next measurement
    if (Simulator::Now().GetSeconds() < 14.5)
    {
        Simulator::Schedule(Seconds(0.5), &LogPowerAndHandover, ue, ueId, gnbNodes);
    }
}

// ========== CALLBACK DE HANDOVER PARA GARANTIR CONECTIVIDADE ==========
void NotifyHandoverEndOkUe(std::string context, uint64_t imsi, uint16_t cellId, uint16_t rnti)
{
    double now = Simulator::Now().GetSeconds();
    std::cout << "[HANDOVER_OK] T=" << std::fixed << std::setprecision(3) << now 
              << "s - UE IMSI=" << imsi << " completou handover para CellId=" << cellId 
              << " (RNTI=" << rnti << "). Bearer mantido com sucesso." << std::endl;
}

void NotifyHandoverStartUe(std::string context, uint64_t imsi, uint16_t cellId, uint16_t rnti, uint16_t targetCellId)
{
    double now = Simulator::Now().GetSeconds();
    std::cout << "[HANDOVER_START] T=" << std::fixed << std::setprecision(3) << now 
              << "s - UE IMSI=" << imsi << " iniciando handover de CellId=" << cellId 
              << " para CellId=" << targetCellId << std::endl;
}

// ========== MECANISMO DE RECONEXÃO AUTOMÁTICA ==========
void CheckAndReconnectUes(Ptr<NrHelper> nrHelper,
                          NetDeviceContainer ueNetDevs,
                          NetDeviceContainer gnbNetDevs,
                          Ptr<FlowMonitor> monitor,
                          Ptr<Ipv4FlowClassifier> classifier)
{
    // Parâmetros não utilizados diretamente nesta versão de verificação
    (void)monitor;
    (void)classifier;

    const double now = Simulator::Now().GetSeconds();
    const double inactivityThreshold = 1.5; // segundos sem tráfego recebido

    for (uint32_t i = 0; i < ueNetDevs.GetN(); ++i)
    {
        Ptr<Node> ueNode = ueNetDevs.Get(i)->GetNode();
        uint32_t nodeId = ueNode->GetId();

        // Somente os UEs móveis (árbitros) são monitorados
        if (refereeNodeIds.find(nodeId) == refereeNodeIds.end())
        {
            continue;
        }

        double lastActiveTime = std::numeric_limits<double>::lowest();
        auto it = lastRefereeActivityTime.find(nodeId);
        if (it != lastRefereeActivityTime.end())
        {
            lastActiveTime = it->second;
        }

        bool isActive = (lastActiveTime != std::numeric_limits<double>::lowest()) &&
                        ((now - lastActiveTime) <= inactivityThreshold);

        if (!isActive)
        {
            double elapsed = (lastActiveTime == std::numeric_limits<double>::lowest()) ? -1.0 : (now - lastActiveTime);
            std::cout << "[RECONNECT] T=" << now << "s - Árbitro com NodeId " << nodeId
                      << " sem atividade há " << (elapsed < 0 ? "N/A" : std::to_string(elapsed) + "s")
                      << ". Forçando reconexão na gNB mais próxima." << std::endl;

            NetDeviceContainer singleUe;
            singleUe.Add(ueNetDevs.Get(i));
            nrHelper->AttachToClosestGnb(singleUe, gnbNetDevs);

            // Atualiza a última atividade para evitar múltiplas reconexões consecutivas
            lastRefereeActivityTime[nodeId] = now;
        }
    }

    if (now < 14.5)
    {
        Simulator::Schedule(Seconds(2.0), &CheckAndReconnectUes, nrHelper, ueNetDevs, gnbNetDevs, monitor, classifier);
    }
}




// ========== FLOW MONITORING FUNCTION ==========
void
TraceFlowMonitorStats(Ptr<FlowMonitor> monitor, Ptr<Ipv4FlowClassifier> classifier)
{
    if (!flowStatsFile.is_open())
    {
        flowStatsFile.open("flow_stats.csv", std::ios_base::out);
    }

    if (!flowStatsHeaderWritten)
    {
        flowStatsFile << "Time,UeId,FlowId,Direction,SrcAddr,DstAddr,Throughput_kbps,Latency_ms,Jitter_ms,PacketLoss" << std::endl;
        flowStatsHeaderWritten = true;
    }

    monitor->CheckForLostPackets();
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();

    for (auto const& [flowId, flowStats] : stats)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(flowId);
        
        Ipv4Mask ueSubnetMask("255.0.0.0");
        Ipv4Address ueSubnet("7.0.0.0");
        std::string direction = (t.sourceAddress.CombineMask(ueSubnetMask) == ueSubnet) ? "UL" : "DL";
        
        uint32_t ueId = 0;
        Ipv4Address ueIp = (direction == "UL") ? t.sourceAddress : t.destinationAddress;
        for(uint32_t i = 0; i < NodeList::GetNNodes(); ++i)
        {
            Ptr<Ipv4> ipv4 = NodeList::GetNode(i)->GetObject<Ipv4>();
            if (ipv4 && ipv4->GetNInterfaces() > 1) 
            {
                Ipv4Address addr = ipv4->GetAddress(1, 0).GetLocal();
                if (addr == ueIp)
                {
                    ueId = NodeList::GetNode(i)->GetId();
                    break;
                }
            }
        }

        double interval = 0.1;
        double currentThroughput = 0;
        double currentLatency = 0;
        double currentJitter = 0;
        uint32_t currentPacketLoss = 0;

        bool rxIncreased = false;
        auto it = lastFlowStats.find(flowId);
        if (it != lastFlowStats.end())
        {
            const FlowMonitor::FlowStats& lastStats = it->second;
            if (flowStats.rxPackets > lastStats.rxPackets)
            {
                rxIncreased = true;
                currentThroughput = ((flowStats.rxBytes - lastStats.rxBytes) * 8.0) / (interval * 1000.0);
                currentLatency = (flowStats.delaySum - lastStats.delaySum).GetSeconds() * 1000.0 / (flowStats.rxPackets - lastStats.rxPackets);
                currentJitter = (flowStats.jitterSum - lastStats.jitterSum).GetSeconds() * 1000.0 / (flowStats.rxPackets - lastStats.rxPackets);
            }
            currentPacketLoss = (flowStats.lostPackets - lastStats.lostPackets);
        } else { 
             if (flowStats.rxPackets > 0)
            {
                rxIncreased = true;
                currentThroughput = (flowStats.rxBytes * 8.0) / (interval * 1000.0);
                currentLatency = flowStats.delaySum.GetSeconds() * 1000.0 / flowStats.rxPackets;
                currentJitter = flowStats.jitterSum.GetSeconds() * 1000.0 / flowStats.rxPackets;
            }
            currentPacketLoss = flowStats.lostPackets;
        }
        
        lastFlowStats[flowId] = flowStats;

        if (direction == "UL" && rxIncreased && refereeNodeIds.find(ueId) != refereeNodeIds.end())
        {
            lastRefereeActivityTime[ueId] = Simulator::Now().GetSeconds();
        }

        flowStatsFile << Simulator::Now().GetSeconds() << ","
                      << ueId << ","
                      << flowId << ","
                      << direction << ","
                      << t.sourceAddress << ","
                      << t.destinationAddress << ","
                      << currentThroughput << ","
                      << currentLatency << ","
                      << currentJitter << ","
                      << currentPacketLoss << std::endl;
    }
    Simulator::Schedule(Seconds(0.1), &TraceFlowMonitorStats, monitor, classifier);
}

// ========== FINAL STATISTICS ==========
void PrintFinalStats()
{
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << " STADIUM SIMULATION FINAL STATISTICS" << std::endl;
    std::cout << std::string(60, '=') << std::endl;
    
    double simDuration = Simulator::Now().GetSeconds();
    std::cout << std::fixed << std::setprecision(1)
              << "⏱  Simulation Duration: " << simDuration << "s" << std::endl;
    std::cout << "  Stadium Scenario: 6 gNBs (catwalk) + 4 referees (field)" << std::endl;
    std::cout << " Connection Establishments: " << simStats.connectionEstablishments << std::endl;
    std::cout << " Total Handovers (Manual Detection): " << manualHandoverCount << std::endl;
    std::cout << " Total Handover Events (Traces): " << simStats.handovers << std::endl;
    
    // Per-UE statistics (if available)
    std::cout << "\n Per-UE Statistics:" << std::endl;
    for (uint32_t i = 0; i < 4; ++i) // 4 referees
    {
        std::cout << "   Referee " << i << ": Circular movement at " << ARBITRO_SPEED << " m/s" << std::endl;
    }
    
    std::cout << "\n Output files generated:" << std::endl;
    std::cout << "    handover_log_stadium.txt (handover events)" << std::endl;
    std::cout << "     ue_positions_stadium.csv (referee trajectories)" << std::endl;
    std::cout << "    power_measurements_stadium.csv (TX/RX power analysis)" << std::endl;
    std::cout << "    flow_stats.csv (traffic flow statistics)" << std::endl;
    
    std::cout << "\n Stadium Scenario Summary:" << std::endl;
    std::cout << "   - gNBs: Circular catwalk (r=" << CATWALK_RADIUS << "m, h=" << CATWALK_HEIGHT << "m)" << std::endl;
    std::cout << "   - Referees: Circular field (r=" << CAMPO_RADIUS << "m, h=" << ARBITRO_HEIGHT << "m)" << std::endl;
    std::cout << "   - QoS: Voice + Video + ULL + BestEffort traffic" << std::endl;
    std::cout << std::string(60, '=') << std::endl;
    
    // Close files
    if (handoverFile.is_open()) handoverFile.close();
    if (positionFile.is_open()) positionFile.close();
    if (powerFile.is_open()) powerFile.close();
    if (flowStatsFile.is_open()) flowStatsFile.close();
}
 
// ========== MAIN FUNCTION ==========
 int
 main(int argc, char* argv[])
 {
     /*
      * Variables that represent the parameters we will accept as input by the
      * command line. Each of them is initialized with a default value, and
      * possibly overridden below when command-line arguments are parsed.
      */
     // ========== CONFIGURATION PARAMETERS ==========
     uint16_t gNbNum = 6;  // 6 gNBs on stadium catwalk
     uint16_t ueNumPergNb = 1;
     bool logging = false;
     
     // Traffic optimization to prevent scheduler crashes
     uint32_t refereeBitRate = 5000000;   // 5 Mbps effective
     uint32_t cameraBitRate = 35000000;   // 35 Mbps as per user requirements
     bool doubleOperationalBand = false;
     bool traces = false;
     bool anim = false;
 
     // Traffic parameters for different profiles
     // Profile 1: Mobile referees (4 UEs) - 35 Mbps configured for guaranteed 5+ Mbps effective
     uint32_t udpPacketSizeReferees = 1000;  // Larger packets for mobile efficiency
     double targetRateMbpsReferees = refereeBitRate / 1e6;  // Use configurable referee bit rate
     
     // Profile 2: Static 4K cameras (10 UEs) - configurable Mbps video uplink only
     uint32_t udpPacketSizeCamera4K = 1000;  // Optimized packet size for 4K video
     double targetRateMbpsCamera4K = cameraBitRate / 1e6;   // Use configurable camera bit rate
     

    // Lambda calculations for new profiles
    uint32_t lambdaReferees = (targetRateMbpsReferees * 1e6) / (udpPacketSizeReferees * 8);
    uint32_t lambdaCamera4K = (targetRateMbpsCamera4K * 1e6) / (udpPacketSizeCamera4K * 8);
    

    std::cout << "\n=== STADIUM TRAFFIC PROFILES ===" << std::endl;
    std::cout << "Referees: " << targetRateMbpsReferees << " Mbps (" << lambdaReferees << " pkt/s)" << std::endl;
    std::cout << "4K Cameras: " << targetRateMbpsCamera4K << " Mbps (" << lambdaCamera4K << " pkt/s)" << std::endl;

    // Simulation parameters
    Time simTime = MilliSeconds(15000);  // 30 seconds for testing
    Time udpAppStartTime = MilliSeconds(300);  // Slightly increased startup delay for stability

    // NR parameters - optimized for stadium scenario
    uint16_t numerologyBwp1 = 1;  // 30 kHz SCS for good coverage and capacity balance
    double centralFrequencyBand1 = 3.7e9;
    double bandwidthBand1 = 100e6;  // 100 MHz for stadium scenario
    uint16_t numerologyBwp2 = 1;
    double centralFrequencyBand2 = 3.8e9;
    double bandwidthBand2 = 100e6;
    double totalTxPower = 0;  // 0 dBm

    std::string simTag = "Stadium_Handover_" + std::to_string(gNbNum) + "gNBs_" + std::to_string(ueNumPergNb*gNbNum) + "UEs";
    std::string outputDir = "./";

    // ========== COMMAND LINE ==========
 
     /*
      * From here, we instruct the ns3::CommandLine class of all the input parameters
      * that we may accept as input, as well as their description, and the storage
      * variable.
      */
     CommandLine cmd(__FILE__);
 
     cmd.AddValue("gNbNum", "The number of gNbs in multiple-ue topology", gNbNum);
     cmd.AddValue("ueNumPergNb", "The number of UE per gNb in multiple-ue topology", ueNumPergNb);
     cmd.AddValue("logging", "Enable logging", logging);
     cmd.AddValue("doubleOperationalBand",
                  "If true, simulate two operational bands with one CC for each band,"
                  "and each CC will have 1 BWP that spans the entire CC.",
                  doubleOperationalBand);
     cmd.AddValue("refereeBitRate", "Bit rate for referee video stream", refereeBitRate);
     cmd.AddValue("cameraBitRate", "Bit rate for 4K camera video stream", cameraBitRate);
     cmd.AddValue("simTime", "Simulation time", simTime);
     cmd.AddValue("numerologyBwp1", "The numerology to be used in bandwidth part 1", numerologyBwp1);
     cmd.AddValue("centralFrequencyBand1",
                  "The system frequency to be used in band 1",
                  centralFrequencyBand1);
     cmd.AddValue("bandwidthBand1", "The system bandwidth to be used in band 1", bandwidthBand1);
     cmd.AddValue("numerologyBwp2", "The numerology to be used in bandwidth part 2", numerologyBwp2);
     cmd.AddValue("centralFrequencyBand2",
                  "The system frequency to be used in band 2",
                  centralFrequencyBand2);
     cmd.AddValue("bandwidthBand2", "The system bandwidth to be used in band 2", bandwidthBand2);
     cmd.AddValue("totalTxPower",
                  "total tx power that will be proportionally assigned to"
                  " bands, CCs and bandwidth parts depending on each BWP bandwidth ",
                  totalTxPower);
     cmd.AddValue("simTag",
                  "tag to be appended to output filenames to distinguish simulation campaigns",
                  simTag);
     cmd.AddValue("outputDir", "directory where to store simulation results", outputDir);
 
     // Parse the command line
     cmd.Parse(argc, argv);

     // uint32_t lambdaVideo = (targetRateMbpsVideo * 1e6) / (udpPacketSizeVideo * 8); // Unused in current setup
 
     /*
      * Check if the frequency is in the allowed range.
      * If you need to add other checks, here is the best position to put them.
      */
     NS_ABORT_IF(centralFrequencyBand1 < 0.5e9 && centralFrequencyBand1 > 100e9);
     NS_ABORT_IF(centralFrequencyBand2 < 0.5e9 && centralFrequencyBand2 > 100e9);
 
     // ========== LOGGING ==========
     /*
      * If the logging variable is set to true, enable the log of some components
      * through the code. The same effect can be obtained through the use
      * of the NS_LOG environment variable:
      *
      * export NS_LOG="UdpClient=level_info|prefix_time|prefix_func|prefix_node:UdpServer=..."
      *
      * Usually, the environment variable way is preferred, as it is more customizable,
      * and more expressive.
      */
     if (logging)
     {
        // LogComponentEnable("UdpClient", LOG_LEVEL_INFO);
        // LogComponentEnable("UdpServer", LOG_LEVEL_INFO);
        // LogComponentEnable("NrPdcp", LOG_LEVEL_INFO);

         LogComponentEnable("NrUePhy", LOG_LEVEL_INFO); 
         LogComponentEnable("NrGnbRrc", LOG_LEVEL_INFO);
         LogComponentEnable("NrUeRrc", LOG_LEVEL_INFO);
         LogComponentEnable("NrA3RsrpHandoverAlgorithm", LOG_LEVEL_INFO);
     }
 
     // ========== GLOBAL CONFIGURATIONS ==========
     /*
      * In general, attributes for the NR module are typically configured in NrHelper.  However, some
      * attributes need to be configured globally through the Config::SetDefault() method. Below is
      * an example: if you want to make the RLC buffer very large, you can pass a very large integer
      * here.
      */
     Config::SetDefault("ns3::NrRlcUm::MaxTxBufferSize", UintegerValue(999999999));
     Config::SetDefault("ns3::NrEpsBearer::Release", UintegerValue(15)); // release 15
     Config::SetDefault("ns3::NrGnbMac::NumberOfRaPreambles", UintegerValue(64));  // Number of preambles available for RACH process
     
     // Correção: Configurações inválidas removidas - atributos não existem nesta versão do NR
     // Usando apenas configurações válidas e testadas
     
     // Enhanced scheduler configurations to handle high UE loads

     // Correção: Handover mais conservador para evitar falhas durante movimento
     Config::SetDefault("ns3::NrA3RsrpHandoverAlgorithm::Hysteresis", DoubleValue(3.0));  // Aumentado para 3.0 dB
     Config::SetDefault("ns3::NrA3RsrpHandoverAlgorithm::TimeToTrigger", TimeValue(MilliSeconds(256))); // Aumentado para 256ms
     
     // Enhanced RRC configurations for mobile UEs
     // Config::SetDefault("ns3::NrRrcProtocolReal::RrcConfigurationDelay", TimeValue(MilliSeconds(3))); // Commented out - not supported in this NS-3 version
     // Config::SetDefault("ns3::NrEpcX2::X2HandoverPreparationDelay", TimeValue(MilliSeconds(15))); // Commented out - not supported in this NS-3 version

     std::cout << "\n============ STADIUM SCENARIO WITH HANDOVER ============" << std::endl;
     std::cout << "- Configuration: " << gNbNum << " gNBs on catwalk" << std::endl;
     std::cout << "- Profile 1: 4 mobile referees (" << targetRateMbpsReferees << " Mbps video uplink)" << std::endl;
     std::cout << "- Profile 2: 10 static 4K cameras (" << targetRateMbpsCamera4K << " Mbps video uplink)" << std::endl;
     std::cout << "- Catwalk: radius=" << CATWALK_RADIUS << "m, height=" << CATWALK_HEIGHT << "m" << std::endl;
     std::cout << "- Field: radius=" << CAMPO_RADIUS << "m, referee speed=" << ARBITRO_SPEED << " m/s" << std::endl;
     std::cout << "- gNB Power: " << totalTxPower << " dBm (small cells)" << std::endl;
     std::cout << "=========================================================" << std::endl;
     


     
    // ========== NODE CREATION ==========
    NodeContainer gnbNodes;
    gnbNodes.Create(gNbNum);
    
    // Profile 1: Mobile referees (4 UEs)
    NodeContainer refereeNodes;
    refereeNodes.Create(4); // place to insert how much UE HD 5 Mbps

    refereeNodeIds.clear();
    for (uint32_t i = 0; i < refereeNodes.GetN(); ++i)
    {
        uint32_t nodeId = refereeNodes.Get(i)->GetId();
        refereeNodeIds.insert(nodeId);
        lastRefereeActivityTime[nodeId] = 0.0; // inicializa com tempo 0
    }
    
    // Profile 2: Static 4K cameras (10 UEs)
    NodeContainer camera4kNodes;
    camera4kNodes.Create(10); // place to insert how much UE 4K 35 Mbps
    
    // Combined UE container for compatibility
    NodeContainer ueNodes;
    ueNodes.Add(refereeNodes);
    ueNodes.Add(camera4kNodes);
    
    std::cout << "Created " << refereeNodes.GetN() << " referee nodes and " 
              << camera4kNodes.GetN() << " 4K camera nodes" << std::endl;

    // ========== MOBILITY - STADIUM SCENARIO ==========
    
    // 1. gNBs on catwalk (fixed circular positions)
    MobilityHelper gnbMobility;
    gnbMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    gnbMobility.Install(gnbNodes);

    for (uint32_t i = 0; i < gNbNum; ++i)
    {
        double angle = (i * 2.0 * M_PI) / gNbNum;
        double x = CATWALK_RADIUS * cos(angle);
        double y = CATWALK_RADIUS * sin(angle);
        
        Ptr<MobilityModel> mobility = gnbNodes.Get(i)->GetObject<MobilityModel>();
        mobility->SetPosition(Vector(x, y, CATWALK_HEIGHT));
        
        std::cout << "gNB " << i << ": (" << x << ", " << y << ", " << CATWALK_HEIGHT << ")" << std::endl;
    }
    
    std::cout << "Traffic Config - Referees: " << refereeBitRate/1000000.0 << "Mbps, Cameras: " << cameraBitRate/1000000.0 << "Mbps" << std::endl;

    // 2. Profile 1: Mobile referees - circular movement in field center
    MobilityHelper refereeMobility;
    refereeMobility.SetMobilityModel("ns3::ConstantVelocityMobilityModel");
    refereeMobility.Install(refereeNodes);

    std::cout << "\n=== PROFILE 1: Mobile Referees (" << targetRateMbpsReferees << " Mbps video uplink) ===" << std::endl;
    for (uint32_t i = 0; i < refereeNodes.GetN(); ++i)
    {
        double angle = (i * 2.0 * M_PI) / refereeNodes.GetN();
        double x = CAMPO_RADIUS * cos(angle);
        double y = CAMPO_RADIUS * sin(angle);
        
        Ptr<MobilityModel> mobility = refereeNodes.Get(i)->GetObject<MobilityModel>();
        mobility->SetPosition(Vector(x, y, ARBITRO_HEIGHT));
        
        std::cout << "Referee " << i << ": (" << x << ", " << y << ", " << ARBITRO_HEIGHT << ") - Mobile" << std::endl;
        
        // Correção: Escalonar o início do movimento de cada árbitro (offset de 125ms)
        // Isso evita que todos os árbitros atualizem posição simultaneamente
        double startTime = 0.8 + (i * 0.125);  // 0.8s, 0.925s, 1.05s, 1.175s
        Simulator::Schedule(Seconds(startTime), &MoveArbitroCircular, refereeNodes.Get(i), i);
        std::cout << "  -> Movimento iniciará em t=" << startTime << "s" << std::endl;
    }
    
    // 3. Profile 2: Static 4K cameras - fixed positions around field perimeter
    MobilityHelper camera4kMobility;
    camera4kMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    camera4kMobility.Install(camera4kNodes);
    
    // Predefined 4K camera positions (10 positions)
    std::vector<Vector> cameraPositions = {
        Vector(40, 60, 2.5),    Vector(60, 60, 2.5),  // Vector(80, 60, 2.5),
        Vector(-30, 60, 2.5),  Vector(-70, 60, 2.5), // Vector(-80, 60, 2.5),
        Vector(-90, -20, 2.5),   Vector(80, -20, 2.5),   // Vector(80, -60, 2.5),
        Vector(80, -60, 2.5),  Vector(40, -60, 2.5),  Vector(-40, -60, 2.5),
        Vector(-80, -60, 2.5)
    };
    
    std::cout << "\n=== PROFILE 2: Static 4K Cameras (" << targetRateMbpsCamera4K << " Mbps video uplink) ===" << std::endl;
    for (uint32_t i = 0; i < camera4kNodes.GetN() && i < cameraPositions.size(); ++i)
    {
        Ptr<MobilityModel> mobility = camera4kNodes.Get(i)->GetObject<MobilityModel>();
        mobility->SetPosition(cameraPositions[i]);
        
        std::cout << "4K Camera " << i << ": (" << cameraPositions[i].x << ", " 
                  << cameraPositions[i].y << ", " << cameraPositions[i].z << ") - Static" << std::endl;
    }

     // ========== CORE NETWORK ==========

    /*
      * Setup the NR module. We create the various helpers needed for the
      * NR simulation:
      * - nrEpcHelper, which will setup the core network
      * - IdealBeamformingHelper, which takes care of the beamforming part
      * - NrHelper, which takes care of creating and connecting the various
      * part of the NR stack
      */
     Ptr<NrPointToPointEpcHelper> nrEpcHelper = CreateObject<NrPointToPointEpcHelper>();
     Ptr<IdealBeamformingHelper> idealBeamformingHelper = CreateObject<IdealBeamformingHelper>();
     Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();
 
     // Put the pointers inside nrHelper
     nrHelper->SetBeamformingHelper(idealBeamformingHelper);
     nrHelper->SetEpcHelper(nrEpcHelper);
     nrHelper->SetSchedulerTypeId(TypeId::LookupByName("ns3::NrMacSchedulerOfdmaQos"));
     nrHelper->SetHandoverAlgorithmType("ns3::NrA3RsrpHandoverAlgorithm");
     
     // Enhanced configurations for mobile UEs (referees)
     nrHelper->SetUePhyAttribute("TxPower", DoubleValue(23.0));  // Higher UE power for mobile nodes
     nrHelper->SetUePhyAttribute("NoiseFigure", DoubleValue(5.0));  // Optimized noise figure
     
     // Enhanced configurations for better handover performance
     nrHelper->SetGnbPhyAttribute("TxPower", DoubleValue(0.0));
     nrHelper->SetGnbPhyAttribute("NoiseFigure", DoubleValue(5.0));
     
     // Scheduler attributes to prioritize mobile traffic
     nrHelper->SetSchedulerAttribute("FixedMcsDl", BooleanValue(false));
     nrHelper->SetSchedulerAttribute("FixedMcsUl", BooleanValue(false));
     
     std::cout << "\n--- Stadium scenario configured with NrMacSchedulerOfdmaQos (for 5QI Mechanism) ---" << std::endl;
     std::cout << "--- Enhanced mobile UE support enabled ---" << std::endl;


         // --- CORE NETWORK CREATION AND POSITIONING BLOCK START ---

     // 1. Get PGW and SGW nodes from helper
     Ptr<Node> pgw = nrEpcHelper->GetPgwNode();
     Ptr<Node> sgw = nrEpcHelper->GetSgwNode();

     // 2. Create nodes for Remote Host and MME
     NodeContainer remoteHostContainer;
     remoteHostContainer.Create(1);
     Ptr<Node> remoteHost = remoteHostContainer.Get(0);
     
     NodeContainer mmeContainer;
     mmeContainer.Create(1);
     Ptr<Node> mme = mmeContainer.Get(0);

     // 3. Install internet stack on Remote Host
     InternetStackHelper internet;
     internet.Install(remoteHostContainer);

     // 4. Group all core network nodes in a single container
     NodeContainer coreNodes;
     coreNodes.Add(pgw);
     coreNodes.Add(sgw);
     coreNodes.Add(remoteHost);
     coreNodes.Add(mme);

     // 5. Install mobility on all core network nodes at once
     MobilityHelper coreMobility;
     coreMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
     coreMobility.Install(coreNodes);

     // 6. Define exact position of each node at MPU
     sgw->GetObject<MobilityModel>()->SetPosition(Vector(240.0, -120.0, 0.0));
     pgw->GetObject<MobilityModel>()->SetPosition(Vector(240.0, -130.0, 0.0));
     remoteHost->GetObject<MobilityModel>()->SetPosition(Vector(240.0, -140.0, 0.0));
     mme->GetObject<MobilityModel>()->SetPosition(Vector(240.0, -150.0, 0.0));

/*     // 7. Fix Node 22 to remove warning to NetAnim
     Ptr<Node> node22 = ns3::NodeContainer::GetGlobal().Get(22);
     Ptr<ConstantPositionMobilityModel> mobModel22 = CreateObject<ConstantPositionMobilityModel>();
     mobModel22->SetPosition(mme->GetObject<MobilityModel>()->GetPosition()); // Mesma posição do MME
     node22->AggregateObject(mobModel22);  
*/


     // --- CORE NETWORK CREATION AND POSITIONING BLOCK END ---

    // --- MOBILITY BLOCK END ---


    std::cout << "\n=== gNB Positions ===" << std::endl;
    std::vector<Vector> gnbPositions;
    for (uint32_t i = 0; i < gnbNodes.GetN(); ++i)
    {
        Ptr<Node> gnb = gnbNodes.Get(i);
        Ptr<MobilityModel> mob = gnb->GetObject<MobilityModel>();
        Vector pos = mob->GetPosition();
        gnbPositions.push_back(pos);
        std::cout << "gNB " << i << ": (" << pos.x << ", " << pos.y << ", " << pos.z << ")" << std::endl;
    }

    std::cout << "\n=== UE Positions and Associated gNB ===" << std::endl;
    for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
    {
        Ptr<Node> ue = ueNodes.Get(i);
        Ptr<MobilityModel> mob = ue->GetObject<MobilityModel>();
        Vector uePos = mob->GetPosition();

        // Find the closest gNB
        double minDist = std::numeric_limits<double>::max();
        int gnbIndex = -1;
        for (uint32_t j = 0; j < gnbPositions.size(); ++j)
        {
            double dist = std::sqrt(
                std::pow(uePos.x - gnbPositions[j].x, 2) +
                std::pow(uePos.y - gnbPositions[j].y, 2) +
                std::pow(uePos.z - gnbPositions[j].z, 2));
            if (dist < minDist)
            {
                minDist = dist;
                gnbIndex = j;
            }
        }

        std::cout << "UE " << i << ": (" << uePos.x << ", " << uePos.y << ", " << uePos.z
                << ") -> gNB " << gnbIndex << std::endl;
    }


    
 

 /*
  * Create four different NodeContainer for the different traffic types.
  * In ueVoiceContainer we will put the UEs that will receive the voice traffic,
  * in ueVideoContainer the UEs for video traffic,
  * in ueLowLatContainer the UEs for low-latency traffic,
  * and in ueBestEffContainer the UEs for best-effort traffic.
  */
 NodeContainer ueVoiceContainer;
 NodeContainer ueVideoContainer;
 NodeContainer ueLowLatContainer;
 NodeContainer ueBestEffContainer;

// Stadium scenario: ALL UEs use VIDEO 5QI (referees and 4K cameras)
// Profile 1: Mobile referees (4 UEs) - 5 Mbps video uplink
for (uint32_t j = 0; j < refereeNodes.GetN(); ++j)
{
    ueVideoContainer.Add(refereeNodes.Get(j));
}

// Profile 2: Static 4K cameras (10 UEs) - 35 Mbps video uplink  
for (uint32_t j = 0; j < camera4kNodes.GetN(); ++j)
{
    ueVideoContainer.Add(camera4kNodes.Get(j));
}

std::cout << "\n=== SERVICE DISTRIBUTION ====" << std::endl;
std::cout << "All UEs using VIDEO 5QI (GBR_CONV_VIDEO):" << std::endl;
std::cout << "- Referees: " << refereeNodes.GetN() << " UEs @ " << targetRateMbpsReferees << " Mbps" << std::endl;
std::cout << "- 4K Cameras: " << camera4kNodes.GetN() << " UEs @ " << targetRateMbpsCamera4K << " Mbps" << std::endl;

 NS_LOG_UNCOND("UEs Voice: " << ueVoiceContainer.GetN());
 NS_LOG_UNCOND("UEs Video: " << ueVideoContainer.GetN() << " (All stadium UEs)");
 NS_LOG_UNCOND("UEs LowLat: " << ueLowLatContainer.GetN());
 NS_LOG_UNCOND("UEs BestEff: " << ueBestEffContainer.GetN());



 
     /*
      * TODO: Add a print, or a plot, that shows the scenario.
      */
     NS_LOG_INFO("Creating " << ueNodes.GetN() << " user terminals and "
                             << gnbNodes.GetN() << " gNBs");

     /*
      * Spectrum division. We create two operational bands, each of them containing
      * one component carrier, and each CC containing a single bandwidth part
      * centered at the frequency specified by the input parameters.
      * Each spectrum part length is, as well, specified by the input parameters.
      * Both operational bands will use the StreetCanyon channel modeling.
      */
     BandwidthPartInfoPtrVector allBwps;
     CcBwpCreator ccBwpCreator;
     const uint8_t numCcPerBand = 1; // in this example, both bands have a single CC
 
     // Create the configuration for the CcBwpHelper. SimpleOperationBandConf creates
     // a single BWP per CC
     CcBwpCreator::SimpleOperationBandConf bandConf1(centralFrequencyBand1,
                                                     bandwidthBand1,
                                                     numCcPerBand,
                                                     BandwidthPartInfo::UMi_StreetCanyon);
     CcBwpCreator::SimpleOperationBandConf bandConf2(centralFrequencyBand2,
                                                     bandwidthBand2,
                                                     numCcPerBand,
                                                     BandwidthPartInfo::UMi_StreetCanyon);
 
     // By using the configuration created, it is time to make the operation bands
     OperationBandInfo band1 = ccBwpCreator.CreateOperationBandContiguousCc(bandConf1);
     OperationBandInfo band2 = ccBwpCreator.CreateOperationBandContiguousCc(bandConf2);





// ...continue normally with device installation...
 
     /*
      * The configured spectrum division is:
      * ------------Band1--------------|--------------Band2-----------------
      * ------------CC1----------------|--------------CC2-------------------
      * ------------BWP1---------------|--------------BWP2------------------
      */
 
     /*
      * Attributes of ThreeGppChannelModel still cannot be set in our way.
      * TODO: Coordinate with Tommaso
      */
     Config::SetDefault("ns3::ThreeGppChannelModel::UpdatePeriod", TimeValue(MilliSeconds(0)));
     nrHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
     nrHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(false));
 
     /*
      * Initialize channel and pathloss, plus other things inside band1. If needed,
      * the band configuration can be done manually, but we leave it for more
      * sophisticated examples. For the moment, this method will take care
      * of all the spectrum initialization needs.
      */
     nrHelper->InitializeOperationBand(&band1);
 
     /*
      * Start to account for the bandwidth used by the example, as well as
      * the total power that has to be divided among the BWPs.
      */
     double x = pow(10, totalTxPower / 10);
     double totalBandwidth = bandwidthBand1;
 
     /*
      * if not single band simulation, initialize and setup power in the second band
      */
     if (doubleOperationalBand)
     {
         // Initialize channel and pathloss, plus other things inside band2
         nrHelper->InitializeOperationBand(&band2);
         totalBandwidth += bandwidthBand2;
         allBwps = CcBwpCreator::GetAllBwps({band1, band2});
     }
     else
     {
         allBwps = CcBwpCreator::GetAllBwps({band1});
     }
 
     /*
      * allBwps contains all the spectrum configuration needed for the nrHelper.
      *
      * Now, we can setup the attributes. We can have three kind of attributes:
      * (i) parameters that are valid for all the bandwidth parts and applies to
      * all nodes, (ii) parameters that are valid for all the bandwidth parts
      * and applies to some node only, and (iii) parameters that are different for
      * every bandwidth parts. The approach is:
      *
      * - for (i): Configure the attribute through the helper, and then install;
      * - for (ii): Configure the attribute through the helper, and then install
      * for the first set of nodes. Then, change the attribute through the helper,
      * and install again;
      * - for (iii): Install, and then configure the attributes by retrieving
      * the pointer needed, and calling "SetAttribute" on top of such pointer.
      *
      */
 
     Packet::EnableChecking();
     Packet::EnablePrinting();
 
     /*
      *  Case (i): Attributes valid for all the nodes
      */
     // Beamforming method
     idealBeamformingHelper->SetAttribute("BeamformingMethod",
                                          TypeIdValue(DirectPathBeamforming::GetTypeId()));
 
     // Core latency
     nrEpcHelper->SetAttribute("S1uLinkDelay", TimeValue(MilliSeconds(0)));
 
     // Antennas for all the UEs
     nrHelper->SetUeAntennaAttribute("NumRows", UintegerValue(2));
     nrHelper->SetUeAntennaAttribute("NumColumns", UintegerValue(4));
     nrHelper->SetUeAntennaAttribute("AntennaElement",
                                     PointerValue(CreateObject<IsotropicAntennaModel>()));
 
     // Antennas for all the gNbs
     nrHelper->SetGnbAntennaAttribute("NumRows", UintegerValue(4));
     nrHelper->SetGnbAntennaAttribute("NumColumns", UintegerValue(8));
     nrHelper->SetGnbAntennaAttribute("AntennaElement",
                                      PointerValue(CreateObject<IsotropicAntennaModel>()));
 
    uint32_t bwpIdForVoice = 0;
    uint32_t bwpIdForVideo = 0;
    uint32_t bwpIdForLowLat = 0;
    uint32_t bwpIdForBestEff = 0;

    
     if (doubleOperationalBand)
     {
         bwpIdForVoice = 1;
         bwpIdForVideo = 0;
         bwpIdForLowLat = 1;
         bwpIdForBestEff = 1;
     }
 
     // gNb routing between Bearer and bandwidh part
     nrHelper->SetGnbBwpManagerAlgorithmAttribute("GBR_CONV_VOICE", UintegerValue(bwpIdForVoice));
     nrHelper->SetGnbBwpManagerAlgorithmAttribute("GBR_CONV_VIDEO", UintegerValue(bwpIdForVideo));
     nrHelper->SetGnbBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(bwpIdForLowLat));
     nrHelper->SetGnbBwpManagerAlgorithmAttribute("NGBR_VIDEO_TCP_DEFAULT", UintegerValue(bwpIdForBestEff));
   
 
     // Ue routing between Bearer and bandwidth part
     nrHelper->SetUeBwpManagerAlgorithmAttribute("GBR_CONV_VOICE", UintegerValue(bwpIdForVoice));
     nrHelper->SetUeBwpManagerAlgorithmAttribute("GBR_CONV_VIDEO", UintegerValue(bwpIdForVideo));
     nrHelper->SetUeBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(bwpIdForLowLat));
     nrHelper->SetUeBwpManagerAlgorithmAttribute("NGBR_VIDEO_TCP_DEFAULT", UintegerValue(bwpIdForBestEff));
 
 
     /*
      * We miss many other parameters. By default, not configuring them is equivalent
      * to use the default values. Please, have a look at the documentation to see
      * what are the default values for all the attributes you are not seeing here.
      */
 
     /*
      * Case (ii): Attributes valid for a subset of the nodes
      */
 
     // NOT PRESENT IN THIS SIMPLE EXAMPLE
 
     /*
      * We have configured the attributes we needed. Now, install and get the pointers
      * to the NetDevices, which contains all the NR stack:
      */
 
 NetDeviceContainer gnbNetDev =
     nrHelper->InstallGnbDevice(gnbNodes, allBwps);
 NetDeviceContainer ueVoiceNetDev = nrHelper->InstallUeDevice(ueVoiceContainer, allBwps);
 NetDeviceContainer ueVideoNetDev = nrHelper->InstallUeDevice(ueVideoContainer, allBwps);
 NetDeviceContainer ueLowLatNetDev = nrHelper->InstallUeDevice(ueLowLatContainer, allBwps);
 NetDeviceContainer ueBestEffNetDev = nrHelper->InstallUeDevice(ueBestEffContainer, allBwps);

 int64_t randomStream = 1;
 randomStream += nrHelper->AssignStreams(gnbNetDev, randomStream);
 randomStream += nrHelper->AssignStreams(ueVoiceNetDev, randomStream); // 5QI = 1
 randomStream += nrHelper->AssignStreams(ueVideoNetDev, randomStream);  // 5QI = 2
 randomStream += nrHelper->AssignStreams(ueLowLatNetDev, randomStream); // 5QI = 7
 randomStream += nrHelper->AssignStreams(ueBestEffNetDev, randomStream); // 5QI = 9
 


/*
 
     // --- START OF DYNAMIC GNB CONFIGURATION BLOCK ---

    std::cout << "\n--- Configurando Padrão TDD para todas as gNBs ---" << std::endl;
    // BWP0, the TDD one - Aplicado a TODAS as gNBs
    for (uint32_t i = 0; i < gnbNetDev.GetN(); ++i)
    {
        nrHelper->GetGnbPhy(gnbNetDev.Get(i), 0)
            ->SetAttribute("Pattern", StringValue("DL|DL|UL|S|UL|UL|UL|UL|S|UL"));
    }
    std::cout << "Padrão TDD 'DL|DL|UL|S|UL|UL|UL|UL|S|UL' aplicado a " << gnbNetDev.GetN() << " gNBs." << std::endl;
    std::cout << "-------------------------------------------------" << std::endl;

*/


    // --- END OF DYNAMIC GNB CONFIGURATION BLOCK ---

     // Case (iii): Go node for node and change the attributes we have to setup
     // per-node.
 
     // Get the first netdevice (gnbNetDev.Get (0)) and the first bandwidth part (0)
     // and set the attribute.
     nrHelper->GetGnbPhy(gnbNetDev.Get(0), 0)
         ->SetAttribute("Numerology", UintegerValue(numerologyBwp1));
     nrHelper->GetGnbPhy(gnbNetDev.Get(0), 0)
         ->SetAttribute("TxPower", DoubleValue(10 * log10((bandwidthBand1 / totalBandwidth) * x)));
 
     if (doubleOperationalBand)
     {
         // Get the first netdevice (gnbNetDev.Get (0)) and the second bandwidth part (1)
         // and set the attribute.
         nrHelper->GetGnbPhy(gnbNetDev.Get(0), 1)
             ->SetAttribute("Numerology", UintegerValue(numerologyBwp2));
         nrHelper->GetGnbPhy(gnbNetDev.Get(0), 1)
             ->SetTxPower(10 * log10((bandwidthBand2 / totalBandwidth) * x));
     }
 
     // When all the configuration is done, explicitly call UpdateConfig ()
     // Instead of calling individually for each netDevice, we can call
     // NrHelper::UpdateDeviceConfigs() to update a NetDeviceContainer with a single call. This was
     // introduced with the v.3.2 Release.
    nrHelper->UpdateDeviceConfigs(gnbNetDev);
    nrHelper->UpdateDeviceConfigs(ueVoiceNetDev);
    nrHelper->UpdateDeviceConfigs(ueVideoNetDev);
    nrHelper->UpdateDeviceConfigs(ueLowLatNetDev);
    nrHelper->UpdateDeviceConfigs(ueBestEffNetDev);
 
     // From here, it is standard NS3. In the future, we will create helpers
     // for this part as well.

 
     // connect a remoteHost to pgw. Setup routing too
     PointToPointHelper p2ph;

     // p2ph.EnablePcapAll("nr-udp-traffic");
     // If you want to enable pcap for a specific device, use gnbNetDev or another defined NetDeviceContainer
     // Example: p2ph.EnablePcap("nr-udp-traffic", gnbNetDev.Get(0), true);
     // p2ph.EnablePcap("nr-udp-traffic", gnbNetDev.Get(0), true);
     // p2ph.EnablePcap("nr-udp-traffic", ueVoiceNetDev.Get(0), true);
     // p2ph.EnablePcap("nr-udp-traffic", ueVideoNetDev.Get(0), true);
     // p2ph.EnablePcap("nr-udp-traffic", ueLowLatNetDev.Get(0), true);
     // p2ph.EnablePcap("nr-udp-traffic", ueBestEffNetDev.Get(0), true);


     p2ph.SetDeviceAttribute("DataRate", DataRateValue(DataRate("100Gb/s")));
     p2ph.SetDeviceAttribute("Mtu", UintegerValue(2500));
     p2ph.SetChannelAttribute("Delay", TimeValue(Seconds(0.000)));
     NetDeviceContainer internetDevices = p2ph.Install(pgw, remoteHost);
     Ipv4AddressHelper ipv4h;
     Ipv4StaticRoutingHelper ipv4RoutingHelper;
     ipv4h.SetBase("1.0.0.0", "255.0.0.0");
     Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign(internetDevices);
     Ptr<Ipv4StaticRouting> remoteHostStaticRouting =
         ipv4RoutingHelper.GetStaticRouting(remoteHost->GetObject<Ipv4>());
     remoteHostStaticRouting->AddNetworkRouteTo(Ipv4Address("7.0.0.0"), Ipv4Mask("255.0.0.0"), 1);
     internet.Install(ueNodes);
 
    Ipv4InterfaceContainer ueVoiceIpIface =
        nrEpcHelper->AssignUeIpv4Address(NetDeviceContainer(ueVoiceNetDev));
    Ipv4InterfaceContainer ueVideoIpIface =
        nrEpcHelper->AssignUeIpv4Address(NetDeviceContainer(ueVideoNetDev));
    Ipv4InterfaceContainer ueLowLatIpIface =
        nrEpcHelper->AssignUeIpv4Address(NetDeviceContainer(ueLowLatNetDev));
    Ipv4InterfaceContainer ueBestEffIpIface =
        nrEpcHelper->AssignUeIpv4Address(NetDeviceContainer(ueBestEffNetDev));






     /*
     
                    RemoteHost
                    |
                    | (Point-to-Point)
                    |
         PGW/SGW 4G<|>5G UPF/AMF
                    |
                    | (Logical Connection)
                    |
                  gNB1 
                    |         
                   UE1 - CONV VOICE - 5QI = 1
                   UE2 - CONV VIDEO - 5QI = 2
                   UE3 - U_LOW_LAT  - 5QI = 7
                   UE4 - Best_Eff   - 5QI = 9      
                    



      +-----------------------------------------------------------------+
      |                      Football Stadium                           |
      |                                                                 |
      |      ***************** Catwalk (Height: 25m) ***************    |
      |      *                                                     *    | 
      |      *           gNB 2 o                   o gNB 1         *    |
      |      *                                                     *    |
      |      *                                                     *    |
      |      *           Football Field                            *    |   
      |      *                                                     *    |
      |      * gNB 3 o                             UE 0    o gNB 0 *    |
      |      *                                                     *    |
      |      *                       UE 2                          *    |
      |      *              UE 3                                   *    |
      |      *                                                     *    |
      |      *                                                     *    |
      |      *           gNB 4 o                 o gNB 5           *    |
      |      *                                                     *    |
      |      *******************************************************    |
      |                                                                 |
      +-----------------------------------------------------------------+
                               |
                               | (Backhaul / Xn Connection between gNBs)
                               |
                      +------------------+
                      | 5G/EPC Core Network |
                      +------------------+



        ^ Signal Strength (RSRP)
      |
      | Neighbor Cell Signal (B) -------------------- /
      |                                           /
      |                                          /
      |--- Current Cell Signal (A) ---\-----------/--- POINT WHERE A3 EVENT IS TRIGGERED
      |                            | \         /    (Sinal B > Sinal A + Histerese)
      |                            |  \       /
      |                Histerese ->{   \     /
      |                            |    \   /
      |                            |     \ / <--- Ponto onde os sinais se cruzam
      |                            |      X
      |                           /      / \
      |                          /      /   \
      |                         /      /     \
      +------------------------------------------------------------> Time / Distance
      

     
     
     */
 

     Packet::EnablePrinting();

     
     // Set the default gateway for the UEs
     for (uint32_t j = 0; j < ueNodes.GetN(); ++j)
     {
         Ptr<Ipv4StaticRouting> ueStaticRouting = ipv4RoutingHelper.GetStaticRouting(
             ueNodes.Get(j)->GetObject<Ipv4>());
         ueStaticRouting->SetDefaultRoute(nrEpcHelper->GetUeDefaultGatewayAddress(), 1);
     }
 
      // attach UEs to the closest gNB
    nrHelper->AttachToClosestGnb(ueVoiceNetDev, gnbNetDev);
    nrHelper->AttachToClosestGnb(ueVideoNetDev, gnbNetDev);
    nrHelper->AttachToClosestGnb(ueLowLatNetDev, gnbNetDev);
    nrHelper->AttachToClosestGnb(ueBestEffNetDev, gnbNetDev);
 

    // ========== VALIDATION CELL ==========
    std::cout << "\n--- Verificando a Célula (gNB) de Anexação Inicial dos UEs ---" << std::endl;
    for (uint32_t i = 0; i < ueVideoNetDev.GetN(); ++i)
    {
        Ptr<NetDevice> ueDev = ueVideoNetDev.Get(i);
        Ptr<NrUeNetDevice> nrUeDev = DynamicCast<NrUeNetDevice>(ueDev);
        if (nrUeDev)
        {
            // Correção: Obter o CellId do RRC do UE
            Ptr<NrUeRrc> ueRrc = nrUeDev->GetRrc();
            uint16_t servingCellId = ueRrc->GetCellId();
            
            Ptr<NrGnbNetDevice> servingGnb = nullptr;
            // Encontrar a gNB que corresponde ao CellId
            for (uint32_t j = 0; j < gnbNetDev.GetN(); ++j)
            {
                Ptr<NrGnbNetDevice> gnbDev = DynamicCast<NrGnbNetDevice>(gnbNetDev.Get(j));
                if (gnbDev && gnbDev->GetCellId() == servingCellId)
                {
                    servingGnb = gnbDev;
                    break;
                }
            }

            if (servingGnb)
            {
                std::cout << "UE " << ueDev->GetNode()->GetId() 
                          << " (Tipo: " << (i < 4 ? "Árbitro" : "Câmera") << ")"
                          << " anexado à gNB " << servingGnb->GetNode()->GetId() 
                          << " (CellId: " << servingCellId << ")" << std::endl;

                if (refereeNodeIds.find(ueDev->GetNode()->GetId()) != refereeNodeIds.end())
                {
                    lastRefereeActivityTime[ueDev->GetNode()->GetId()] = Simulator::Now().GetSeconds();
                }
            }
            else
            {
                std::cout << "UE " << ueDev->GetNode()->GetId() << " não conseguiu se anexar a nenhuma gNB." << std::endl;
            }
        }
    }
    std::cout << "----------------------------------------------------------" << std::endl;



     /*
      * Traffic part. Install two kind of traffic: low-latency and voice, each
      * identified by a particular source port.
      */
    // #################################################################
    // ### APPLICATION AND BEARER INSTALLATION START              ###
    // #################################################################

    // Old service-based port configuration (commented out - unused)
    // uint16_t dlPortVoice = 1111, ulPortVoice = 2221;
    // uint16_t dlPortVideo = 1112, ulPortVideo = 2222;
    // uint16_t dlPortLowLat = 1117, ulPortLowLat = 2227;
    // uint16_t dlPortBestEff = 1119, ulPortBestEff = 2229;

   ApplicationContainer serverApps, clientApps;

    // --- UPLINK ONLY SERVER INSTALLATION ---
    // All traffic is uplink (UEs -> RemoteHost), so servers only on RemoteHost
    uint16_t ulPortRefereesVideo = 2221;   // Referees video uplink (5 Mbps)
    uint16_t ulPortCamera4kVideo = 2222;   // 4K cameras video uplink (35 Mbps)
    
    // Uplink video servers for both profiles
    serverApps.Add(UdpServerHelper(ulPortRefereesVideo).Install(remoteHost));
    serverApps.Add(UdpServerHelper(ulPortCamera4kVideo).Install(remoteHost));
    
    std::cout << "\n=== UPLINK-ONLY TRAFFIC CONFIGURATION ===" << std::endl;
    std::cout << "Referee video servers: Port " << ulPortRefereesVideo << std::endl;
    std::cout << "4K camera video servers: Port " << ulPortCamera4kVideo << std::endl;

    // --- UPLINK ONLY CLIENT CONFIGURATION ---
    
    // Video bearers with different priorities
    NrEpsBearer refereesBearer(NrEpsBearer::GBR_CONV_VIDEO);   // Higher priority for mobile referees
    NrEpsBearer cameraBearer(NrEpsBearer::GBR_CONV_VIDEO);     // Higher priority for cameras
    
    // Set critical priority for mobile referees (QCI 1) vs video priority for cameras (QCI 2)
    refereesBearer.qci = NrEpsBearer::GBR_CONV_VIDEO;  // QCI 2 - highest priority
    cameraBearer.qci = NrEpsBearer::GBR_CONV_VIDEO;    // QCI 2 - highest priority
    
    // QoS differentiation through QCI types only (NS-3 NR manages GBR/MBR internally)
    
    Ipv4Address remoteHostAddress = remoteHost->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
    
    std::cout << "RemoteHost IP: " << remoteHostAddress << std::endl;


    
    // --- PROFILE 1: MOBILE REFEREES UPLINK (5 Mbps video) ---
    std::cout << "\n=== Configuring Profile 1: Mobile Referees ===" << std::endl;
    for (uint32_t i = 0; i < refereeNodes.GetN(); ++i)
    {
        Ptr<NetDevice> ueDevice = ueVideoNetDev.Get(i); // First 4 devices are referees
        Ipv4Address ueAddress = ueVideoIpIface.GetAddress(i);

        // UPLINK Traffic (Referee -> RemoteHost) - 5 Mbps video
        UdpClientHelper ulClientReferee(remoteHostAddress, ulPortRefereesVideo);
        ulClientReferee.SetAttribute("MaxPackets", UintegerValue(0xFFFFFFFF));
        ulClientReferee.SetAttribute("PacketSize", UintegerValue(udpPacketSizeReferees));
        ulClientReferee.SetAttribute("Interval", TimeValue(Seconds(1.0 / lambdaReferees)));
        clientApps.Add(ulClientReferee.Install(refereeNodes.Get(i)));

        // TFT for uplink video bearer
        Ptr<NrEpcTft> ulTftReferee = Create<NrEpcTft>();
        NrEpcTft::PacketFilter ulpf;
        ulpf.direction = NrEpcTft::UPLINK;
        ulpf.remotePortStart = ulPortRefereesVideo;
        ulpf.remotePortEnd = ulPortRefereesVideo;
        ulTftReferee->Add(ulpf);
        nrHelper->ActivateDedicatedEpsBearer(ueDevice, refereesBearer, ulTftReferee);

        std::cout << "Referee " << i << " | IP: " << ueAddress << " | " << targetRateMbpsReferees << " Mbps uplink" << std::endl;
    }

    // --- PROFILE 2: STATIC 4K CAMERAS UPLINK (35 Mbps video) ---
    std::cout << "\n=== Configuring Profile 2: Static 4K Cameras ===" << std::endl;
    for (uint32_t i = 0; i < camera4kNodes.GetN(); ++i)
    {
        uint32_t videoIndex = refereeNodes.GetN() + i; // Cameras start after referees in video container
        Ptr<NetDevice> ueDevice = ueVideoNetDev.Get(videoIndex);
        Ipv4Address ueAddress = ueVideoIpIface.GetAddress(videoIndex);

        // UPLINK Traffic (4K Camera -> RemoteHost) - 35 Mbps video
        UdpClientHelper ulClient4K(remoteHostAddress, ulPortCamera4kVideo);
        ulClient4K.SetAttribute("MaxPackets", UintegerValue(0xFFFFFFFF));
        ulClient4K.SetAttribute("PacketSize", UintegerValue(udpPacketSizeCamera4K));
        ulClient4K.SetAttribute("Interval", TimeValue(Seconds(1.0 / lambdaCamera4K)));
        clientApps.Add(ulClient4K.Install(camera4kNodes.Get(i)));

        // TFT for uplink video bearer
        Ptr<NrEpcTft> ulTft4K = Create<NrEpcTft>();
        NrEpcTft::PacketFilter ulpf;
        ulpf.direction = NrEpcTft::UPLINK;
        ulpf.remotePortStart = ulPortCamera4kVideo;
        ulpf.remotePortEnd = ulPortCamera4kVideo;
        ulTft4K->Add(ulpf);
        nrHelper->ActivateDedicatedEpsBearer(ueDevice, cameraBearer, ulTft4K);

        std::cout << "4K Camera " << i << " | IP: " << ueAddress << " | " << targetRateMbpsCamera4K << " Mbps uplink" << std::endl;
    }

    // --- DUPLICATE CAMERA CONFIGURATION REMOVED ---
    // This section was creating duplicate flows for 4K cameras
    // Only the first camera configuration loop above is needed
    
    std::cout << "\n=== TRAFFIC CONFIGURATION SUMMARY ===" << std::endl;
    std::cout << "Referees (4): " << targetRateMbpsReferees << " Mbps each (HIGH PRIORITY - target: 10+ Mbps effective)" << std::endl;
    std::cout << "4K Cameras (10): " << targetRateMbpsCamera4K << " Mbps each (STANDARD PRIORITY)" << std::endl;
    std::cout << "Total configured uplink traffic: " << (4 * targetRateMbpsReferees + 10 * targetRateMbpsCamera4K) << " Mbps" << std::endl;
    std::cout << "Stadium coverage: 6 gNBs @ 33 dBm, 100 MHz bandwidth" << std::endl;
    std::cout << "Enhanced handover for mobile referees enabled" << std::endl;


    // ###############################################################
    // ### APPLICATION AND BEARER INSTALLATION END                  ###
    // ###############################################################
 

     // start UDP server and client apps
     serverApps.Start(udpAppStartTime);
     clientApps.Start(udpAppStartTime);


    // Add X2 interface for handover between gNBs
    nrHelper->AddX2Interface(gnbNodes);

    // Enhanced handover configuration for stadium scenario
    std::cout << "\n--- Configurando Interface X2 e Sistema de Handover ---" << std::endl;

    // Configure automatic reconnection system for mobile referees
    NetDeviceContainer allUeNetDevs;
    allUeNetDevs.Add(ueVideoNetDev);
    allUeNetDevs.Add(ueVoiceNetDev);
    allUeNetDevs.Add(ueLowLatNetDev); 
    allUeNetDevs.Add(ueBestEffNetDev);

    // DISABLED: Schedule reconnection monitoring system (causing issues)
    // Simulator::Schedule(Seconds(2.0), &CheckAndReconnectUes, nrHelper, allUeNetDevs, gnbNetDev, monitor, classifier);

    // Enable basic tracing for analysis
    if (traces)
    {
        nrHelper->EnableTraces(); // Use the available function
        // DISABLED: Advanced tracing functions not available in this NR version
        // nrHelper->EnableRlcTraces(); 
        // nrHelper->EnablePdcpTraces();
        
        std::cout << "Basic NR traces enabled" << std::endl;
    }

    // Connect NR-specific handover callbacks (already configured above)
    std::cout << "X2 interface habilitada entre " << gnbNodes.GetN() << " gNBs" << std::endl;
    std::cout << "Sistema de reconexão automática ativado para árbitros móveis" << std::endl;
    std::cout << "Callbacks de handover já conectados anteriormente" << std::endl;
    std::cout << "--------------------------------------------------------" << std::endl;

    // DISABLED: Schedule final statistics collection (causing compilation issues)
    // Simulator::Schedule(simTime - MilliSeconds(100), &PrintFinalStats);


     serverApps.Stop(simTime);
     clientApps.Stop(simTime);
 
     // enable the traces provided by the nr module
     if (traces)
     {
         nrHelper->EnableTraces();
     }
 
     FlowMonitorHelper flowmonHelper;
     NodeContainer endpointNodes;
     endpointNodes.Add(remoteHost);
     endpointNodes.Add(ueNodes);
 
     Ptr<ns3::FlowMonitor> monitor = flowmonHelper.Install(endpointNodes);
     monitor->SetAttribute("DelayBinWidth", DoubleValue(0.001));
     monitor->SetAttribute("JitterBinWidth", DoubleValue(0.001));
     monitor->SetAttribute("PacketSizeBinWidth", DoubleValue(20));

     Ptr<Ipv4FlowClassifier> classifier =
         DynamicCast<Ipv4FlowClassifier>(flowmonHelper.GetClassifier());
     Simulator::Schedule(Seconds(0.1), &TraceFlowMonitorStats, monitor, classifier);

    // ========== CRITICAL FIX: ENABLE BEARER CONTINUITY DURING HANDOVER ==========
    // This ensures that data bearers are maintained when UEs handover between gNBs
    // Without this, UEs lose their data connection after handover
    std::cout << "\n--- Habilitando Continuidade de Bearers Durante Handover ---" << std::endl;
    for (uint32_t i = 0; i < gnbNetDev.GetN(); ++i)
    {
        Ptr<NrGnbNetDevice> gnbDev = DynamicCast<NrGnbNetDevice>(gnbNetDev.Get(i));
        if (gnbDev)
        {
            Ptr<NrGnbRrc> rrc = gnbDev->GetRrc();
            // Enable automatic bearer setup for handover
            rrc->SetAttribute("AdmitHandoverRequest", BooleanValue(true));
            rrc->SetAttribute("AdmitRrcConnectionRequest", BooleanValue(true));
        }
    }
    std::cout << "Continuidade de bearers habilitada em todas as " << gnbNetDev.GetN() << " gNBs" << std::endl;
    std::cout << "---------------------------------------------------------------" << std::endl;


if (anim)
{     
    // --- ANIMATION BLOCK START ---
    AnimationInterface anim("handover_animation_15s.xml");
    anim.SetMaxPktsPerTraceFile(500000);
    anim.EnablePacketMetadata(true);
  
    // anim.EnableIpv4RouteTracking("routingtable-wireless.xml", Seconds(0), Seconds(10), Seconds(0.25)); // Opcional, se quiser ver rotas


    anim.SetBackgroundImage("/Users/carloshenriquelopes/ns-3-dev/scratch/icons/maracana.png", -365, -270, 0.6, 0.6, 1);

    uint32_t ueIcon = anim.AddResource("/Users/carloshenriquelopes/ns-3-dev/scratch/icons/cam.png");
    uint32_t gnbIcon = anim.AddResource("/Users/carloshenriquelopes/ns-3-dev/scratch/icons/gnb.png");
    uint32_t serverIcon = anim.AddResource("/Users/carloshenriquelopes/ns-3-dev/scratch/icons/remotehost.png");
    uint32_t mmeIcon = anim.AddResource("/Users/carloshenriquelopes/ns-3-dev/scratch/icons/mme.png");
    uint32_t pgwIcon = anim.AddResource("/Users/carloshenriquelopes/ns-3-dev/scratch/icons/pgw.png");
    uint32_t sgwIcon = anim.AddResource("/Users/carloshenriquelopes/ns-3-dev/scratch/icons/sgw.png");

    // Iterate over ALL gNBs to apply icon
    for (uint32_t i = 0; i < gnbNodes.GetN(); ++i)
    {
        anim.UpdateNodeImage(gnbNodes.Get(i)->GetId(), gnbIcon);
    }

    // Iterate over all UEs (already correct)
    for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
    {
        anim.UpdateNodeImage(ueNodes.Get(i)->GetId(), ueIcon);
    }

    anim.UpdateNodeImage(pgw->GetId(), sgwIcon);
    anim.UpdateNodeImage(sgw->GetId(), pgwIcon);
    anim.UpdateNodeImage(22, mmeIcon); // add icon to Node 22
    anim.UpdateNodeImage(mme->GetId(), mmeIcon);

    anim.UpdateNodeImage(remoteHost->GetId(), serverIcon);
 }

    // --- ANIMATION BLOCK END ---

     // Initialize tracking system for stadium handover
     std::cout << "\n--- Initializing handover tracking system ---" << std::endl;
     
     // Correção: Escalonar tracking para evitar medições simultâneas
     for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
     {
         // Cada UE tem seu tracking em momentos diferentes (offset de 100ms)
         double trackOffset = i * 0.1;
         Simulator::Schedule(Seconds(2.0 + trackOffset), &TrackUePosition, ueNodes.Get(i), i);
         Simulator::Schedule(Seconds(2.5 + trackOffset), &LogPowerAndHandover, ueNodes.Get(i), i, gnbNodes);
     }
     
     // Schedule periodic position reports
     Simulator::Schedule(Seconds(1.0), &PeriodicPositionReport, ueNodes);
 
     std::cout << "Tracking system activated for " << ueNodes.GetN() << " cameras" << std::endl;
     
     // ========== CONNECT HANDOVER CALLBACKS ==========
     std::cout << "\n--- Conectando Callbacks de Handover ---" << std::endl;
     Config::Connect("/NodeList/*/DeviceList/*/NrUeRrc/HandoverStart",
                     MakeCallback(&NotifyHandoverStartUe));
     Config::Connect("/NodeList/*/DeviceList/*/NrUeRrc/HandoverEndOk",
                     MakeCallback(&NotifyHandoverEndOkUe));
     std::cout << "Callbacks de handover conectados para monitoramento de continuidade" << std::endl;
     std::cout << "=========================================================" << std::endl;
 
     Simulator::Stop(simTime);
     Simulator::Run();
 
     /*
      * To check what was installed in the memory, i.e., BWPs of gNB Device, and its configuration.
      * Example is: Node 1 -> Device 0 -> BandwidthPartMap -> {0,1} BWPs -> NrGnbPhy -> Numerology,
     GtkConfigStore config;
     config.ConfigureAttributes ();
     */
 
     // Print per-flow statistics
     monitor->CheckForLostPackets();
     FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();
 
     double averageFlowThroughput = 0.0;
     double averageFlowDelay = 0.0;
     double averageFlowJitter = 0.0;
     double totalChannelTime = simTime.GetSeconds(); // Total simulation time
     double channelBusyTime = 0.0; // Accumulated time that channel is busy
 
     for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin();
     i != stats.end();
     ++i)
     {
        double dataRate = 76e6; // Channel transmission rate (in bps, adjust as needed) 76 Mb/s
        // double dataRate = (gNbNum * ueNumPergNb * targetRateMbpsVideo * 1e6) + (gNbNum * ueNumPergNb * targetRateMbpsBe * 1e6) + (gNbNum * ueNumPergNb * targetRateMbpsULL * 1e6); // Channel transmission rate (in bps, adjust as needed)


        // Calculate busy time on channel for this flow
        double busyTime = (i->second.rxBytes * 8.0) / dataRate; // Busy time in seconds
        channelBusyTime += busyTime;
    }
       
     double channelUtilization = (channelBusyTime / totalChannelTime) * 100.0;
     std::cout << " \n\n Output: \n\n\n - 1.0.0.2 (gNB) > 7.0.0.x (UE) - Downlink \n - 7.0.0.x (UE) > 1.0.0.2 (gNB) - Uplink \n\n" << std::endl;
    

     std::ofstream outFile;
     std::string filename = outputDir + "/" + simTag;
     outFile.open(filename.c_str(), std::ofstream::out | std::ofstream::trunc);
     if (!outFile.is_open())
     {
         std::cerr << "Can't open file " << filename << std::endl;
         return 1;
     }
 
     outFile.setf(std::ios_base::fixed);
 
     double flowDuration = (simTime - udpAppStartTime).GetSeconds();
     for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin();
          i != stats.end();
          ++i)
     {
         Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(i->first);
         std::stringstream protoStream;
         protoStream << (uint16_t)t.protocol;
         if (t.protocol == 6)
         {
             protoStream.str("TCP");
         }
         if (t.protocol == 17)
         {
             protoStream.str("UDP");
         }
         outFile << "\nFlow " << i->first << " (" << t.sourceAddress << ":" << t.sourcePort << " -> "
                 << t.destinationAddress << ":" << t.destinationPort << ") protocol "
                 << protoStream.str() << "\n";
         outFile << "  Tx Packets: " << i->second.txPackets << "\n";
         outFile << "  Tx Bytes:   " << i->second.txBytes << "\n";
         outFile << "  TxOffered:  " << i->second.txBytes * 8.0 / flowDuration / 1000.0 / 1000.0
                 << " Mbps\n";
         outFile << "  Rx Bytes:   " << i->second.rxBytes << "\n";
         if (i->second.rxPackets > 0)
         {
             // Measure the duration of the flow from receiver's perspective
             averageFlowThroughput += i->second.rxBytes * 8.0 / flowDuration / 1000 / 1000;
             averageFlowDelay += 1000 * i->second.delaySum.GetSeconds() / i->second.rxPackets;
             averageFlowJitter += 1000 * i->second.jitterSum.GetSeconds() / i->second.rxPackets;
 
             outFile << "  Throughput: " << i->second.rxBytes * 8.0 / flowDuration / 1000 / 1000
                     << " Mbps\n";
             outFile << "  Mean delay:  "
                     << 1000 * i->second.delaySum.GetSeconds() / i->second.rxPackets << " ms\n";
             // outFile << "  Mean upt:  " << i->second.uptSum / i->second.rxPackets / 1000/1000 << "
             // Mbps \n";
             outFile << "  Mean jitter:  "
                     << 1000 * i->second.jitterSum.GetSeconds() / i->second.rxPackets << " ms\n";
         }
         else
         {
             outFile << "  Throughput:  0 Mbps\n";
             outFile << "  Mean delay:  0 ms\n";
             outFile << "  Mean jitter: 0 ms\n";
         }
         outFile << "  Rx Packets: " << i->second.rxPackets << "\n";
     }
 
     double meanFlowThroughput = averageFlowThroughput / stats.size();
     double meanFlowDelay = averageFlowDelay / stats.size();
     double meanFlowJitter = averageFlowJitter / stats.size();
 
     outFile << "\n\n  Mean flow throughput: " << meanFlowThroughput << " Mbps\n";
     outFile << "  Mean flow delay: " << meanFlowDelay << " ms\n";
     outFile << "  Mean flow jitter: " << meanFlowJitter << " ms\n\n";

     outFile << "  Taxa de Ocupação de Dados: " << channelUtilization << " % \n\n";
 

     std::cout << "===== Estatísticas de PRBs =====" << std::endl;
     std::cout << "Tempo total do canal ocupado: " << channelBusyTime << " segundos" << std::endl;
     std::cout << "Total simulation time: " << totalChannelTime << " seconds\n\n" << std::endl;
 
     std::cout << "Scheduler configurado: NrMacSchedulerOfdmaQos \n\n\n" << std::endl;


     outFile.close();
 
     std::ifstream f(filename.c_str());
 
     if (f.is_open())
     {
         std::cout << f.rdbuf();
     }



 
     Simulator::Destroy();
 
     if (argc == 0)
     {
         double toleranceMeanFlowThroughput = 0.0001 * 56.258560;
         double toleranceMeanFlowDelay = 0.0001 * 0.553292;
 
         if (meanFlowThroughput >= 56.258560 - toleranceMeanFlowThroughput &&
             meanFlowThroughput <= 56.258560 + toleranceMeanFlowThroughput &&
             meanFlowDelay >= 0.553292 - toleranceMeanFlowDelay &&
             meanFlowDelay <= 0.553292 + toleranceMeanFlowDelay)
         {
             return EXIT_SUCCESS;
         }
         else
         {
             return EXIT_FAILURE;
         }
     }
     else if (argc == 1 and ueNumPergNb == 9) // called from examples-to-run.py with these parameters
     {
         double toleranceMeanFlowThroughput = 0.0001 * 47.858536;
         double toleranceMeanFlowDelay = 0.0001 * 10.504189;
 
         if (meanFlowThroughput >= 47.858536 - toleranceMeanFlowThroughput &&
             meanFlowThroughput <= 47.858536 + toleranceMeanFlowThroughput &&
             meanFlowDelay >= 10.504189 - toleranceMeanFlowDelay &&
             meanFlowDelay <= 10.504189 + toleranceMeanFlowDelay)
         {
             return EXIT_SUCCESS;
         }
         else
         {
             return EXIT_FAILURE;
         }
     }
     else
     {
         return EXIT_SUCCESS; // we dont check other parameters configurations at the moment
     }
 }
