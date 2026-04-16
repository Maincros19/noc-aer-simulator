#ifndef FLIT_H
#define FLIT_H

#include <cstdint>

enum FlitType {
    HEADER,
    BODY,
    TAIL
};

struct Flit {
    uint64_t id;
    uint64_t packet_id;
    FlitType type;
    int source_router_id;
    int dest_router_id;
    int current_router_id;
    uint64_t injection_time;

    Flit() : id(-1), packet_id(-1), type(HEADER), source_router_id(-1), dest_router_id(-1), current_router_id(-1), injection_time(0) {}

    Flit(uint64_t f_id, uint64_t p_id, FlitType t, int src_r_id, int dest_r_id, int curr_r_id, uint64_t inj_time)
        : id(f_id), packet_id(p_id), type(t), source_router_id(src_r_id), dest_router_id(dest_r_id), current_router_id(curr_r_id), injection_time(inj_time) {}
};

#endif
