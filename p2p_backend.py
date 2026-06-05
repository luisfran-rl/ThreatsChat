import socket
import threading
import time

class P2PNode:
    def __init__(self, local_ip, local_port, on_message_received):
        self.local_ip = local_ip
        self.local_port = int(local_port)
        self.on_message_received = on_message_received
        self.server_socket = None
        self.is_running = False

    def start_server(self):
        """
        PASO 1: Crea un hilo independiente para el servidor.
        Esto permite que el ciclo de escucha corra en el fondo sin congelar el programa.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # NOTA DEL PUNTO 7: Evita que el puerto se quede bloqueado al cerrar el programa
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.local_ip, self.local_port))
            self.server_socket.listen(5)
            self.is_running = True
            
            # Creamos el hilo secundario y lo iniciamos
            server_thread = threading.Thread(target=self._listen_loop, daemon=True)
            server_thread.start()
            return True
        except Exception as e:
            self.on_message_received(f"[Error al iniciar servidor]: {e}")
            return False

    def _listen_loop(self):
        """
        PASO 3: Ciclo infinito (while) para recibir múltiples paquetes
        sin que el servidor se apague tras el primer mensaje.
        """
        while self.is_running:
            try:
                # El hilo se queda aquí pausado esperando una conexión entrante
                client_conn, client_addr = self.server_socket.accept()
                data = client_conn.recv(1024).decode('utf-8')
                if data:
                    # Envia el mensaje recibido de vuelta a la interfaz para mostrarlo
                    self.on_message_received(f"[{client_addr[0]}:{client_addr[1]}]: {data}")
                client_conn.close()
            except Exception:
                # Si el socket se cierra de forma segura, rompemos el ciclo
                break

    def send_message(self, target_ip, target_port, message):
        """
        PASO 2: Función de cliente para enviar datos (TCP)
        """
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((target_ip, int(target_port)))
            client_socket.send(message.encode('utf-8'))
            client_socket.close()
            return True
        except Exception as e:
            self.on_message_received(f"[Error de envío a {target_ip}:{target_port}]: {e}")
            return False

    def stop(self):
        """Cierre seguro de sockets para liberar los puertos"""
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()