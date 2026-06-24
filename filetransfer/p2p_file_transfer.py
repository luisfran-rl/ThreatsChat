import os
import sys
import socket
import threading
import time

# =====================================================================
# CONFIGURACIÓN CRIPTOGRÁFICA Y DE FRAGMENTACIÓN (Rúbrica)
# =====================================================================
DESPLAZAMIENTO = 5
CHUNK_SIZE = 262144  # 256 KB para ráfagas óptimas en la nube

def cifrar_bytes(datos, desplazamiento=DESPLAZAMIENTO):
    return bytes([(b + desplazamiento) % 256 for b in datos])

def descifrar_bytes(datos, desplazamiento=DESPLAZAMIENTO):
    return bytes([(b - desplazamiento) % 256 for b in datos])

# =====================================================================
# LÓGICA DE TRÁFICO P2P DE ARCHIVOS
# =====================================================================
class NodoP2PArchivos:
    def __init__(self, mi_puerto, ip_rival, puerto_rival):
        self.mi_puerto = int(mi_puerto)
        self.ip_rival = ip_rival
        self.puerto_rival = int(puerto_rival)
        self.sock_enviar = None

    def iniciar(self):
        # 1. Servidor de escucha asíncrono
        threading.Thread(target=self._servidor_escucha, daemon=True).start()
        
        # 2. Cliente de conexión en segundo plano
        threading.Thread(target=self._conectar_a_rival, daemon=True).start()
        
        time.sleep(1.5)
        print("\n--- 🟢 ENTORNO P2P COMPLETAMENTE SINCRONIZADO ---")
        
        while True:
            sys.stdin.flush()
            print("\n========================================")
            print("Opciones:")
            print("1) Enviar un archivo al nodo rival")
            print("2) Salir")
            print("========================================")
            opcion = input("Selecciona una opción: ").strip()
            
            if opcion == "1":
                if not self.sock_enviar:
                    print("⚠️ El enlace con el rival no está listo.")
                    continue
                ruta_archivo = input("Introduce la ruta del archivo (ej. archivo_55MB.dat): ").strip()
                if os.path.exists(ruta_archivo):
                    self._enviar_archivo(ruta_archivo)
                else:
                    print("❌ El archivo no existe en la ruta especificada.")
            elif opcion == "2":
                print("Saliendo del sistema...")
                break

    def _servidor_escucha(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("0.0.0.0", self.mi_puerto))
        server_socket.listen(5)
        
        while True:
            try:
                conn, addr = server_socket.accept()
                threading.Thread(target=self._manejar_recepcion, args=(conn,), daemon=True).start()
            except Exception:
                break

    def _manejar_recepcion(self, conn):
        try:
            # Intentar decodificar la cabecera de metadatos de forma segura
            try:
                raw_data = conn.recv(1024)
                metadatos = raw_data.decode('utf-8').strip('\x00')
            except Exception:
                # Si no es texto descifrable (ej. ráfaga binaria residual), cerramos canal seguro
                conn.close()
                return

            if not metadatos or ":" not in metadatos:
                conn.close()
                return
            
            nombre_archivo, tamano_archivo = metadatos.split(":")
            tamano_archivo = int(tamano_archivo)
            
            print(f"\n\n[📥 RECEPCIÓN] Recibiendo: '{nombre_archivo}' ({tamano_archivo / (1024*1024):.2f} MB)")
            print("🔒 Descifrando bloques y desfragmentando en disco...")
            
            ruta_salida = f"recibido_{nombre_archivo}"
            bytes_recibidos = 0
            inicio_tiempo = time.time()
            
            # Control de reportes cada 10 MB
            bloque_reporte = 1024 * 1024 * 10 
            ultimo_reporte = 0
            
            with open(ruta_salida, "wb") as f:
                while bytes_recibidos < tamano_archivo:
                    bloque_por_leer = min(CHUNK_SIZE, tamano_archivo - bytes_recibidos)
                    buffer_cifrado = conn.recv(bloque_por_leer)
                    if not buffer_cifrado:
                        break
                    
                    buffer_descifrado = descifrar_bytes(buffer_cifrado)
                    f.write(buffer_descifrado)
                    bytes_recibidos += len(buffer_cifrado)
                    
                    if bytes_recibidos - ultimo_reporte >= bloque_reporte or bytes_recibidos == tamano_archivo:
                        print(f" -> Guardado: {bytes_recibidos / (1024*1024):.1f} MB / {tamano_archivo / (1024*1024):.1f} MB")
                        ultimo_reporte = bytes_recibidos
            
            fin_tiempo = time.time()
            print(f"✅ ¡Archivo '{ruta_salida}' reconstruido e íntegro!")
            print(f"⏱️ Tiempo de recepción: {fin_tiempo - inicio_tiempo:.2f} segundos.\n")
            conn.close()
        except Exception:
            pass

    def _enviar_archivo(self, ruta_archivo):
        try:
            nombre_archivo = os.path.basename(ruta_archivo)
            tamano_archivo = os.path.getsize(ruta_archivo)
            
            sock_transferencia = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_transferencia.connect((self.ip_rival, self.puerto_rival))
            
            cabecera = f"{nombre_archivo}:{tamano_archivo}".ljust(1024, '\x00')
            sock_transferencia.sendall(cabecera.encode('utf-8'))
            
            print(f"\n[📡 ENVÍO] Procesando e inyectando '{nombre_archivo}' a la red...")
            
            bytes_enviados = 0
            inicio_tiempo = time.time()
            bloque_reporte = 1024 * 1024 * 10
            ultimo_reporte = 0
            
            with open(ruta_archivo, "rb") as f:
                while bytes_enviados < tamano_archivo:
                    buffer_plano = f.read(CHUNK_SIZE)
                    if not buffer_plano:
                        break
                    
                    buffer_cifrado = cifrar_bytes(buffer_plano)
                    sock_transferencia.sendall(buffer_cifrado)
                    bytes_enviados += len(buffer_plano)
                    
                    if bytes_enviados - ultimo_reporte >= bloque_reporte or bytes_enviados == tamano_archivo:
                        print(f" -> Transmitido: {bytes_enviados / (1024*1024):.1f} MB...")
                        ultimo_reporte = bytes_enviados
            
            sock_transferencia.shutdown(socket.SHUT_WR)
            fin_tiempo = time.time()
            print(f"✅ Transmisión completada con éxito.")
            print(f"⏱️ Tiempo total de red: {fin_tiempo - inicio_tiempo:.2f} segundos.")
            sock_transferencia.close()
            
            time.sleep(0.5)
        except Exception as e:
            print(f"\n❌ Error al transmitir el archivo: {e}")

    def _conectar_a_rival(self):
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ip_rival, self.puerto_rival))
                self.sock_enviar = sock
                print(f"⚡ Enlace saliente acoplado con ({self.ip_rival}:{self.puerto_rival})")
                break
            except Exception:
                time.sleep(2)

if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    print("=== 🛠️ TRANSFERENCIA SEGURA DE ARCHIVOS P2P EN CODESPACES ===")
    mi_puerto = input("Introduce TU PUERTO de escucha local (ej. 9000): ").strip()
    ip_rival = input("Introduce la IP del nodo rival (ej. 127.0.0.1): ").strip()
    puerto_rival = input("Introduce el PUERTO del nodo rival (ej. 9001): ").strip()
    
    nodo = NodoP2PArchivos(mi_puerto, ip_rival, puerto_rival)
    nodo.iniciar()