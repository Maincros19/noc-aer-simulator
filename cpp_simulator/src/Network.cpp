#include "Network.h"
#include <iostream>

Network::Network(int dim_x, int dim_y, EventQueue& eq)
    : dim_x(dim_x), dim_y(dim_y), event_queue(eq) {
    // Crear routers para la malla
    for (int y = 0; y < dim_y; ++y) {
        for (int x = 0; x < dim_x; ++x) {
            int router_id = getRouterId(x, y);
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
    // Este método podría usarse para añadir routers de forma más flexible si no es una malla regular
    // Por ahora, los routers se crean en el constructor para una malla.
    if (routers.find(id) == routers.end()) {
        routers[id] = new Router(id, x, y, dim_x, dim_y, event_queue);
    } else {
        std::cerr << "Error: Router with ID " << id << " already exists." << std::endl;
    }
}

Router* Network::getRouter(int id) {
    auto it = routers.find(id);
    if (it != routers.end()) {
        return it->second;
    }
    return nullptr;
}

void Network::runSimulation() {
    while (!event_queue.isEmpty()) {
        Event current_event = event_queue.getNextEvent();
        uint64_t current_time = current_event.timestamp;

        // std::cout << "Processing event at time " << current_time << ", type: " << current_event.type << std::endl;

        switch (current_event.type) {
            case ROUTER_PROCESSING:
                if (Router* r = getRouter(current_event.source_router_id)) {
                    // Si el evento trae un flit (reenvío), el router lo recibe primero
                    if (current_event.flit.id != -1) {
                        r->receiveFlit(current_event.flit, LOCAL, current_time);
                    }
                    r->processFlit(current_time);
                }
                break;
            default:
                break;
        }
    }
}
