import socket
import threading

class GatoServer:
    def __init__(self, ip="127.0.0.1", port=7000):
        self.ip = ip
        self.port = port
        # Matriz indexada por las coordenadas de la tarea: Filas (4,5,6), Columnas (1,2,3)
        self.tablero = {f: {c: " " for c in [1, 2, 3]} for f in [4, 5, 6]}
        self.jugadores = []  # Guardará las conexiones de los 2 jugadores
        self.simbolos = {}   # conn -> 'X' o 'O'
        self.turno_actual = 0 # Índice del jugador que tiene el turno
        self.juego_activo = True
        self.lock = threading.Lock()

    def verificar_ganador(self):
        t = self.tablero
        # Combinaciones ganadoras usando las coordenadas del problema
        lineas = [
            # Filas
            [(4,1), (4,2), (4,3)], [(5,1), (5,2), (5,3)], [(6,1), (6,2), (6,3)],
            # Columnas
            [(4,1), (5,1), (6,1)], [(4,2), (5,2), (6,2)], [(4,3), (5,3), (6,3)],
            # Diagonales
            [(4,1), (5,2), (6,3)], [(4,3), (5,2), (6,1)]
        ]
        for linea in lineas:
            valores = [t[f][c] for f, c in linea]
            if valores[0] != " " and valores[0] == valores[1] == valores[2]:
                return valores[0] # Retorna 'X' o 'O'
        
        # Verificar empate
        if all(t[f][c] != " " for f in [4,5,6] for c in [1,2,3]):
            return "EMPATE"
        return None

    def transmitir_a_todos(self, mensaje):
        """Envía un estado o instrucción a ambos clientes."""
        for conn in self.jugadores:
            try:
                conn.sendall((mensaje + "\n").encode('utf-8'))
            except Exception:
                pass

    def generar_estado_tablero(self):
        """Serializa el tablero para enviárselo a los clientes."""
        # Ejemplo de cadena: "TABLERO|X| |O| |X| | | |O"
        celdas = []
        for f in [4, 5, 6]:
            for c in [1, 2, 3]:
                celdas.append(self.tablero[f][c])
        return "TABLERO|" + "|".join(celdas)

    def manejar_jugador(self, conn, id_jugador):
        simbolo = self.simbolos[conn]
        conn.sendall(f"INFO|Tu símbolo es {simbolo}\n".encode('utf-8'))
        
        if len(self.jugadores) < 2:
            conn.sendall("INFO|Esperando al segundo jugador...\n".encode('utf-8'))
        else:
            self.transmitir_a_todos("INFO|¡Juego iniciado! Comienza el Jugador X.")
            self.transmitir_a_todos(self.generar_estado_tablero())
            self.transmitir_a_todos(f"TURNO|{self.simbolos[self.jugadores[self.turno_actual]]}")

        while self.juego_activo:
            try:
                data = conn.recv(1024).decode('utf-8').strip()
                if not data:
                    break
                
                if data.startswith("JUGADA:"):
                    with self.lock:
                        # Verificar si es el turno de este jugador
                        if self.jugadores[self.turno_actual] != conn:
                            conn.sendall("ERROR|No es tu turno.\n".encode('utf-8'))
                            continue
                        
                        # Parsear coordenadas "JUGADA:fila,columna"
                        try:
                            _, coords = data.split(":")
                            f_str, c_str = coords.split(",")
                            f, c = int(f_str), int(c_str)
                        except ValueError:
                            conn.sendall("ERROR|Formato inválido.\n".encode('utf-8'))
                            continue

                        # Validación de existencia de rango (Fila 4-6, Columna 1-3)
                        if f not in [4, 5, 6] or c not in [1, 2, 3]:
                            conn.sendall("ERROR|Coordenada fuera de rango (Fila: 4-6, Col: 1-3).\n".encode('utf-8'))
                            continue
                        
                        # Validación de celda ocupada
                        if self.tablero[f][c] != " ":
                            conn.sendall("ERROR|Esa posición ya está ocupada.\n".encode('utf-8'))
                            continue

                        # Registrar jugada válida
                        self.tablero[f][c] = simbolo
                        
                        # Comprobar estado del juego
                        ganador = self.verificar_ganador()
                        self.transmitir_a_todos(self.generar_estado_tablero())
                        
                        if ganador:
                            self.juego_activo = False
                            if ganador == "EMPATE":
                                self.transmitir_a_todos("FIN|¡El juego ha terminado en un EMPATE!")
                            else:
                                self.transmitir_a_todos(f"FIN|¡El jugador {ganador} ha ganado el juego!")
                            break
                        
                        # Cambiar de turno
                        self.turno_actual = 1 - self.turno_actual
                        self.transmitir_a_todos(f"TURNO|{self.simbolos[self.jugadores[self.turno_actual]]}")

            except Exception:
                break

        print(f"🔌 Jugador {simbolo} desconectado.")
        with self.lock:
            if conn in self.jugadores:
                self.jugadores.remove(conn)
        conn.close()

    def iniciar(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.ip, self.port))
        server.listen(2)
        print(f"🏛️ Servidor del Gato esperando conexiones en el puerto {self.port}...")

        try:
            while len(self.jugadores) < 2:
                conn, addr = server.accept()
                self.jugadores.append(conn)
                id_j = len(self.jugadores)
                self.simbolos[conn] = "X" if id_j == 1 else "O"
                print(f"👥 Jugador {id_j} conectado desde {addr[0]}:{addr[1]} ({self.simbolos[conn]})")
                threading.Thread(target=self.manejar_jugador, args=(conn, id_j), daemon=True).start()
            
            # Mantener el hilo principal vivo
            while self.juego_activo:
                threading.Event().wait(1)
        finally:
            server.close()

if __name__ == "__main__":
    GatoServer().iniciar()