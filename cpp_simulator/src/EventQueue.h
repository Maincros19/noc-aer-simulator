#ifndef EVENT_QUEUE_H
#define EVENT_QUEUE_H

#include <queue>
#include <vector>
#include "Event.h"

class EventQueue {
public:
    EventQueue() : current_time(0) {}

    void addEvent(const Event& event) {
        pq.push(event);
    }

    Event getNextEvent() {
        Event event = pq.top();
        pq.pop();
        current_time = event.timestamp; // Update current_time when an event is processed
        return event;
    }

    bool isEmpty() const {
        return pq.empty();
    }

    uint64_t getCurrentTime() const {
        return current_time;
    }

private:
    std::priority_queue<Event, std::vector<Event>, std::greater<Event>> pq;
    uint64_t current_time; // Track the current simulation time
};


#endif // EVENT_QUEUE_H
