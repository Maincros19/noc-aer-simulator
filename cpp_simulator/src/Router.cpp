#include "Router.h"
#include "Event.h"
#include <iostream>

Router::Router(int id, int x, int y, int dim_x, int dim_y, EventQueue& eq)
    : id(id), x_coord(x), y_coord(y), dim_x(dim_x), dim_y(dim_y), event_queue(eq),
      max_injection_buffer_size(1024), max_network_buffer_size(32), last_arbitrated_port(WEST), is_processing_scheduled(false),
      flits_dropped(0), flits_received(0),     flits_injected(0),
    flits_forwarded(0),
    link_activity(NUM_PORTS, 0),
    total_latency(0), total_latency_sq(0), total_injection_latency(0), total_network_latency(0),
      total_ram_latency(0), total_buffer_latency(0) {
    for (int i = 0; i < NUM_PORTS; ++i) {
        input_buffers[static_cast<Port>(i)] = std::queue<Flit>();

        // Asignar el tamaño de crédito correcto según el tipo de puerto
        if (i == LOCAL) {
            downstream_credits[static_cast<Port>(i)] = max_injection_buffer_size;
        } else {
            downstream_credits[static_cast<Port>(i)] = max_network_buffer_size;
        }
    }
}

// --- NUEVO: Función para que Python guarde los pesos en la SRAM del router ---
void Router::mapNeuron(int neuron_id, double v_th, double leak, const std::vector<Synapse>& synapses) {
    LogicalNeuron n;
    n.neuron_id = neuron_id;
    n.v_mem = 0.0; // Inicia en potencial de reposo
    n.v_th = v_th;
    n.leak_factor = leak;
    n.synapses = synapses;
    n.spike_count = 0;
    local_neurons.push_back(n);
}

void Router::evaluateNeurons(uint64_t current_time, uint64_t tiempo_limite) {
    this->tiempo_limite_actual = tiempo_limite;
    bool generated_spikes = false;

    for (auto& n : local_neurons) {
        n.v_mem *= n.leak_factor;
        if (n.v_mem >= n.v_th) {
            n.v_mem = 0.0;
            n.spike_count++;

            if (multicast_enabled && !n.synapses.empty()) {
                // --- MODO MULTICAST: 1 solo flit en la inyección ---
                uint64_t flit_id_global = ((uint64_t)this->id << 32) | (flit_id_counter++);
                Flit flit(flit_id_global, 0, BODY, this->id, -1, this->id, current_time);
                flit.is_multicast = true;

                for (auto& syn : n.synapses) {
                    flit.dest_routers.push_back(syn.dest_router_id);
                    flit.dest_neurons.push_back(syn.dest_neuron_id);
                    flit.payload_weights.push_back(syn.weight);
                }

                if (input_buffers[LOCAL].size() < max_injection_buffer_size) {
                    input_buffers[LOCAL].push(flit);
                    generated_spikes = true;
                    flits_injected++;
                } else {
                    flits_dropped++;
                }
            } else {
                // --- MODO UNICAST ORIGINAL ---
                for (auto& syn : n.synapses) {
                    uint64_t flit_id_global = ((uint64_t)this->id << 32) | (flit_id_counter++);
                    Flit flit(flit_id_global, 0, BODY, this->id, syn.dest_router_id, this->id, current_time, syn.weight, syn.dest_neuron_id);
                    if (input_buffers[LOCAL].size() < max_injection_buffer_size) {
                        input_buffers[LOCAL].push(flit);
                        generated_spikes = true;
                        flits_injected++;
                    } else {
                        flits_dropped++;
                    }
                }
            }
        }
    }

    if (generated_spikes && !is_processing_scheduled) {
        event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, id));
        is_processing_scheduled = true;
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
    // En lugar de meterlo al buffer físico, agendamos su nacimiento
    event_queue.addEvent(Event(current_time, SOURCE_INJECTION, id, flit.dest_router_id, flit, LOCAL));
}

void Router::receiveCredit(Port out_port) {
    downstream_credits[out_port]++;
}

