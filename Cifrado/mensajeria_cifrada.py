import os
import sys
import socket
import threading
import time

# =====================================================================
# CREDENCIALES PREDEFINIDAS EN LOS NODOS (Punto 3 de la tarea / Rúbrica)
# =====================================================================
USUARIOS_VALIDOS = {
    "luis_p2p": "seguridad2026",
    "rival_p2p": "distribuidos123"
}

# =====================================================================
# ALGORITMO TRADICIONAL: CIFRADO CÉSAR (Punto 2 y 4 / Rúbrica)
# Usa un desplazamiento fijo (ej. 5 posiciones) para cifrar texto plano.
# =====================================================================
DESPLAZAMIENTO = 5

def cifrar_cesar(texto, desplazamiento=DESPLAZAMIENTO):
    resultado = ""
    for char in texto:
        # Cifrar mayúsculas
        if char.isupper():
            resultado += chr((ord(char) + desplazamiento - 65) % 26 + 65)
        # Cifrar minúsculas
        elif char.islower():
            resultado += chr((ord(char) + desplazamiento - 97) % 26 + 97)
        # Mantener espacios y caracteres especiales intactos para evitar errores
        else:
            resultado += char
    return resultado

def descifrar_cesar(texto_cifrado, desplazamiento=DESPLAZAMIENTO):
    # Descifrar es simplemente aplicar el desplazamiento a la inversa
    return cifrar_cesar(texto_cifrado, -desplazamiento)

# =====================================================================
# LÓGICA DE RED Y BACKEND P2P
# =====================================================================
class NodoP2PSeguro:
    def __init__(self, mi_puerto, ip_rival, puerto_rival):
        self.mi_puerto = int(mi_puerto)
        self.ip_rival = ip_rival
        self.puerto_rival = int(puerto_rival)
        self.sock_enviar = None

    def iniciar(self):
        # 1. Levantar el servidor de escucha para recibir paquetes asíncronos
        threading.Thread(target=self._servidor_escucha, daemon=True).start()
        
        # 2. Intentar conectar con el otro nodo en segundo plano
        threading.Thread(target=self._conectar_a_rival, daemon=True).start()
        
        # 3. Ciclo principal en el hilo de la interfaz para enviar mensajes
        time.sleep(1) # Breve pausa para limpiar mensajes de conexión
        print("\n--- 🟢 SISTEMA P2P LISTO PARA ENVIAR MENSAJES ---")
        print("Escribe tu mensaje y presiona Enter (o 'salir' para terminar):\n")
        
        while True:
            try:
                mensaje_original = input()
                if mensaje_original.lower() == 'salir':
                    break
                if not mensaje_original.strip():
                    continue
                
                if self.sock_enviar:
                    # Cifrar el paquete antes de enviarlo
                    mensaje_cifrado = cifrar_cesar(mensaje_original)
                    
                    print(f"\n[🔒 LOCAL] Texto Original: '{mensaje_original}'")
                    print(f"[📡 LOCAL] Encriptando paquete enviado: '{mensaje_cifrado}'\n")
                    
                    # Enviar el paquete encriptado a la red
                    self.sock_enviar.sendall((mensaje_cifrado + "\n").encode('utf-8'))
                else:
                    print("⚠️ Aún no hay conexión con el otro nodo. Esperando...")
            except (KeyboardInterrupt, EOFError):
                break

    def _servidor_escucha(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("0.0.0.0", self.mi_puerto))
        server_socket.listen(1)
        
        conn, addr = server_socket.accept()
        buffer = ""
        while True:
            try:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    paquete_recibido, buffer = buffer.split("\n", 1)
                    
                    # PROCESAMIENTO Y DESCIFRADO (Punto 5 de la tarea)
                    mensaje_descifrado = descifrar_cesar(paquete_recibido)
                    
                    print(f"\n[📥 REMOTO] Paquete codificado recibido en red: '{paquete_recibido}'")
                    print(f"[🔓 REMOTO] Paquete decodificado: '{mensaje_descifrado}'")
                    print("──────────────────────────────────────────────────")
            except Exception:
                break

    def _conectar_a_rival(self):
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ip_rival, self.puerto_rival))
                self.sock_enviar = sock
                print(f"\n⚡ Conexión saliente establecida con el nodo rival ({self.ip_rival}:{self.puerto_rival})")
                break
            except Exception:
                time.sleep(2) # Reintentar cada 2 segundos si el rival no ha abierto

# =====================================================================
# MÓDULO DE AUTENTICACIÓN (LOGIN)
# =====================================================================
def login_sistema():
    print("=====================================================")
    print("       🔐 INICIO DE SESIÓN OBLIGATORIO DEL NODO      ")
    print("=====================================================")
    intentos = 3
    while intentos > 0:
        usuario = input("Introduce tu Usuario: ").strip()
        contrasena = input("Introduce tu Contraseña: ").strip()
        
        if usuario in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario] == contrasena:
            print("\n✅ Autenticación exitosa. Cargando entorno P2P...\n")
            time.sleep(1)
            return True
        else:
            intentos -= 1
            print(f"❌ Credenciales incorrectas. Intentos restantes: {intentos}\n")
            
    print("🚫 Acceso denegado. Saliendo del sistema.")
    return False

if __name__ == "__main__":
    # Forzar el Login antes de configurar cualquier socket
    if not login_sistema():
        sys.exit(1)
        
    os.system('clear' if os.name == 'posix' else 'cls')
    print("=== 🛠️ CONFIGURACIÓN DE RED HOMOGÉNEA P2P ===")
    mi_puerto = input("Introduce TU PUERTO de escucha local (ej. 8000): ").strip()
    ip_rival = input("Introduce la IP del nodo rival (ej. 127.0.0.1): ").strip()
    puerto_rival = input("Introduce el PUERTO del nodo rival (ej. 8001): ").strip()
    
    nodo = NodoP2PSeguro(mi_puerto, ip_rival, puerto_rival)
    nodo.iniciar()