from scapy.all import *
import time
import json
import argparse
import numpy as np
import math
import binascii
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.http import HTTP, HTTPRequest
import paho.mqtt.publish as publish  
import threading
from queue import Queue
from ctypes import *

#Map the JSON file to fields compatible with scapy
FIELD_MAP = {
    "IntField": IntField,
    "StrField": StrField,
    "ByteField": ByteField,
    "ShortField": ShortField,
    "LongField": LongField,
    "IPField": IPField,
    "MACField": MACField,
    "EnumField": EnumField,
    
}
#Map the scapy fields
def get_scapy_field(field):

    field_class = FIELD_MAP.get(field['tipo'])
    if not field_class:
        raise ValueError(f"Tipo de campo não suportado: {field['tipo']}")
    return field_class(field['nome'], default=field.get('default', 0))
    
# Generates poisson distribution
def generate_uniform():
    return np.random.uniform()



def poisson_distribution(lambda_):
    min_val, max_val = max(0, lambda_ - math.sqrt(lambda_)), lambda_ + math.sqrt(lambda_)
    
    if lambda_ < 30:
        L = math.exp(-lambda_)
        p = 1.0
        k = 0

        while p > L:
            k += 1
            p *= generate_uniform()

        k -= 1  # Ajuste porque o loop incrementa uma vez a mais
    else:
        # Define as variáveis fora do loop para garantir seu escopo
        b = 0.931 + 2.53 * math.sqrt(lambda_)
        a = -0.059 + 0.02483 * b
        inv_alpha = 1.1239 + 1.1328 / (b - 3.4)
        v_r = 0.9277 - 3.6224 / (b - 2)

        while True:
            U = generate_uniform() - 0.5
            V = generate_uniform()
            us = 0.5 - abs(U)

            if us < 0.013 and V > us:
                continue

            k = math.floor((2 * a / us + b) * U + lambda_ + 0.43)
            if k < 0 or k < min_val or k > max_val:
                continue

            if us >= 0.07 and V <= v_r:
                break

            if us < 0.013 and V <= math.exp(-0.5 * k * k / lambda_):
                break

            if math.log(V) + math.log(inv_alpha) - math.log(a / (us * us) + b) <= -lambda_ + k * math.log(lambda_) - math.lgamma(k + 1):
                break

    return int(max(min_val, min(k, max_val)))



 
# Generates TCP traffic
def generate_tcp_traffic(duration, messages_per_second, destination_ip, interface, port):
 
    messages_per_second_array = [poisson_distribution(messages_per_second) for _ in range(duration)]

    def send_packets(num_messages, start_time, second):
        for _ in range(num_messages):
            timestamp = str(time.time())
            timestamp = timestamp 
            print("Sending "+timestamp)
            packet = IP(dst=destination_ip) / TCP(dport=port) / timestamp
            send(packet, iface=interface, verbose=0)
 
        while time.time() < start_time + second + 1:
            time.sleep(0.001)  

    start_time = time.time()

    for second, num_messages in enumerate(messages_per_second_array):
        
        send_packets(num_messages, start_time, second)

    print("Finalizado o envio de pacotes.")



def generate_udp_traffic(duration, messages_per_second, destination_ip, interface, port):
    
    messages_per_second_array = [poisson_distribution(messages_per_second) for _ in range(duration)]

    def send_packets(num_messages, start_time, second):
        for _ in range(num_messages):
            timestamp = str(time.time())
            timestamp = timestamp 
            print("Sending "+timestamp)
            packet = IP(dst=destination_ip) / UDP(dport=port) / timestamp
            send(packet, iface=interface, verbose=0)
        
        while time.time() < start_time + second + 1:
            time.sleep(0.001)  

    start_time = time.time()

    for second, num_messages in enumerate(messages_per_second_array):
        
        send_packets(num_messages, start_time, second)

    print("Finalizado o envio de pacotes.")


# Generates MQTT traffic
def generate_mqtt_traffic(duration, messages_per_second, destination_ip, topic):
    start_time = time.time()
    next_send_time = start_time

    while time.time() - start_time < duration:
        
        if time.time() > next_send_time:
            next_send_time = time.time() + 1  # Próximo segundo
            num_messages = poisson_distribution(messages_per_second)
            

            interval = 1 / num_messages if num_messages > 0 else 1  

            for _ in range(num_messages):
                current_time = time.time()
                if current_time >= next_send_time:
                    break  

                message = str(current_time)
                print("Sending " + message)
                publish.single(topic, message, hostname=destination_ip)
                
                time.sleep(interval - (time.time() - current_time))

