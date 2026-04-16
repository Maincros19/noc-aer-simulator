#ifndef ROUTER_H
#define ROUTER_H

#include <queue>
#include <map>
#include <vector>
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
    static const int BUFFER_SIZE = 1024; // Aumentado para manejar ráfagas de spikes neuromórficos

    Router(int id, int x, int y, int dim_x, int dim_y, EventQueue& eq);

    void receiveFlit(Flit flit, Port in_port, uint64_t current_time);
    void processFlit(uint64_t current_time);
    void injectFlit(Flit flit, uint64_t current_time);

    int getX() const { return x_coord; }
    int getY() const { return y_coord; }
    int getId() const { return id; }
    uint64_t getFlitsDropped() const { return flits_dropped; }
    uint64_t getFlitsReceived() const { return flits_received; }
    double getAvgLatency() const { return flits_received > 0 ? (double)total_latency / flits_received : 0; }

private:
    int id;
    int x_coord;
    int y_coord;
    int dim_x;
    int dim_y;
    EventQueue& event_queue;

    // Buffers de entrada para cada puerto
    std::map<Port, std::queue<Flit>> input_buffers;
    Port last_arbitrated_port; // Para arbitraje Round Robin

    // Métricas de congestión y rendimiento
    uint64_t flits_dropped; // Contador de flits descartados por buffer lleno
    uint64_t flits_received; // Contador de flits que llegaron a su destino
    uint64_t total_latency; // Suma de latencias para calcular el promedio

    // Lógica de ruteo (ejemplo simple: ruteo XY)
    Port routeFlit(const Flit& flit);
    Port arbitrate();
    void switchFlit(Flit flit, Port out_port, uint64_t current_time);
};

#endif
