import collections

class Flit:
    SINGLE = 0

    def __init__(self, packet_id, source_node, current_node, destination_nodes, flit_type, timestamp_injection, packet_type_str, size=1):
        self.packet_id = packet_id
        self.source_node = source_node
        self.current_node = current_node
        self.destination_nodes = set(destination_nodes) # Usar un set para destinos multicast
        self.flit_type = flit_type
        self.timestamp_injection = timestamp_injection
        self.timestamp_arrival = -1 # Tiempo de llegada al destino
        self.packet_type_str = packet_type_str
        self.size = size
        self.path = [source_node] # Para trazar el camino

    def __repr__(self):
        return f"Flit(P_ID={self.packet_id}, Src={self.source_node}, Curr={self.current_node}, Dst={self.destination_nodes}, Type={self.flit_type}, Inj={self.timestamp_injection})"

class Packet:
    def __init__(self, packet_id, source_node, destination_nodes, timestamp_injection, packet_type_str):
        self.packet_id = packet_id
        self.source_node = source_node
        self.destination_nodes = set(destination_nodes) # Todos los destinos originales
        self.timestamp_injection = timestamp_injection
        self.packet_type_str = packet_type_str
        self.flits = [] # En AER, un paquete es un solo flit
        self.delivered_to = set() # Nodos a los que ya se entregó el flit
        self.delivery_times = {} # {destino: tiempo_entrega}

    def add_flit(self, flit):
        self.flits.append(flit)

    def is_fully_delivered(self):
        return self.destination_nodes == self.delivered_to

    def __repr__(self):
        return f"Packet(P_ID={self.packet_id}, Src={self.source_node}, Dst={self.destination_nodes}, Inj={self.timestamp_injection}, Delivered={self.delivered_to})"