void Router::processFlit(uint64_t current_time) {
    is_processing_scheduled = false;
    Port in_port = arbitrate();
    if (in_port == NUM_PORTS) return;

    Flit flit = input_buffers[in_port].front();

    if (flit.is_multicast) {
        // 1. Agrupar destinos en ramas (Branches)
        std::map<Port, Flit> branch_flits;
        for (size_t i = 0; i < flit.dest_routers.size(); ++i) {
            Flit dummy; dummy.dest_router_id = flit.dest_routers[i];
            Port out_port = routeFlit(dummy);

            if (branch_flits.find(out_port) == branch_flits.end()) {
                branch_flits[out_port] = flit;
                branch_flits[out_port].dest_routers.clear();
                branch_flits[out_port].dest_neurons.clear();
                branch_flits[out_port].payload_weights.clear();
            }
            branch_flits[out_port].dest_routers.push_back(flit.dest_routers[i]);
            branch_flits[out_port].dest_neurons.push_back(flit.dest_neurons[i]);
            branch_flits[out_port].payload_weights.push_back(flit.payload_weights[i]);
        }

        // 2. Comprobar créditos para todas las ramas requeridas
        bool stall = false;
        for (auto const& pair : branch_flits) {
            if (pair.first != LOCAL && downstream_credits[pair.first] <= 0) {
                stall = true; break;
            }
        }

        if (stall) {
            if (!is_processing_scheduled) {
                event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, id));
                is_processing_scheduled = true;
            }
            return;
        }

        input_buffers[in_port].pop();
        if (in_port == LOCAL && flit.network_entry_time == flit.injection_time) {
            flit.network_entry_time = current_time;
        }

        if (in_port != LOCAL) {
            int prev_router_id = -1;
            Port prev_out_port = LOCAL;
            if (in_port == NORTH) { prev_router_id = id - dim_x; prev_out_port = SOUTH; }
            else if (in_port == SOUTH) { prev_router_id = id + dim_x; prev_out_port = NORTH; }
            else if (in_port == EAST) { prev_router_id = id + 1; prev_out_port = WEST; }
            else if (in_port == WEST) { prev_router_id = id - 1; prev_out_port = EAST; }
            if (prev_router_id >= 0 && prev_router_id < (dim_x * dim_y)) {
                Flit credit_flit; credit_flit.injection_time = current_time;
                event_queue.addEvent(Event(current_time + 1, CREDIT_ARRIVAL, prev_router_id, prev_router_id, credit_flit, prev_out_port));
            }
        }

        for (auto& pair : branch_flits) {
            Port out_port = pair.first;
            Flit b_flit = pair.second;
            if (out_port != LOCAL) downstream_credits[out_port]--;
            flits_forwarded++;
            link_activity[out_port]++;
            b_flit.network_entry_time = flit.network_entry_time;
            switchFlit(b_flit, out_port, current_time);
        }
    } else {
        // --- UNICAST ORIGINAL ---
        Port out_port = routeFlit(flit);
        if (out_port != LOCAL && downstream_credits[out_port] <= 0) {
            if (!is_processing_scheduled) {
                event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, id));
                is_processing_scheduled = true;
            }
            return;
        }
        input_buffers[in_port].pop();
        if (out_port != LOCAL) downstream_credits[out_port]--;
        if (in_port == LOCAL && flit.network_entry_time == flit.injection_time) flit.network_entry_time = current_time;
        flits_forwarded++;
        link_activity[out_port]++;

        if (in_port != LOCAL) {
            int prev_router_id = -1;
            Port prev_out_port = LOCAL;
            if (in_port == NORTH) { prev_router_id = id - dim_x; prev_out_port = SOUTH; }
            else if (in_port == SOUTH) { prev_router_id = id + dim_x; prev_out_port = NORTH; }
            else if (in_port == EAST) { prev_router_id = id + 1; prev_out_port = WEST; }
            else if (in_port == WEST) { prev_router_id = id - 1; prev_out_port = EAST; }
            if (prev_router_id >= 0 && prev_router_id < (dim_x * dim_y)) {
                Flit credit_flit; credit_flit.injection_time = current_time;
                event_queue.addEvent(Event(current_time + 1, CREDIT_ARRIVAL, prev_router_id, prev_router_id, credit_flit, prev_out_port));
            }
        }
        switchFlit(flit, out_port, current_time);
    }

    bool has_more_flits = false;
    for (int i = 0; i < NUM_PORTS; ++i) {
        if (!input_buffers[static_cast<Port>(i)].empty()) { has_more_flits = true; break; }
    }
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
        flits_received++;
        uint64_t lat = (current_time > flit.injection_time) ? (current_time - flit.injection_time) : 1;
        total_latency += lat; total_latency_sq += (lat * lat);
        total_ram_latency += (flit.dma_entry_time >= flit.injection_time) ? (flit.dma_entry_time - flit.injection_time) : 0;
        total_buffer_latency += (flit.network_entry_time >= flit.dma_entry_time) ? (flit.network_entry_time - flit.dma_entry_time) : 0;
        total_network_latency += (current_time > flit.network_entry_time) ? (current_time - flit.network_entry_time) : 0;
        total_injection_latency += (flit.network_entry_time >= flit.injection_time) ? (flit.network_entry_time - flit.injection_time) : 0;

        if (flit.is_multicast) {
            for (size_t i = 0; i < flit.dest_routers.size(); ++i) {
                if (flit.dest_routers[i] == id) {
                    for (auto& n : local_neurons) {
                        if (n.neuron_id == flit.dest_neurons[i]) {
                            if (current_time > tiempo_limite_actual) late_flits++;
                            else n.v_mem += flit.payload_weights[i];
                            break;
                        }
                    }
                }
            }
        } else {
            for (auto& n : local_neurons) {
                if (n.neuron_id == flit.dest_neuron_id) {
                    if (current_time > tiempo_limite_actual) late_flits++;
                    else n.v_mem += flit.payload_weight;
                    break;
                }
            }
        }
    } else {
        int next_router_id = -1;
        if (out_port == NORTH) next_router_id = id - dim_x;
        else if (out_port == SOUTH) next_router_id = id + dim_x;
        else if (out_port == EAST) next_router_id = id + 1;
        else if (out_port == WEST) next_router_id = id - 1;

        if (next_router_id >= 0 && next_router_id < (dim_x * dim_y)) {
            flit.current_router_id = id;
            event_queue.addEvent(Event(current_time + 1, FLIT_ARRIVAL, next_router_id, flit.is_multicast ? -1 : flit.dest_router_id, flit));
        }
    }
}
void Router::setBufferSizes(int inj_size, int net_size) {
    max_injection_buffer_size = inj_size;
    max_network_buffer_size = net_size;

    // Sincronizamos los créditos: LOCAL tiene el tamaño de inyección, el resto el de red
    for (int i = 0; i < NUM_PORTS; ++i) {
        if (i == LOCAL) {
            downstream_credits[static_cast<Port>(i)] = max_injection_buffer_size;
        } else {
            downstream_credits[static_cast<Port>(i)] = max_network_buffer_size;
        }
    }
}

bool Router::canAcceptLocalFlit() {
    return input_buffers[LOCAL].size() < max_injection_buffer_size;
}
// void Router::addPendingInjection(Flit flit, uint64_t current_time) {
    // pending_injections.push(flit);
    // Si el router estaba dormido, lo despertamos para que empiece a inyectar
    // if (!is_processing_scheduled) {
        // event_queue.addEvent(Event(current_time + 1, ROUTER_PROCESSING, id, id));
        // is_processing_scheduled = true;
    // }
// }
uint64_t Router::getNeuronSpikeCount(int neuron_id) const {
    for (const auto& n : local_neurons) {
        if (n.neuron_id == neuron_id) return n.spike_count;
    }
    return 0; // Si no existe, no ha disparado
}

// Método para resetear el contador de late_flits entre imágenes
void Router::resetNeuronsState() {
    for (auto& n : local_neurons) {
        n.v_mem = 0.0;
        n.spike_count = 0;
    }
    late_flits = 0; // Resetear también el contador de descartes
}

// Método para exponer el valor a Python
uint64_t Router::getLateFlits() const {
    return late_flits;
}
