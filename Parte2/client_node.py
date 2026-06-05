import os
import sys
import socket
import threading

class ClienteP2P:
    def __init__(self, local_port, server_ip="127.0.0.1", server_port=6000):
        self.local_ip = "127.0.0.1"
        self.local_port = int(local_port)
        self.server_ip = server_ip
        self.server_port = int(server_port)
        self.server_socket = None
        self.is_running = False

    def start_escucha(self):
        """Servidor interno del cliente: Escucha permanentemente lo que el Servidor Central retransmita."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.local_ip, self.local_port))
            self.server_socket.listen(5)
            self.is_running = True
            threading.Thread(target=self._listen_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"❌ Error al abrir puerto de escucha local {self.local_port}: {e}")
            return False

    def _listen_loop(self):
        while self.is_running:
            try:
                conn, addr = self.server_socket.accept()
                data = conn.recv(1024).decode('utf-8')
                if data:
                    # Imprime de forma limpia el mensaje retransmitido que llegó
                    print(f"\n📩 [Broadcast Recibido]: {data}")
                    print("Escribe un mensaje (o 'salir'): ", end="", flush=True)
                conn.close()
            except Exception:
                break

    def registrarse_en_servidor(self):
        """Nota técnica: Envía el paquete principal informando por qué puerto escuchará."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, self.server_port))
            # Enviamos la bandera de REGISTRO seguida de nuestro puerto local
            mensaje_registro = f"REGISTRO:{self.local_port}"
            sock.send(mensaje_registro.encode('utf-8'))
            respuesta = sock.recv(1024).decode('utf-8')
            sock.close()
            return respuesta == "OK"
        except Exception as e:
            print(f"❌ No se pudo conectar al Servidor Central: {e}")
            return False

    def enviar_mensaje_a_sala(self, mensaje):
        """PUNTO 2: Envía el paquete predefiniendo únicamente al nodo servidor central."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, self.server_port))
            # Enviamos el mensaje limpio, el servidor se encargará de distribuirlo
            sock.send(mensaje.encode('utf-8'))
            sock.close()
            return True
        except Exception:
            print("⚠️ Error al enviar el mensaje al servidor central.")
            return False

    def stop(self):
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()

def main():
    os.system('clear')
    print("=== 👤 NUEVO NODO CLIENTE P2P ===")
    local_port = input("Introduce el PUERTO LOCAL por donde escuchará este cliente (ej. 5001, 5002): ")

    cliente = ClienteP2P(local_port)
    
    # 1. Abrimos su hilo/puerto de escucha
    if not cliente.start_escucha():
        sys.exit()
        
    # 2. Nos registramos automáticamente en el Servidor Central
    print("🔄 Conectando y registrando en el Servidor Central...")
    if not cliente.registrarse_en_servidor():
        print("❌ Registro fallido. Asegúrate de que central_server.py esté corriendo.")
        cliente.stop()
        sys.exit()

    os.system('clear')
    print(f"=== 🟢 CLIENTE CONECTADO (Puerto Escucha: {local_port}) ===")
    print("Todo lo que escribas se enviará al Servidor Central y se replicará a los demás.\n")

    try:
        while True:
            msg = input("Escribe un mensaje (o 'salir'): ")
            if msg.lower() == 'salir':
                break
            if msg.strip():
                cliente.enviar_mensaje_a_sala(f"Nodo {local_port}: {msg}")
    finally:
        print("\nLiberando recursos del cliente...")
        cliente.stop()

if __name__ == "__main__":
    main()