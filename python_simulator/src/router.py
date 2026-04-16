import simpy
import collections
from packet import Flit, Packet

# Definiciones de puertos (igual que en C++)
NORTH, EAST, SOUTH, WEST, LOCAL = 0, 1, 2, 3, 4
NUM_PORTS = 5

class Router:
    def __init__(self, env, router_id, mesh_dim_x, mesh_dim_y, buffer_size, network_links):
        self.env = env
        self.id = router_id
        self.mesh_dim_x = mesh_dim_x
        self.mesh_dim_y = mesh_dim_y
        self.buffer_size = buffer_size
        self.network_links = network_links # Referencia a los enlaces de la red

        self.input_buffers = {port: simpy.Store(env, capacity=buffer_size) for port in range(NUM_PORTS)}
        self.output_buffers = {port: simpy.Store(env, capacity=buffer_size) for port in range(NUM_PORTS)}

        self.next_input_port_to_arbitrate = 0 # Para arbitraje round-robin en input
        self.next_output_port_to_arbitrate = 0 # Para arbitraje round-robin en output

        self.flits_received_local = [] # Flits entregados localmente
        self.flits_sent_out = {port: [] for port in range(NUM_PORTS)}

        self.env.process(self.run())

    def run(self):
        while True:
            # Procesar todos los buffers en este ciclo
            self._process_input_buffers_sync()
            self._process_output_buffers_sync()
            yield self.env.timeout(1)

    def _process_input_buffers_sync(self):
        for port in range(NUM_PORTS):
            if len(self.input_buffers[port].items) > 0:
                # Usamos una forma no bloqueante de obtener del Store
                # SimPy Store.get() devuelve un evento, pero podemos acceder a .items
                flit = self.input_buffers[port].items.pop(0)
                
                # Asegurar que flit.destination_nodes sea un set
                dest_nodes = flit.destination_nodes
                if isinstance(dest_nodes, list):
                    dest_nodes = set(dest_nodes)
                
                # Para enrutamiento XY, tomamos el primer destino
                target = list(dest_nodes)[0]
                dest_x = target % self.mesh_dim_x
                dest_y = target // self.mesh_dim_x
                curr_x = self.id % self.mesh_dim_x
                curr_y = self.id // self.mesh_dim_x

                next_ports = []
                # Si este nodo es uno de los destinos, entregar localmente
                if self.id in dest_nodes:
                    next_ports.append(LOCAL)
                
                # Enrutamiento XY hacia el destino
                if curr_x < dest_x: next_ports.append(EAST)
                elif curr_x > dest_x: next_ports.append(WEST)
                elif curr_y < dest_y: next_ports.append(SOUTH)
                elif curr_y > dest_y: next_ports.append(NORTH)
                elif self.id == target and LOCAL not in next_ports:
                    next_ports.append(LOCAL)

                for out_port in next_ports:
                    if out_port == LOCAL:
                        flit.timestamp_arrival = self.env.now
                        self.flits_received_local.append(flit)
                    else:
                        replicated_flit = Flit(flit.packet_id, flit.source_node, self.id, list(flit.destination_nodes), 
                                               flit.flit_type, flit.timestamp_injection, flit.packet_type_str, flit.size)
                        replicated_flit.path = list(flit.path) + [self.id]
                        self.output_buffers[out_port].put(replicated_flit)

    def _process_output_buffers_sync(self):
        for port in range(NUM_PORTS):
            if port == LOCAL: continue
            if len(self.output_buffers[port].items) > 0:
                flit = self.output_buffers[port].items.pop(0)
                dest_router_id = self.get_neighbor_id(port)
                if dest_router_id != -1:
                    self.flits_sent_out[port].append(flit)



    def receive_flit(self, flit, in_port):
        # Método para que la red inyecte flits en los input_buffers de este router
        # Esto se llamará desde la clase Network
        try:
            self.input_buffers[in_port].put(flit)
        except Exception: # SimPy Store no lanza QueueFull normalmente
            print(f"[{self.env.now}] Router {self.id}: Input buffer {in_port} lleno. Flit descartado.")
            # En un simulador real, esto indicaría congestión y el flit se reintentaría

    def get_coordinates(self, node_id):
        return node_id % self.mesh_dim_x, node_id // self.mesh_dim_x

    def get_neighbor_id(self, port):
        x, y = self.get_coordinates(self.id)
        if port == NORTH: return self.id - self.mesh_dim_x if y > 0 else -1
        if port == EAST: return self.id + 1 if x < self.mesh_dim_x - 1 else -1
        if port == SOUTH: return self.id + self.mesh_dim_x if y < self.mesh_dim_y - 1 else -1
        if port == WEST: return self.id - 1 if x > 0 else -1
        return -1 # LOCAL o puerto inválido
