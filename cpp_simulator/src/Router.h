#ifndef ROUTER_H
#define ROUTER_H

#include <queue>
#include <map>
#include <vector>
#include <cmath>
#include "Flit.h"
#include "EventQueue.h"

enum Port {
    LOCAL,
    NORTH,
    SOUTH,
    EAST,
    WEST,
    NUM_PORTS
};

class Router {
public:
    Router(int id, int x, int y, int dim_x, int dim_y, EventQueue& eq);

    void receiveFlit(Flit flit, Port in_port, uint64_t current_time);
    void processFlit(uint64_t current_time);
    void injectFlit(Flit flit, uint64_t current_time);

    int getX() const { return x_coord; }
    int getY() const { return y_coord; }
    int getId() const { return id; }
    uint64_t getFlitsDropped() const { return flits_dropped; }
    uint64_t getFlitsReceived() const { return flits_received; }
    uint64_t getFlitsInjected() const { return flits_injected; }
    uint64_t getFlitsForwarded() const { return flits_forwarded; }
    uint64_t getTotalLatency() const { return total_latency; }
    
    double getAvgLatency() const { return flits_received > 0 ? (double)total_latency / flits_received : 0; }
    double getLatencyJitter() const { 
        if (flits_received < 2) return 0;
        double avg = getAvgLatency();
        double variance = ((double)total_latency_sq / flits_received) - (avg * avg);
        return std::sqrt(std::max(0.0, variance));
    }

    void setMaxBufferSize(int size) { max_buffer_size = size; }
    int getMaxBufferSize() const { return max_buffer_size; }

private:
    int id;
    int x_coord;
    int y_coord;
    int dim_x;
    int dim_y;
    EventQueue& event_queue;
    int max_buffer_size;

    // Buffers de entrada para cada puerto
    std::map<Port, std::queue<Flit>> input_buffers;
    Port last_arbitrated_port; // Para arbitraje Round Robin

    // Métricas de congestión y rendimiento
    uint64_t flits_dropped;   // Contador de flits descartados por buffer lleno
    uint64_t flits_received;  // Contador de flits que llegaron a su destino (LOCAL)
    uint64_t flits_injected;  // Contador de flits inyectados localmente
    uint64_t flits_forwarded; // Contador de flits procesados (para energía dinámica)
    uint64_t total_latency;   // Suma de latencias
    uint64_t total_latency_sq; // Suma de latencias al cuadrado (para jitter)

    // Lógica de ruteo
    Port routeFlit(const Flit& flit);
    Port arbitrate();
    void switchFlit(Flit flit, Port out_port, uint64_t current_time);
};

#endif
