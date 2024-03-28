from scapy.all import *
import argparse
import paho.mqtt.client as mqtt
import json
import time
import binascii
#Field map to create custom protocols
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
#Function to convert json to custom protocols
def get_scapy_field(field):
    tipo = field['tipo']
    nome = field['nome']
    default = field.get('default', None)
    
    extra_args = field.get('args', [])

    field_class = FIELD_MAP.get(tipo)
    
    if not field_class:
        raise ValueError(f"Tipo de campo não suportado: {tipo}")

    if tipo == "EnumField":
    
        return field_class(nome, default, *extra_args)
    else:
        return field_class(nome, default)
    
# Function to calculate the delay between the creation and arrival of the packet
def calculate_delay(received_timestamp):
    current_time = time.time()
    try:
        received_timestamp = float(received_timestamp)
        delay = current_time - received_timestamp
        
        delay = round(delay, 2)
       
        print(f"Delay: {delay:.2f} ms")  
    except ValueError:
        print("Invalid timestamp received.")

# Packet Handler 
        
def handle_packet(packet):
    
    if packet.haslayer(TCP) and packet[TCP].dport == args.port:
        if packet.haslayer(Raw):
            payload = packet[Raw].load.decode(errors="ignore")
            if any(method in payload for method in ["GET ", "POST ", "PUT ", "DELETE ", "HEAD "]) and "HTTP" in payload:
                lines = payload.split('\r\n')
                timestamp = lines[-1]
               
                try:
                    delay = calculate_delay(timestamp)
                    
                except ValueError as e:
                    print(f"Error processing timestamp: {e}")
            else:
                if packet.haslayer(TCP) and packet.haslayer(Raw):
                    data = packet[Raw].load.decode()
                    if "GET" in data:
                        lines = data.split('\r\n')
                        timestamp = lines[-1]  
                        calculate_delay(timestamp)
                    else:
                        lines = data.split('\r\n')
                        timestamp = lines[-1] 
                        calculate_delay(timestamp)
        else:
            print("TCP packet without Raw layer.")
    
   
    if packet.haslayer(UDP):
        # Extraindo a carga útil da camada UDP
        udp_layer = packet.getlayer(UDP)
        if udp_layer and udp_layer.payload:
            # Decodifica a carga útil para string
            udp_data = bytes(udp_layer.payload).decode('utf-8').strip()
            
            # A carga útil agora é uma string do timestamp
            try:
                # O timestamp é a carga útil inteira neste caso
                received_timestamp = float(udp_data)
                current_time = time.time()
                calculate_delay(current_time)
                
            except ValueError as e:
                print(f"Erro ao processar o timestamp: {e}")
   

    
    

# Listen network for TCP, HTTP and UDP packets
def listen_network(protocol, port):
    filter_str = f"{protocol.lower()} port {port}"
    if protocol.lower() == "http":
        filter_str = f"tcp port {port}"
    else:
        filter_str = f"{protocol.lower()} port {port}" 
    print(f"Listening on {filter_str}")
    sniff(filter=filter_str, prn=handle_packet, store=0)

# Callback for MQTT messages
def on_message(client, userdata, message):
    #print(f"Message received on topic {message.topic}: {message.payload}")
    #print("Received Payload")
    #print(message.payload.decode())
    calculate_delay(message.payload.decode())

# Listen MQTT Broker
def listen_mqtt(broker_address, topic):
    client_id = f'python-mqtt-{random.randint(0, 1000)}'
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
    client.on_message = on_message
    client.connect(broker_address)
    client.subscribe(topic)
    client.loop_forever()

# Listem Custom Protocol
def listen_custom(protocol_file):
    with open(protocol_file, 'r') as file:
        protocol_def = json.load(file)

    class MyProtocol(Packet):
        name = protocol_def['nome']
        fields_desc = [get_scapy_field(field) for field in protocol_def['campos']]

    
    bind_layers(IP, MyProtocol)

    def custom_handler(packet):
     if packet.haslayer(MyProtocol):
        print(f"Received custom packet: {packet[MyProtocol].summary()}")
        if 'timestamp' in packet[MyProtocol].fields:
            timestamp = packet[MyProtocol].timestamp
            print(f"Timestamp recebido: {timestamp}")
            try:
                # Garante que o timestamp é um número antes de calcular o atraso
                timestamp = float(timestamp)
                delay = calculate_delay(time.time() - timestamp)
                print(f"Delay: {delay} seconds")
            except ValueError:
                print("O timestamp recebido não é um número válido.")
        else:
            print("Campo de timestamp não encontrado no pacote.")
            
    print("Listening for custom protocol packets...")
    sniff(prn=custom_handler, store=0)

# Lê a definição do protocolo do arquivo JSON
def load_protocol_definition(json_file):
    with open(json_file, 'r') as file:
        return json.load(file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', required=True, help='Protocol to listen to (TCP, UDP, MQTT, CUSTOM)')
    parser.add_argument('--port', type=int, help='Port to listen on',default=12345)
    parser.add_argument('--source', help='Broker address for MQTT')
    parser.add_argument('--topic', help='MQTT topic (required for MQTT)')
    parser.add_argument('--custom', help='JSON file for custom protocol (required for CUSTOM)')

    args = parser.parse_args()
    if args.protocol.upper() == "HTTP" and not args.port:
        args.port = 80

    # Lógica para escutar baseada no protocolo
    if args.protocol.upper() in ["TCP", "UDP", "HTTP"]:
        listen_network(args.protocol, args.port)
    
    elif args.protocol.upper() == "MQTT":
        if not args.source or not args.topic:
            raise ValueError("Broker address and topic are required for MQTT protocol")
        listen_mqtt(args.source, args.topic)
    elif args.protocol.upper() == "CUSTOM":
        
        if not args.custom:
            raise ValueError("JSON file is required for Custom protocol")
        listen_custom(args.custom)
   
    
    else:
        raise ValueError("Unsupported protocol")
