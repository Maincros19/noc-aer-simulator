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
    void stepSimulation(int num_events);
    void handleEvent(const Event& event);

    // Aggregate Metrics
    uint64_t getTotalFlitsInjected() const;
    uint64_t getTotalFlitsReceived() const;
    uint64_t getTotalFlitsDropped() const;
    double getAvgLatency() const;
    double getAvgJitter() const;
    uint64_t getSimulationTime() const;
    uint64_t getTotalForwarded() const;

private:
    int dim_x;
    int dim_y;
    EventQueue& event_queue;
    std::map<int, Router*> routers;
    uint64_t current_sim_time;

    int getRouterId(int x, int y) const { return y * dim_x + x; }
};

#endif // NETWORK_H
