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
        # En lugar de usar el input_buffer LOCAL, lo procesamos directamente para inyección
        self.env.process(self._inject_flit_process(flit))

    def _inject_flit_process(self, flit):
        # Esperar hasta el timestamp de inyección
        if self.env.now < flit.timestamp_injection:
            yield self.env.timeout(flit.timestamp_injection - self.env.now)
        
        router = self.routers[flit.source_node]
        # Para simplificar, inyectamos directamente en el proceso de enrutamiento del router origen
        # En un modelo más preciso, iría al input_buffer[LOCAL]
        
        # Determinar puertos de salida iniciales (Enrutamiento XY)
        dest_x = list(flit.destination_nodes)[0] % self.config['MESH_DIM_X']
        dest_y = list(flit.destination_nodes)[0] // self.config['MESH_DIM_X']
        curr_x = router.id % self.config['MESH_DIM_X']
        curr_y = router.id // self.config['MESH_DIM_X']

        next_ports = []
        if curr_x < dest_x: next_ports.append(EAST)
        elif curr_x > dest_x: next_ports.append(WEST)
        elif curr_y < dest_y: next_ports.append(SOUTH)
        elif curr_y > dest_y: next_ports.append(NORTH)
        else: next_ports.append(LOCAL) # Ya está en el destino (o uno de ellos)

        # Manejo de Multicast en inyección
        for dest_node in flit.destination_nodes:
            if dest_node == router.id and LOCAL not in next_ports:
                next_ports.append(LOCAL)

        for out_port in next_ports:
            if out_port == LOCAL:
                self._deliver_flit(flit, router.id)
            else:
                # Replicar y poner en output_buffer
                replicated_flit = Flit(flit.packet_id, flit.source_node, router.id, list(flit.destination_nodes), 
                                       flit.flit_type, flit.timestamp_injection, flit.packet_type_str)
                yield router.output_buffers[out_port].put(replicated_flit)
                self.total_switch_traversals += 1

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
                for out_port in range(4): # No LOCAL
                    if len(router.flits_sent_out[out_port]) > 0:
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