# Generates HTTP traffic
def generate_http_traffic(duration, messages_per_second, destination_ip, headers, interface,port):
    start_time = time.time()
    next_second = start_time + 1
    
    for _ in range(duration):
        current_time = time.time()
      
        while current_time < next_second:
            time.sleep(next_second - current_time)
            current_time = time.time()

        num_messages = poisson_distribution(messages_per_second)
        print(f"Enviando {num_messages} mensagens")

        for _ in range(num_messages):
            timestamp = str(time.time())
            print("Sending " + timestamp)

            formatted_headers = '\r\n'.join(f"{key}: {value}" for key, value in headers.items())
            payload = f"GET / HTTP/1.1\r\nHost: {destination_ip}\r\n{formatted_headers}\r\n\r\n{timestamp}"
            packet = IP(dst=destination_ip) / TCP(dport=port) / Raw(load=payload)
            send(packet, iface=interface, verbose=0)

            if num_messages > 1:
                time.sleep(1.0 / num_messages)

        next_second += 1  



# Generates Custom Traffic
def generate_custom_traffic(duration, messages_per_second, destination_ip, interface, json_file):
    with open(json_file, 'r') as file:
        protocol_def = json.load(file)

    class MeuProtocoloDinamico(Packet):
        name = protocol_def['nome']
        fields_desc = [get_scapy_field(field) for field in protocol_def['campos']]

    start_time = time.time()
    next_send_time = start_time

    for _ in range(duration):
        current_time = time.time()
        
        while current_time < next_send_time:
            time.sleep(next_send_time - current_time)
            current_time = time.time()

        next_send_time += 1  
        num_messages = poisson_distribution(messages_per_second)
        
        interval = 1 / num_messages if num_messages > 0 else 1  

        for _ in range(num_messages):
            current_time = time.time()
            if current_time >= next_send_time:
                break  
            
            packet_fields = {field['nome']: field['default'] for field in protocol_def['campos']}
            packet_fields['timestamp'] = int(current_time)
            print("Sending "+str(int(current_time)))
            packet = IP(dst=destination_ip) / MeuProtocoloDinamico(**packet_fields)
            send(packet, iface=interface, verbose=1)
            packet.show()
            
            time.sleep(interval - (time.time() - current_time))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--time', type=int, required=True, help='Duration of the traffic generation in seconds')
    parser.add_argument('--mean', type=float, required=True, help='Average number of messages per second')
    parser.add_argument('--target', type=str, required=True, help='Destination IP address for the traffic')
    parser.add_argument('--port', type=int, help='Destination Port for the traffic',default=12345)
    parser.add_argument('--interface', type=str, required=True, help='Network interface to use')
    parser.add_argument('--protocol', type=str, required=True, help='Protocol type (TCP, UDP, MQTT, HTTP, XML, Custom)')
    parser.add_argument('--topic', type=str, help='MQTT topic (required for MQTT)')
    parser.add_argument('--header', action='append', help='HTTP headers (required for HTTP)')
    parser.add_argument('--custom', type=str, help='JSON file for custom protocol (required for Custom)')

    args = parser.parse_args()

    if args.protocol.upper() == "TCP":
        generate_tcp_traffic(args.time, args.mean, args.target, args.interface, args.port)
    elif args.protocol.upper() == "UDP":
        generate_udp_traffic(args.time, args.mean, args.target, args.interface, args.port)
    elif args.protocol.upper() == "MQTT":
        if not args.topic:
            raise ValueError("MQTT topic is required for MQTT protocol")
        generate_mqtt_traffic(args.time, args.mean, args.target, args.topic)
    elif args.protocol.upper() == "HTTP":
        
        if not args.header:
            raise ValueError("HTTP headers are required for HTTP protocol")

        headers = {h.split(":")[0]: h.split(":")[1].strip() for h in args.header}
        generate_http_traffic(args.time, args.mean, args.target, headers, args.interface, args.port)
    elif args.protocol.upper() == "CUSTOM":
        if not args.custom:
            raise ValueError("JSON file is required for Custom protocol")
        generate_custom_traffic(args.time, args.mean, args.target, args.interface, args.custom)
    else:
        raise ValueError("Unsupported protocol")

