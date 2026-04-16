#include "Router.h"
#include <iostream>
#include <numeric> // Para std::iota

Router::Router(int id, int x, int y, EventQueue& eq)
    : id(id), x_coord(x), y_coord(y), event_queue(eq), last_arbitrated_port(LOCAL), flits_dropped(0), flits_received(0), total_latency(0) {
    for (int i = 0; i < NUM_PORTS; ++i) {
        input_buffers[(Port)i] = std::queue<Flit>();
    }
}

void Router::receiveFlit(Flit flit, Port in_port, uint64_t current_time) {
    if (input_buffers[in_port].size() < BUFFER_SIZE) {
        input_buffers[in_port].push(flit);
        // Programar un evento para procesar este flit en el siguiente ciclo disponible
        event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, flit.dest_router_id));
    } else {
        flits_dropped++;
        // Silenciado para evitar inundación de logs
        // std::cout << "Router " << id << " at time " << current_time << ": Dropped flit " << flit.id 
        //           << " due to full buffer on port " << in_port << std::endl;
    }
}

void Router::processFlit(uint64_t current_time) {
    Port arbitrated_port = arbitrate();

    if (arbitrated_port != NUM_PORTS) { // Si se ha seleccionado un puerto con flits
        Flit flit = input_buffers[arbitrated_port].front();
        input_buffers[arbitrated_port].pop();

        Port out_port = routeFlit(flit);
        switchFlit(flit, out_port, current_time);
    }
}

void Router::injectFlit(Flit flit, uint64_t current_time) {
    receiveFlit(flit, LOCAL, current_time);
}

Port Router::routeFlit(const Flit& flit) {
    int dest_x = flit.dest_router_id % 4; 
    int dest_y = flit.dest_router_id / 4; 

    if (x_coord < dest_x) return EAST;
    if (x_coord > dest_x) return WEST;
    if (y_coord < dest_y) return NORTH; 
    if (y_coord > dest_y) return SOUTH; 
    
    return LOCAL; 
}

Port Router::arbitrate() {
    for (int i = 0; i < NUM_PORTS; ++i) {
        Port current_port = static_cast<Port>((last_arbitrated_port + 1 + i) % NUM_PORTS);
        if (!input_buffers[current_port].empty()) {
            last_arbitrated_port = current_port;
            return current_port;
        }
    }
    return NUM_PORTS; 
}

void Router::switchFlit(Flit flit, Port out_port, uint64_t current_time) {
    if (out_port == LOCAL) {
        flits_received++;
        total_latency += (current_time - flit.injection_time);
    } else {
        // Determinar el ID del router vecino basado en el puerto de salida
        int next_router_id = -1;
        Port next_in_port = LOCAL;

        if (out_port == NORTH) { next_router_id = id - 4; next_in_port = SOUTH; }
        else if (out_port == SOUTH) { next_router_id = id + 4; next_in_port = NORTH; }
        else if (out_port == EAST) { next_router_id = id + 1; next_in_port = WEST; }
        else if (out_port == WEST) { next_router_id = id - 1; next_in_port = EAST; }

        if (next_router_id >= 0 && next_router_id < 16) {
            // En una red real, necesitaríamos acceso al objeto Network para obtener el puntero al vecino.
            // Para simplificar esta PoC, el Network.cpp ya maneja la conexión inicial, 
            // pero el switchFlit necesita disparar el evento en el vecino.
            // Como el Router no tiene puntero a Network, usaremos el EventQueue para que el Network procese el salto.
            event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, next_router_id, flit.dest_router_id, flit));
        }
    }
}
