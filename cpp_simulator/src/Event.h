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
        : timestamp(ts), type(t), source_router_id(src_id), dest_router_id(dest_id), flit(f) {}

    bool operator>(const Event& other) const {
        return timestamp > other.timestamp;
    }
};

#endif
