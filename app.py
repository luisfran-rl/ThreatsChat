import os
import sys
from p2p_backend import P2PNode

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_screen()
    print("=== 🌐 CONFIGURACIÓN INICIAL DEL NODO P2P ===")
    
    # En Codespaces usamos localhost (127.0.0.1) para simular los nodos de forma interna
    local_ip = "127.0.0.1" 
    local_port = input("Introduce el PUERTO LOCAL para este nodo (ej. 5001): ")
    
    print("\n=== 🎯 CONFIGURACIÓN DEL DESTINATARIO ===")
    target_ip = "127.0.0.1"
    target_port = input("Introduce el PUERTO DESTINO al que vas a enviar (ej. 5002): ")

    # Función callback que el hilo del servidor llamará cuando reciba un paquete
    def registrar_mensaje(mensaje):
        print(f"\n📩 {mensaje}")
        print("Escribe un mensaje (o 'salir'): ", end="", flush=True)

    # Inicializar el nodo backend
    nodo = P2PNode(local_ip, local_port, registrar_mensaje)
    
    if nodo.start_server():
        clear_screen()
        print(f"=== 🟢 NODO ACTIVO ===")
        print(f"Escuchando en -> {local_ip}:{local_port}")
        print(f"Apuntando a  -> {target_ip}:{target_port}")
        print("========================================\n")
    else:
        print("No se pudo iniciar el nodo. Verifica el puerto.")
        sys.exit()

    # Ciclo del hilo principal: Se queda esperando que tú escribas algo para enviar
    try:
        while True:
            msg = input("Escribe un mensaje (o 'salir'): ")
            if msg.lower() == 'salir':
                break
            if msg.strip():
                # Llama a la función cliente para mandar el paquete
                exito = nodo.send_message(target_ip, target_port, msg)
                if exito:
                    print(f"   [Enviado con éxito] -> {msg}")
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCerrando nodo de forma segura y liberando puertos...")
        nodo.stop()
        print("¡Adiós!")

if __name__ == "__main__":
    main()