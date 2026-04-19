#include "Router.h"
#include "Event.h"
#include <iostream>

Router::Router(int id, int x, int y, int dim_x, int dim_y, EventQueue& eq)
    : id(id), x_coord(x), y_coord(y), dim_x(dim_x), dim_y(dim_y), event_queue(eq),
      max_buffer_size(1024), last_arbitrated_port(WEST), is_processing_scheduled(false),
      flits_dropped(0), flits_received(0), flits_injected(0), flits_forwarded(0),
      total_latency(0), total_latency_sq(0) {
    for (int i = 0; i < NUM_PORTS; ++i) {
        input_buffers[static_cast<Port>(i)] = std::queue<Flit>();
        downstream_credits[static_cast<Port>(i)] = max_buffer_size;
    }
}

void Router::receiveFlit(Flit flit, Port in_port, uint64_t current_time) {
    input_buffers[in_port].push(flit);
    
    // Solo "despertamos" al router si no estaba ya programado para trabajar
    if (!is_processing_scheduled) {
        event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, id));
        is_processing_scheduled = true;
    }
}

void Router::injectFlit(Flit flit, uint64_t current_time) {
    flits_injected++;
    receiveFlit(flit, LOCAL, current_time);
}

void Router::receiveCredit(Port out_port) {
    downstream_credits[out_port]++;
}

void Router::processFlit(uint64_t current_time) {
    is_processing_scheduled = false; // Ya estamos trabajando en este ciclo

    Port in_port = arbitrate();
    if (in_port == NUM_PORTS) return;

    Flit flit = input_buffers[in_port].front(); 
    Port out_port = routeFlit(flit);

    // CONTROL DE FLUJO: Comprobamos si el vecino tiene espacio
    if (out_port != LOCAL && downstream_credits[out_port] <= 0) {
        // STALL: No hay créditos. El flit se queda bloqueado.
        // Nos reprogramamos para intentar de nuevo en el siguiente ciclo.
        if (!is_processing_scheduled) {
            event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, id));
            is_processing_scheduled = true;
        }
        return; 
    }

    // Si llegamos aquí, hay espacio físico en el vecino.
    input_buffers[in_port].pop(); 
    if (out_port != LOCAL) downstream_credits[out_port]--; 

    flits_forwarded++;
    
    // GENERAR CRÉDITO para el router que nos envió este flit
    if (in_port != LOCAL) {
        int prev_router_id = -1;
        Port prev_out_port = LOCAL; 
        if (in_port == NORTH) { prev_router_id = id - dim_x; prev_out_port = SOUTH; }
        else if (in_port == SOUTH) { prev_router_id = id + dim_x; prev_out_port = NORTH; }
        else if (in_port == EAST) { prev_router_id = id + 1; prev_out_port = WEST; }
        else if (in_port == WEST) { prev_router_id = id - 1; prev_out_port = EAST; }

        if (prev_router_id >= 0 && prev_router_id < (dim_x * dim_y)) {
            Flit credit_flit;
            credit_flit.injection_time = current_time; 
            event_queue.addEvent(Event(current_time + 1, CREDIT_ARRIVAL, prev_router_id, prev_router_id, credit_flit, prev_out_port));
        }
    }

    switchFlit(flit, out_port, current_time);
    
    // Al final del ciclo, ¿nos quedan más paquetes esperando en ALGÚN puerto?
    bool has_more_flits = false;
    for (int i = 0; i < NUM_PORTS; ++i) {
        if (!input_buffers[static_cast<Port>(i)].empty()) {
            has_more_flits = true;
            break;
        }
    }
    
    // Si quedan paquetes, nos agendamos para el próximo ciclo
    if (has_more_flits && !is_processing_scheduled) {
        event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, id));
        is_processing_scheduled = true;
    }
}

Port Router::routeFlit(const Flit& flit) {
    int dest_id = flit.dest_router_id;
    int dest_x = dest_id % dim_x;
    int dest_y = dest_id / dim_x;

    if (dest_x > x_coord) return EAST;
    if (dest_x < x_coord) return WEST;
    if (dest_y > y_coord) return SOUTH;
    if (dest_y < y_coord) return NORTH;
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
        // Un flit llega a su destino LOCAL solo si el router actual es el destino.
        // Verificamos si realmente es un flit de datos (BODY) y si este es su destino.
        if (flit.type == BODY && flit.dest_router_id == id) {
            flits_received++;
            // Evitamos subflujos de enteros si current_time < injection_time
            // debido a la inyección asíncrona desde Python.
            uint64_t lat = (current_time > flit.injection_time) ? (current_time - flit.injection_time) : 1;
            total_latency += lat;
            total_latency_sq += (lat * lat);
        }
    } else {
        int next_router_id = -1;
        if (out_port == NORTH) { next_router_id = id - dim_x; }
        else if (out_port == SOUTH) { next_router_id = id + dim_x; }
        else if (out_port == EAST) { next_router_id = id + 1; }
        else if (out_port == WEST) { next_router_id = id - 1; }

        if (next_router_id >= 0 && next_router_id < (dim_x * dim_y)) {
            flit.current_router_id = id;
            event_queue.addEvent(Event(current_time + 1, FLIT_ARRIVAL, next_router_id, flit.dest_router_id, flit));
        }
    }
}
