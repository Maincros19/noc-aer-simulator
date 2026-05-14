#ifndef ROUTER_H
#define ROUTER_H

#include <queue>
#include <map>
#include <vector>
#include <cmath>
#include "Flit.h"
#include "EventQueue.h"
#include "Port.h"

class Router {
public:
    Router(int id, int x, int y, int dim_x, int dim_y, EventQueue& eq);

    void receiveFlit(Flit flit, Port in_port, uint64_t current_time);
    void processFlit(uint64_t current_time);
    void injectFlit(Flit flit, uint64_t current_time);
    void receiveCredit(Port out_port);
    bool isProcessingScheduled() const { return is_processing_scheduled; }
    void setProcessingScheduled(bool scheduled) { is_processing_scheduled = scheduled; }

    int getX() const { return x_coord; }
    int getY() const { return y_coord; }
    int getId() const { return id; }
    uint64_t getFlitsDropped() const { return flits_dropped; }
    uint64_t getFlitsReceived() const { return flits_received; }
    uint64_t getFlitsInjected() const { return flits_injected; }
    uint64_t getFlitsForwarded() const { return flits_forwarded; }
    double getTotalLatency() const { return total_latency; }
    double getTotalLatencySq() const { return total_latency_sq; }
    double getTotalInjectionLatency() const { return total_injection_latency; }
    double getTotalNetworkLatency() const { return total_network_latency; }
    
    double getAvgLatency() const { return flits_received > 0 ? (double)total_latency / flits_received : 0; }
    double getLatencyJitter() const { 
        if (flits_received < 2) return 0;
        double avg = getAvgLatency();
        double variance = ((double)total_latency_sq / flits_received) - (avg * avg);
        return std::sqrt(std::max(0.0, variance));
    }

    void setBufferSizes(int inj_size, int net_size);
    bool canAcceptLocalFlit();
    int getInjectionBufferSize() const { return max_injection_buffer_size; }
    int getNetworkBufferSize() const { return max_network_buffer_size; }
    void addPendingInjection(Flit flit, uint64_t current_time);

    int getBufferOccupancy() const {
        int total = 0;
        for (auto const& [port, queue] : input_buffers) {
            total += queue.size();
        }
        return total;
    }
    // Retorna la ocupación individual de cada puerto [LOCAL, NORTH, SOUTH, EAST, WEST]
    std::vector<int> getDetailedOccupancy() const {
        std::vector<int> detailed(NUM_PORTS);
        for (int i = 0; i < NUM_PORTS; ++i) {
            detailed[i] = input_buffers.at(static_cast<Port>(i)).size();
        }
        return detailed;
    }

    // Retorna si un enlace está en 'Stall' (tiene datos pero no tiene créditos para enviar)
    std::vector<bool> getLinkStallStatus() const {
        std::vector<bool> stalls(NUM_PORTS, false);
        for (int i = 1; i < NUM_PORTS; ++i) { // Empezamos en 1 para saltar el puerto LOCAL
            Port p = static_cast<Port>(i);
            if (!input_buffers.at(p).empty() && downstream_credits.at(p) <= 0) {
                stalls[i] = true;
            }
        }
        return stalls;
    }

private:
    int id;
    int x_coord;
    int y_coord;
    int dim_x;
    int dim_y;
    EventQueue& event_queue;
    int max_injection_buffer_size;
    int max_network_buffer_size;

    // Buffers de entrada para cada puerto
    std::map<Port, std::queue<Flit>> input_buffers;
    std::map<Port, int> downstream_credits;
    Port last_arbitrated_port; // Para arbitraje Round Robin
    bool is_processing_scheduled;
    
    // Métricas de congestión y rendimiento
    uint64_t flits_dropped;   // Contador de flits descartados por buffer lleno
    uint64_t flits_received;  // Contador de flits que llegaron a su destino (LOCAL)
    uint64_t flits_injected;  // Contador de flits inyectados localmente
    uint64_t flits_forwarded; // Contador de flits procesados (para energía dinámica)
    double total_latency;   // Suma de latencias (E2E)
    double total_latency_sq; // Suma de latencias al cuadrado (para jitter)
    double total_injection_latency; // NUEVO
    double total_network_latency;   // NUEVO

    // Lógica de ruteo
    Port routeFlit(const Flit& flit);
    Port arbitrate();
    void switchFlit(Flit flit, Port out_port, uint64_t current_time);

    std::queue<Flit> pending_injections;
};

#endif
