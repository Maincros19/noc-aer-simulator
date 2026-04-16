import simpy
from router import Router, NORTH, EAST, SOUTH, WEST, LOCAL
from packet import Packet, Flit

class Network:
    def __init__(self, env, config):
        self.env = env
        self.config = config
        self.routers = {}
        self.links = {} # {(src_router, dst_router): simpy.Store}
        self.injected_packets = {} # {packet_id: Packet}
        self.completed_packets = []
        self.total_flit_hops = 0
        self.total_switch_traversals = 0
        self.link_activity = {} # {router_id: {port: count}}

        self._build_network()

    def _build_network(self):
        # Crear routers
        for i in range(self.config['NUM_NODES']):
            self.routers[i] = Router(self.env, i, self.config['MESH_DIM_X'], self.config['MESH_DIM_Y'], self.config['BUFFER_SIZE'], self.links)
            self.link_activity[i] = {port: 0 for port in range(5)}

        # Crear enlaces (simplificado: los routers se comunican directamente a través de métodos)
        # En un simulador más detallado, los enlaces tendrían latencia y capacidad.
        # Aquí, la latencia del enlace se modela como 1 ciclo en el proceso de transferencia.

    def inject_packet(self, packet):
        self.injected_packets[packet.packet_id] = packet
        # Crear un flit para el paquete AER
        flit = Flit(packet.packet_id, packet.source_node, packet.source_node, list(packet.destination_nodes), 
                    0, packet.timestamp_injection, packet.packet_type_str)
        packet.add_flit(flit)
        
        # Inyectar el flit en el router origen (simulando que llega desde el LOCAL port)
        self.env.process(self._inject_flit_process(flit))

    def _inject_flit_process(self, flit):
        # Esperar hasta el timestamp de inyección
        if self.env.now < flit.timestamp_injection:
            yield self.env.timeout(flit.timestamp_injection - self.env.now)
        
        router = self.routers[flit.source_node]
        # Inyectar en el buffer LOCAL del router
        yield router.input_buffers[LOCAL].put(flit)

    def _deliver_flit(self, flit, dest_node):
        if flit.packet_id not in self.injected_packets: return
        packet = self.injected_packets[flit.packet_id]
        if dest_node not in packet.delivered_to:
            packet.delivered_to.add(dest_node)
            packet.delivery_times[dest_node] = self.env.now
            
            if packet.is_fully_delivered():
                self.completed_packets.append(packet)
                del self.injected_packets[packet.packet_id]

    def run_network_cycle(self):
        # Este proceso se ejecuta cada ciclo para mover flits entre routers
        while True:
            for router_id, router in self.routers.items():
                # 1. Procesar flits que llegaron al destino local
                while router.flits_received_local:
                    flit = router.flits_received_local.pop(0)
                    self._deliver_flit(flit, router_id)

                # 2. Mover flits entre routers
                for out_port in range(4): # No LOCAL
                    while router.flits_sent_out[out_port]:
                        flit = router.flits_sent_out[out_port].pop(0)
                        
                        # Determinar router destino y puerto de entrada
                        dest_router_id = router.get_neighbor_id(out_port)
                        in_port_at_dest = -1
                        if out_port == NORTH: in_port_at_dest = SOUTH
                        elif out_port == SOUTH: in_port_at_dest = NORTH
                        elif out_port == EAST: in_port_at_dest = WEST
                        elif out_port == WEST: in_port_at_dest = EAST

                        if dest_router_id != -1:
                            dest_router = self.routers[dest_router_id]
                            # Actualizar flit
                            flit.current_node = dest_router_id
                            flit.path.append(dest_router_id)
                            
                            # Inyectar en el input_buffer del destino
                            dest_router.receive_flit(flit, in_port_at_dest)
                            
                            # Actualizar métricas
                            self.total_flit_hops += 1
                            self.link_activity[router_id][out_port] += 1
            
            yield self.env.timeout(1)
