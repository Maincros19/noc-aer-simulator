# -*- coding: utf-8 -*-
import numpy as np
import torch
import torch.nn as nn
import torchvision
from torch.utils.data import DataLoader
import tonic
import snntorch as snn
from snntorch import surrogate
from snntorch import functional as SF
from snntorch import utils
import os

# Reproducibilidad
torch.manual_seed(42)
np.random.seed(42)

device = torch.device("cpu")
print(f"Hardware: {device}")

# Carga de Datos
sensor_size = tonic.datasets.NMNIST.sensor_size
transform = tonic.transforms.Compose([
    tonic.transforms.ToFrame(sensor_size=sensor_size, n_time_bins=30),
    torch.from_numpy
])

trainset = tonic.datasets.NMNIST(save_to='./data', train=True, transform=transform)
testset = tonic.datasets.NMNIST(save_to='./data', train=False, transform=transform)

trainloader = DataLoader(trainset, batch_size=64, shuffle=True)
testloader = DataLoader(testset, batch_size=64, shuffle=False)

# Definición de la Red
spike_grad = surrogate.atan()
beta = 0.5

class CSNN(nn.Module):
    def __init__(self, beta, spike_grad):
        super().__init__()
        self.conv1 = nn.Conv2d(2, 12, 5)
        self.snn1 = snn.Leaky(beta=beta, spike_grad=spike_grad)
        self.pool1 = nn.MaxPool2d(2)
        self.conv2 = nn.Conv2d(12, 32, 5)
        self.snn2 = snn.Leaky(beta=beta, spike_grad=spike_grad)
        self.pool2 = nn.MaxPool2d(2)
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(32*5*5, 10)
        self.snn3 = snn.Leaky(beta=beta, spike_grad=spike_grad)

    def forward(self, x, mem1, mem2, mem3):
        cur = self.conv1(x)
        spk1, mem1 = self.snn1(cur, mem1)
        cur = self.pool1(spk1)
        cur = self.conv2(cur)
        spk2, mem2 = self.snn2(cur, mem2)
        cur = self.pool2(spk2)
        cur = self.flatten(cur)
        cur = self.fc1(cur)
        spk_out, mem3 = self.snn3(cur, mem3)
        return spk_out, spk1, spk2, mem1, mem2, mem3

net = CSNN(beta, spike_grad).to(device)

# Entrenamiento (100 iteraciones)
optimizer = torch.optim.Adam(net.parameters(), lr=2e-3)
loss_fn = SF.ce_rate_loss()

print("Iniciando entrenamiento (100 iteraciones)...")
net.train()
iter_count = 0
max_iters = 100

for data, targets in trainloader:
    data = data.float().to(device).transpose(0, 1) # (time, batch, channel, h, w)
    targets = targets.to(device)
    
    mem1 = net.snn1.init_leaky()
    mem2 = net.snn2.init_leaky()
    mem3 = net.snn3.init_leaky()
    
    spk_rec = []
    for step in range(data.size(0)):
        spk_out, _, _, mem1, mem2, mem3 = net(data[step], mem1, mem2, mem3)
        spk_rec.append(spk_out)
    
    spk_rec = torch.stack(spk_rec)
    loss_val = loss_fn(spk_rec, targets)
    
    optimizer.zero_grad()
    loss_val.backward()
    optimizer.step()
    
    iter_count += 1
    if iter_count % 10 == 0:
        acc = SF.accuracy_rate(spk_rec, targets)
        print(f"Iteración {iter_count}/{max_iters} | Loss: {loss_val.item():.4f} | Precisión: {acc*100:.2f}%")
    if iter_count >= max_iters:
        break

# Generación de Traza
snn_layer_to_nodes_mapping = {
    'input': [0],
    'snn1': [1, 2, 3, 4, 5, 6],
    'snn2': [7, 8, 9, 10, 11, 12, 13, 14],
    'output': [15]
}

def generate_trace(net, data_sample, mapping, filename="nmnist_trace.txt"):
    net.eval()
    trace_events = []
    mem1 = net.snn1.init_leaky()
    mem2 = net.snn2.init_leaky()
    mem3 = net.snn3.init_leaky()
    
    with torch.no_grad():
        for step in range(data_sample.size(0)):
            spk_out, spk1, spk2, mem1, mem2, mem3 = net(data_sample[step], mem1, mem2, mem3)
            
            # Input spikes
            if (data_sample[step] > 0).any():
                for dst in mapping['snn1']:
                    trace_events.append(f"{step} {mapping['input'][0]} {dst} 1 input")
            
            # SNN1 spikes
            spk1_idx = (spk1 > 0).nonzero(as_tuple=False)
            for s in spk1_idx:
                src = mapping['snn1'][s[1].item() % len(mapping['snn1'])]
                for dst in mapping['snn2']:
                    trace_events.append(f"{step} {src} {dst} 1 snn1")
            
            # SNN2 spikes
            spk2_idx = (spk2 > 0).nonzero(as_tuple=False)
            for s in spk2_idx:
                src = mapping['snn2'][s[1].item() % len(mapping['snn2'])]
                for dst in mapping['output']:
                    trace_events.append(f"{step} {src} {dst} 1 snn2")

    with open(filename, 'w') as f:
        for event in trace_events:
            f.write(event + "\n")
    print(f"Traza real generada: {filename} con {len(trace_events)} eventos.")

print("Generando traza a partir de una muestra del test set...")
data_sample, _ = next(iter(testloader))
single_stimulus = data_sample[0:1].float().to(device).transpose(0, 1)
generate_trace(net, single_stimulus, snn_layer_to_nodes_mapping)
