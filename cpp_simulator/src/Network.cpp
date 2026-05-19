#include "Network.h"
#include "Event.h"
#include <iostream>
#include <numeric>

Network::Network(int dim_x, int dim_y, EventQueue& eq)
    : dim_x(dim_x), dim_y(dim_y), event_queue(eq) {
    for (int y = 0; y < dim_y; ++y) {
        for (int x = 0; x < dim_x; ++x) {
            int router_id = y * dim_x + x;
            routers[router_id] = new Router(router_id, x, y, dim_x, dim_y, event_queue);
        }
    }
}

Network::~Network() {
    for (auto const& [id, router] : routers) {
        delete router;
    }
}

void Network::addRouter(int id, int x, int y) {
    if (routers.find(id) == routers.end()) {
        routers[id] = new Router(id, x, y, dim_x, dim_y, event_queue);
    }
}

Router* Network::getRouter(int id) {
    auto it = routers.find(id);
    if (it != routers.end()) {
        return it->second;
    }
    return nullptr;
}

// Función auxiliar para procesar un solo evento (Lógica unificada)
void Network::handleEvent(const Event& event) {
    uint64_t current_time = event.timestamp;
    current_sim_time = current_time;
    Router* router = getRouter(event.source_router_id);

    if (router) {
        if (event.type == FLIT_ARRIVAL) {
            int src_id = event.flit.current_router_id;
            int dst_id = event.source_router_id;

            Port in_port = LOCAL;
            if (src_id == dst_id - dim_x) in_port = NORTH;
            else if (src_id == dst_id + dim_x) in_port = SOUTH;
            else if (src_id == dst_id + 1) in_port = EAST;
            else if (src_id == dst_id - 1) in_port = WEST;

            router->receiveFlit(event.flit, in_port, current_time);
        } else if (event.type == ROUTER_PROCESSING) {
            router->processFlit(current_time);
        } else if (event.type == CREDIT_ARRIVAL) {
            router->receiveCredit(event.port);
            if (!router->isProcessingScheduled()) {
                event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, router->getId(), router->getId()));
                router->setProcessingScheduled(true);
            }
        } else if (event.type == SOURCE_INJECTION) {
            router->addPendingInjection(event.flit, current_time);
        }
    }
}

// Ahora runSimulation y stepSimulation son muy simples:
void Network::runSimulation() {
    while (!event_queue.isEmpty()) {
        handleEvent(event_queue.getNextEvent());
    }
}

void Network::stepSimulation(int num_events) {
    int processed = 0;
    while (!event_queue.isEmpty() && processed < num_events) {
        handleEvent(event_queue.getNextEvent());
        processed++;
    }
}

uint64_t Network::getTotalFlitsInjected() const {
    uint64_t total = 0;
    for (auto const& [id, router] : routers) total += router->getFlitsInjected();
    return total;
}

uint64_t Network::getTotalFlitsReceived() const {
    uint64_t total = 0;
    for (auto const& [id, router] : routers) total += router->getFlitsReceived();
    return total;
}

uint64_t Network::getTotalFlitsDropped() const {
    uint64_t total = 0;
    for (auto const& [id, router] : routers) total += router->getFlitsDropped();
    return total;
}

double Network::getAvgLatency() const {
    double total_lat_sum = 0;
    uint64_t total_rec = 0;
    for (auto const& [id, router] : routers) {
        total_lat_sum += router->getTotalLatency();
        total_rec += router->getFlitsReceived();
    }
    return total_rec > 0 ? total_lat_sum / total_rec : 0;
}

double Network::getAvgJitter() const {
    double global_latency_sum = 0;
    double global_latency_sq_sum = 0;
    uint64_t global_received = 0;

    for (auto const& [id, router] : routers) {
        global_latency_sum += router->getTotalLatency();
        global_latency_sq_sum += router->getTotalLatencySq(); 
        global_received += router->getFlitsReceived();
    }

    if (global_received < 2) return 0.0;

    double global_avg = (double)global_latency_sum / global_received;
    double variance = ((double)global_latency_sq_sum / global_received) - (global_avg * global_avg);
    
    return std::sqrt(std::max(0.0, variance));
}

uint64_t Network::getSimulationTime() const {
    return current_sim_time;
}

uint64_t Network::getTotalForwarded() const {
    uint64_t total = 0;
    for (auto const& [id, router] : routers) total += router->getFlitsForwarded();
    return total;
}
double Network::getAvgInjectionLatency() const {
    double total_inj_sum = 0;
    uint64_t total_rec = 0;
    for (auto const& [id, router] : routers) {
        total_inj_sum += router->getTotalInjectionLatency();
        total_rec += router->getFlitsReceived();
    }
    return total_rec > 0 ? total_inj_sum / total_rec : 0;
}

double Network::getAvgNetworkLatency() const {
    double total_net_sum = 0;
    uint64_t total_rec = 0;
    for (auto const& [id, router] : routers) {
        total_net_sum += router->getTotalNetworkLatency();
        total_rec += router->getFlitsReceived();
    }
    return total_rec > 0 ? total_net_sum / total_rec : 0;
}

double Network::getAvgRamLatency() const {
    double total_ram_sum = 0;
    uint64_t total_rec = 0;
    for (auto const& [id, router] : routers) {
        total_ram_sum += router->getTotalRamLatency();
        total_rec += router->getFlitsReceived();
    }
    return total_rec > 0 ? total_ram_sum / total_rec : 0;
}

double Network::getAvgBufferLatency() const {
    double total_buf_sum = 0;
    uint64_t total_rec = 0;
    for (auto const& [id, router] : routers) {
        total_buf_sum += router->getTotalBufferLatency();
        total_rec += router->getFlitsReceived();
    }
    return total_rec > 0 ? total_buf_sum / total_rec : 0;
}
