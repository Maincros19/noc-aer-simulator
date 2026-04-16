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
            # Etapa 1: Arbitraje de Entrada (Input Arbitration - IA) y Buffer de Entrada (Input Buffer - IB)
            # Los flits llegan a los input_buffers de forma asíncrona a través de receive_flit

            # Etapa 2: Enrutamiento (Routing - RC) y Asignación de Switch (Switch Allocation - SA)
            # Mover flits de input_buffers a output_buffers
            yield self.env.process(self._process_input_buffers())

            # Etapa 3: Asignación de Puerto (Port Allocation - PA) y Travesía de Enlace (Link Traversal - LT)
            # Mover flits de output_buffers a los routers vecinos o localmente
            yield self.env.process(self._process_output_buffers())

            yield self.env.timeout(1) # Un ciclo de reloj

    def _process_input_buffers(self):
        # Arbitrar entre los input_buffers y mover flits a los output_buffers
        for _ in range(NUM_PORTS): # Intentar arbitrar todos los puertos una vez por ciclo
            port_to_check = self.next_input_port_to_arbitrate
            self.next_input_port_to_arbitrate = (self.next_input_port_to_arbitrate + 1) % NUM_PORTS

            if port_to_check == LOCAL: # Flits inyectados localmente
                # La inyección local se maneja directamente en la red, no a través de un buffer de entrada
                continue

            if len(self.input_buffers[port_to_check].items) > 0: # Si hay flits en el buffer
                flit = yield self.input_buffers[port_to_check].get() # Obtener el flit
                
                # Lógica de Enrutamiento XY (simplificada para malla)
                dest_x = list(flit.destination_nodes)[0] % self.mesh_dim_x # Asumimos un destino principal para enrutamiento
                dest_y = list(flit.destination_nodes)[0] // self.mesh_dim_x
                
                curr_x = self.id % self.mesh_dim_x
                curr_y = self.id // self.mesh_dim_x

                next_ports = []

                if flit.destination_nodes == {self.id}: # Si el flit es para este router
                    next_ports.append(LOCAL)
                else:
                    # Enrutamiento XY
                    if curr_x < dest_x: # Necesita ir al Este
                        next_ports.append(EAST)
                    elif curr_x > dest_x: # Necesita ir al Oeste
                        next_ports.append(WEST)
                    elif curr_y < dest_y: # Necesita ir al Sur
                        next_ports.append(SOUTH)
                    elif curr_y > dest_y: # Necesita ir al Norte
                        next_ports.append(NORTH)
                    else: # Ya está en el nodo X,Y pero no es el destino final (multicast a otros nodos)
                        # Esto es una simplificación. En un NoC real, el multicast es más complejo.
                        # Aquí, si ya está en el nodo correcto, lo enviamos localmente y a otros destinos si los hay.
                        next_ports.append(LOCAL)
                        # Para multicast, si hay múltiples destinos, se debería replicar el flit
                        # y enviarlo por diferentes puertos.
                        # Por ahora, el enrutamiento XY solo busca el primer destino.
                        # La replicación para multicast se hará en la etapa de SA/PA.

                # Lógica de Asignación de Switch (SA) y replicación para Multicast
                for dest_node in flit.destination_nodes:
                    if dest_node == self.id: # Si este router es uno de los destinos
                        if LOCAL not in next_ports: # Asegurarse de que se entregue localmente
                            next_ports.append(LOCAL)

                # Para cada puerto de salida determinado por el enrutamiento y multicast
                for out_port in next_ports:
                    if out_port == LOCAL:
                        # Entregar localmente inmediatamente (no pasa por output_buffer)
                        flit.timestamp_arrival = self.env.now
                        self.flits_received_local.append(flit)
                        # Marcar el paquete como entregado a este destino
                        # Esto se manejará en la clase Network para actualizar el Packet original
                    else:
                        # Replicar el flit para cada puerto de salida si es multicast
                        replicated_flit = Flit(flit.packet_id, flit.source_node, self.id, list(flit.destination_nodes), 
                                               flit.flit_type, flit.timestamp_injection, flit.packet_type_str, flit.size)
                        replicated_flit.path = list(flit.path) + [self.id] # Actualizar camino
                        
                        # Intentar poner el flit en el output_buffer
                        try:
                            yield self.output_buffers[out_port].put(replicated_flit)
                        except Exception: # SimPy Store no lanza QueueFull normalmente # Esto no debería ocurrir con Store
                            print(f"[{self.env.now}] Router {self.id}: Output buffer {out_port} lleno. Flit descartado.")
                            # En un simulador real, esto indicaría congestión y el flit se reintentaría

    def _process_output_buffers(self):
        # Arbitrar entre los output_buffers y enviar flits a los enlaces
        for _ in range(NUM_PORTS): # Intentar arbitrar todos los puertos una vez por ciclo
            port_to_check = self.next_output_port_to_arbitrate
            self.next_output_port_to_arbitrate = (self.next_output_port_to_arbitrate + 1) % NUM_PORTS

            if port_to_check == LOCAL: # No se envía nada localmente desde aquí
                continue

            if len(self.output_buffers[port_to_check].items) > 0: # Si hay flits en el buffer
                flit = yield self.output_buffers[port_to_check].get() # Obtener el flit
                
                # Enviar el flit a través del enlace de red
                # La lógica de envío real se manejará en la clase Network
                self.flits_sent_out[port_to_check].append(flit) # Para métricas
                # La clase Network se encargará de pasarlo al router destino

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
