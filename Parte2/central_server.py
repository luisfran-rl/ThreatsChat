import socket
import threading

# Estructura de datos en memoria RAM (Lista de tuplas) para almacenar los nodos (IP, Puerto)
nodos_registrados = []
# Candado de hilos para evitar errores si dos nodos se registran exactamente al mismo tiempo
nodos_lock = threading.Lock()

def retransmitir_mensaje(mensaje_texto, remitente_addr):
    """
    PUNTO 3: Reenvía el paquete recibido a todos los nodos 
    que se encuentren previamente registrados.
    """
    with nodos_lock:
        print(f"📢 Retransmitiendo mensaje a {len(nodos_registrados)} nodos registrados...")
        for ip, puerto in nodos_registrados:
            # Opcional: Evitamos enviarle el mensaje de vuelta a quien lo escribió originalmente
            if (ip, int(puerto)) == remitente_addr:
                continue
                
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((ip, int(puerto)))
                client_socket.send(mensaje_texto.encode('utf-8'))
                client_socket.close()
            except Exception:
                print(f"⚠️ No se pudo retransmitir al nodo {ip}:{puerto}. ¿Se desconectó?")

def manejar_cliente(conn, addr):
    """Maneja las conexiones entrantes al servidor central."""
    try:
        data = conn.recv(1024).decode('utf-8')
        if not data:
            return

        # PUNTO 1: Verificar si es un paquete de registro inicial
        if data.startswith("REGISTRO:"):
            # Formato esperado: "REGISTRO:5001" (el cliente nos manda su puerto de escucha)
            puerto_cliente = data.split(":")[1]
            direccion_completa = (addr[0], int(puerto_cliente))
            
            with nodos_lock:
                if direccion_completa not in nodos_registrados:
                    nodos_registrados.append(direccion_completa)
                    print(f"✅ Nuevo nodo registrado con éxito: {direccion_completa[0]}:{direccion_completa[1]}")
                    print(f"📋 Lista actual de nodos: {nodos_registrados}")
            
            conn.send("OK".encode('utf-8')) # Confirmación al cliente
            
        else:
            # Si no es registro, es un mensaje de chat ordinario para retransmitir
            print(f"📩 Paquete recibido desde {addr[0]}:{addr[1]} -> '{data}'")
            retransmitir_mensaje(data, addr)
            
    except Exception as e:
        print(f"❌ Error manejando la conexión: {e}")
    finally:
        conn.close()

def iniciar_servidor_central():
    server_ip = "127.0.0.1"
    server_port = 6000 # Puerto fijo predefinido para el Servidor Central
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((server_ip, server_port))
        server.listen(100)
        print(f"=== 🏛️ SERVIDOR CENTRAL EN ESTRELLA ACTIVO ===")
        print(f"Escuchando registros en {server_ip}:{server_port}")
        print("================================================\n")
        
        while True:
            conn, addr = server.accept()
            # Creamos un hilo por cada petición entrante para soportar cantidad indefinida de conexiones
            threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()
            
    except KeyboardInterrupt:
        print("\nApagando Servidor Central de manera segura...")
    finally:
        server.close()

if __name__ == "__main__":
    iniciar_servidor_central()