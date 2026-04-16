#ifndef NETWORK_H
#define NETWORK_H

#include <vector>
#include <map>
#include "Router.h"
#include "EventQueue.h"

class Network {
public:
    Network(int dim_x, int dim_y, EventQueue& eq);
    ~Network();

    void addRouter(int id, int x, int y);
    Router* getRouter(int id);
    void runSimulation();

private:
    int dim_x;
    int dim_y;
    EventQueue& event_queue;
    std::map<int, Router*> routers;

    // Helper para obtener el ID del router a partir de sus coordenadas
    int getRouterId(int x, int y) const { return y * dim_x + x; }
};

#endif // NETWORK_H
