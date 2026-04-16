#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "Event.h"
#include "EventQueue.h"
#include "Flit.h"
#include "Router.h"
#include "Network.h"

namespace py = pybind11;

PYBIND11_MODULE(noc_simulator_pybind, m) {
    m.doc() = "pybind11 plugin for NoC AER Simulator C++ core"; // optional module docstring

    py::enum_<EventType>(m, "EventType")
        .value("FLIT_ARRIVAL", FLIT_ARRIVAL)
        .value("ROUTER_PROCESSING", ROUTER_PROCESSING)
        .export_values();

    py::class_<Event>(m, "Event")
        .def(py::init<uint64_t, EventType, int, int>(),
             py::arg("timestamp"), py::arg("type"), py::arg("source_router_id"), py::arg("dest_router_id"))
        .def_readwrite("timestamp", &Event::timestamp)
        .def_readwrite("type", &Event::type)
        .def_readwrite("source_router_id", &Event::source_router_id)
        .def_readwrite("dest_router_id", &Event::dest_router_id);

    py::class_<EventQueue>(m, "EventQueue")
        .def(py::init<>()) 
        .def("addEvent", &EventQueue::addEvent)
        .def("getNextEvent", &EventQueue::getNextEvent)
        .def("isEmpty", &EventQueue::isEmpty)
        .def("getCurrentTime", &EventQueue::getCurrentTime);

    py::enum_<FlitType>(m, "FlitType")
        .value("HEADER", HEADER)
        .value("BODY", BODY)
        .value("TAIL", TAIL)
        .export_values();

    py::class_<Flit>(m, "Flit")
        .def(py::init<uint64_t, uint64_t, FlitType, int, int, int, uint64_t>(),
             py::arg("id"), py::arg("packet_id"), py::arg("type"), py::arg("source_router_id"),
             py::arg("dest_router_id"), py::arg("current_router_id"), py::arg("injection_time"))
        .def_readwrite("id", &Flit::id)
        .def_readwrite("packet_id", &Flit::packet_id)
        .def_readwrite("type", &Flit::type)
        .def_readwrite("source_router_id", &Flit::source_router_id)
        .def_readwrite("dest_router_id", &Flit::dest_router_id)
        .def_readwrite("current_router_id", &Flit::current_router_id)
        .def_readwrite("injection_time", &Flit::injection_time);

    py::enum_<Port>(m, "Port")
        .value("LOCAL", LOCAL)
        .value("NORTH", NORTH)
        .value("EAST", EAST)
        .value("SOUTH", SOUTH)
        .value("WEST", WEST)
        .export_values();

    py::class_<Router>(m, "Router")
        .def(py::init<int, int, int, EventQueue&>(),
             py::arg("id"), py::arg("x"), py::arg("y"), py::arg("event_queue"), py::keep_alive<1, 5>() /* Essential for EventQueue reference */)
        .def("receiveFlit", &Router::receiveFlit)
        .def("processFlit", &Router::processFlit)
        .def("injectFlit", &Router::injectFlit)
        .def("getX", &Router::getX)
        .def("getY", &Router::getY)
        .def("getId", &Router::getId)
        .def("getFlitsDropped", &Router::getFlitsDropped)
        .def("getFlitsReceived", &Router::getFlitsReceived)
        .def("getAvgLatency", &Router::getAvgLatency);

    py::class_<Network>(m, "Network")
        .def(py::init<int, int, EventQueue&>(),
             py::arg("dim_x"), py::arg("dim_y"), py::arg("event_queue"), py::keep_alive<1, 4>() /* Essential for EventQueue reference */)
        .def("addRouter", &Network::addRouter)
        .def("getRouter", &Network::getRouter, py::return_value_policy::reference)
        .def("runSimulation", &Network::runSimulation);
}
