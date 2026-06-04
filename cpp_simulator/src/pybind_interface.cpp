#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "Event.h"
#include "EventQueue.h"
#include "Flit.h"
#include "Router.h"
#include "Network.h"

namespace py = pybind11;

PYBIND11_MODULE(noc_simulator_pybind, m) {
    m.doc() = "pybind11 plugin for NoC AER Simulator C++ core";

    py::enum_<Port>(m, "Port")
        .value("LOCAL", LOCAL)
        .value("NORTH", NORTH)
        .value("EAST", EAST)
        .value("SOUTH", SOUTH)
        .value("WEST", WEST)
        .export_values();

    py::enum_<EventType>(m, "EventType")
        .value("FLIT_ARRIVAL", FLIT_ARRIVAL)
        .value("ROUTER_PROCESSING", ROUTER_PROCESSING)
        .value("LINK_TRANSMISSION", LINK_TRANSMISSION)
        .value("CREDIT_ARRIVAL", CREDIT_ARRIVAL)
        .value("SOURCE_INJECTION", SOURCE_INJECTION)
        .export_values();

    py::enum_<FlitType>(m, "FlitType")
        .value("HEADER", HEADER)
        .value("BODY", BODY)
        .value("TAIL", TAIL)
        .export_values();

    py::class_<Synapse>(m, "Synapse")
        .def(py::init<int, int, double>(), py::arg("dest_router_id"), py::arg("dest_neuron_id"), py::arg("weight"))
        .def_readwrite("dest_router_id", &Synapse::dest_router_id)
        .def_readwrite("dest_neuron_id", &Synapse::dest_neuron_id)
        .def_readwrite("weight", &Synapse::weight);
        // -----------------------------------

    py::class_<Flit>(m, "Flit")
        .def(py::init<uint64_t, uint64_t, FlitType, int, int, int, uint64_t, double, int>(),
             py::arg("id") = -1, py::arg("packet_id") = 0, py::arg("type") = BODY, py::arg("source_router_id") = -1,
             py::arg("dest_router_id") = -1, py::arg("current_router_id") = -1, py::arg("injection_time") = 0,
             py::arg("payload_weight") = 0.0, py::arg("dest_neuron_id") = -1)
        .def_readwrite("id", &Flit::id)
        .def_readwrite("packet_id", &Flit::packet_id)
        .def_readwrite("type", &Flit::type)
        .def_readwrite("source_router_id", &Flit::source_router_id)
        .def_readwrite("dest_router_id", &Flit::dest_router_id)
        .def_readwrite("current_router_id", &Flit::current_router_id)
        .def_readwrite("injection_time", &Flit::injection_time)
        .def_readwrite("dma_entry_time", &Flit::dma_entry_time)
        .def_readwrite("network_entry_time", &Flit::network_entry_time)
        .def_readwrite("payload_weight", &Flit::payload_weight)
        .def_readwrite("dest_neuron_id", &Flit::dest_neuron_id);


    py::class_<Event>(m, "Event")
        .def(py::init<uint64_t, EventType, int, int, Flit, Port>(),
             py::arg("timestamp"), py::arg("type"), py::arg("source_router_id"), py::arg("dest_router_id"), py::arg("flit") = Flit(), py::arg("port") = LOCAL)
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

    py::class_<Router>(m, "Router")
        .def(py::init<int, int, int, int, int, EventQueue&>(),
             py::arg("id"), py::arg("x"), py::arg("y"), py::arg("dim_x"), py::arg("dim_y"), py::arg("event_queue"), py::keep_alive<1, 6>())
        .def("receiveFlit", &Router::receiveFlit)
        .def("processFlit", &Router::processFlit)
        .def("injectFlit", &Router::injectFlit)
        .def("getX", &Router::getX)
        .def("getY", &Router::getY)
        .def("getId", &Router::getId)
        .def("getFlitsDropped", &Router::getFlitsDropped)
        .def("getFlitsReceived", &Router::getFlitsReceived)
        .def("getFlitsInjected", &Router::getFlitsInjected)
        .def("getFlitsForwarded", &Router::getFlitsForwarded)
        .def("getAvgLatency", &Router::getAvgLatency)
        .def("getLatencyJitter", &Router::getLatencyJitter)
        .def("setBufferSizes", &Router::setBufferSizes)
        .def("getInjectionBufferSize", &Router::getInjectionBufferSize)
        .def("getNetworkBufferSize", &Router::getNetworkBufferSize)
        .def("getBufferOccupancy", &Router::getBufferOccupancy)
        .def("getDetailedOccupancy", &Router::getDetailedOccupancy)
        .def("getLinkActivity", &Router::getLinkActivity)
        .def("resetLinkActivity", &Router::resetLinkActivity)
        .def("getLinkStallStatus", &Router::getLinkStallStatus)
        .def("mapNeuron", &Router::mapNeuron, py::arg("neuron_id"), py::arg("v_th"), py::arg("leak"), py::arg("synapses"))
        .def("getNeuronSpikeCount", &Router::getNeuronSpikeCount, py::arg("neuron_id"))
        .def("resetNeuronsState", &Router::resetNeuronsState)
        .def("evaluateNeurons", &Router::evaluateNeurons, py::arg("current_time"), py::arg("tiempo_limite"))
        .def_readwrite("tiempo_limite_actual", &Router::tiempo_limite_actual) // <--- ESTO ES LO QUE FALTA
        .def("getLateFlits", &Router::getLateFlits);

    py::class_<Network>(m, "Network")
        .def(py::init<int, int, EventQueue&>(),
             py::arg("dim_x"), py::arg("dim_y"), py::arg("event_queue"), py::keep_alive<1, 4>())
        .def("addRouter", &Network::addRouter)
        .def("getRouter", &Network::getRouter, py::return_value_policy::reference)
        .def("runSimulation", &Network::runSimulation)
        .def("getTotalFlitsInjected", &Network::getTotalFlitsInjected)
        .def("getTotalFlitsReceived", &Network::getTotalFlitsReceived)
        .def("getTotalFlitsDropped", &Network::getTotalFlitsDropped)
        .def("getAvgLatency", &Network::getAvgLatency)
        .def("getAvgInjectionLatency", &Network::getAvgInjectionLatency) // NUEVO
        .def("getAvgNetworkLatency", &Network::getAvgNetworkLatency)     // NUEVO
        .def("getAvgJitter", &Network::getAvgJitter)
        .def("getSimulationTime", &Network::getSimulationTime)
        .def("getTotalForwarded", &Network::getTotalForwarded)
        .def("getAvgRamLatency", &Network::getAvgRamLatency)
        .def("getAvgBufferLatency", &Network::getAvgBufferLatency)
        .def("resetNeuronsState", &Network::resetNeuronsState)
        .def("stepSimulation", &Network::stepSimulation);



}
