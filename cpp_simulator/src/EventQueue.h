#ifndef EVENT_QUEUE_H
#define EVENT_QUEUE_H

#include <queue>
#include <vector>
#include "Event.h"

class EventQueue {
public:
    void addEvent(const Event& event) {
        pq.push(event);
    }

    Event getNextEvent() {
        Event event = pq.top();
        pq.pop();
        return event;
    }

    bool isEmpty() const {
        return pq.empty();
    }

    uint64_t getCurrentTime() const {
        if (isEmpty()) {
            return 0;
        }
        return pq.top().timestamp;
    }

private:
    std::priority_queue<Event, std::vector<Event>, std::greater<Event>> pq;
};


#endif // EVENT_QUEUE_H
