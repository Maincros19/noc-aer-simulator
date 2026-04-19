#ifndef EVENT_H
#define EVENT_H

#include <cstdint>
#include "Flit.h"
#include "Port.h"

enum EventType {
    CREDIT_ARRIVAL,     // Priority 0 (highest)
    ROUTER_PROCESSING,  // Priority 1
    FLIT_ARRIVAL,       // Priority 2
    LINK_TRANSMISSION,  // Priority 3
    SOURCE_INJECTION    // Priority 4
};

struct Event {
    uint64_t timestamp;
    EventType type;
    int source_router_id;
    int dest_router_id;
    Flit flit;
    Port port;

    Event(uint64_t ts, EventType t, int src_id, int dest_id, Flit f = Flit(), Port p = LOCAL)
        : timestamp(ts), type(t), source_router_id(src_id), dest_router_id(dest_id), flit(f), port(p) {}

    bool operator>(const Event& other) const {
        if (timestamp != other.timestamp) {
            return timestamp > other.timestamp;
        }
        // Tie-breaker: prioritize CREDIT_ARRIVAL and ROUTER_PROCESSING over FLIT_ARRIVAL
        // This ensures credits are processed before new flits arrive, reducing stalls.
        return type < other.type; 
    }
};

#endif
