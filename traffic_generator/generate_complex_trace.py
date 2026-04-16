import random

def generate_complex_trace(filename, num_events, num_nodes, max_timestamp):
    with open(filename, 'w') as f:
        for i in range(num_events):
            timestamp = random.randint(0, max_timestamp)
            source = random.randint(0, num_nodes - 1)
            dest = random.randint(0, num_nodes - 1)
            while dest == source:
                dest = random.randint(0, num_nodes - 1)
            
            # Formato: timestamp source dest size type
            f.write(f"{timestamp} {source} {dest} 1 complex\n")

if __name__ == "__main__":
    generate_complex_trace("complex_trace.txt", 10000, 16, 5000)
    print("Traza compleja de 10,000 eventos generada: complex_trace.txt")
