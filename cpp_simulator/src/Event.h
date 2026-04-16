#ifndef EVENT_H
#define EVENT_H

#include <cstdint>
#include "Flit.h"

enum EventType {
    FLIT_ARRIVAL,
    ROUTER_PROCESSING,
    LINK_TRANSMISSION
};

struct Event {
    uint64_t timestamp;
    EventType type;
    int source_router_id;
    int dest_router_id;
    Flit flit;

    Event(uint64_t ts, EventType t, int src_id, int dest_id, Flit f = Flit())
        : timestamp(ts), type(t), source_router_id(src_id), dest_router_id(dest_id), flit(f) {
            // Si el flit es nuevo (inyección), aseguramos que su tiempo de inyección sea el actual
            if (flit.injection_time == 0 && flit.id != (uint64_t)-1) {
                flit.injection_time = ts;
            }
        }

    bool operator>(const Event& other) const {
        return timestamp > other.timestamp;
    }
};

#endif
