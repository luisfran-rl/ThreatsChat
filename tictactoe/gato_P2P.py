import os
import sys
import socket
import threading
import time
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Header, Footer, Button, Static

# ==========================================
# PUNTO 3: DICCIONARIO DE FUNCIONES INTERNAS
# ==========================================
DICCIONARIO_FUNCIONES = {
    "J": "PROCESAR_JUGADA",   # Formato: J:fila,columna
    "I": "INICIAR_JUEGO"     # Formato: I:puerto_escucha_j2
}

class GatoP2PApp(App):
    CSS = """
    Screen { align: center middle; background: $surface; }
    #game-container { width: 50; height: 30; border: heavy $primary; padding: 1; }
    Grid { grid-size: 3 3; grid-gutter: 1; margin: 1 0; height: 11; }
    Button { width: 100%; height: 100%; content-align: center middle; text-style: bold; }
    .status-box { background: $panel; color: $text; padding: 1; border: solid $accent; margin-top: 1; height: 6; }
    """
    
    TITLE = "🎮 Gato P2P Descentralizado Puro"
    BINDINGS = [("q", "quit", "Salir")]

    def __init__(self, modo, mi_puerto, ip_rival=None, puerto_rival=None):
        super().__init__()
        self.modo = modo # "1" (J1) o "2" (J2)
        self.mi_puerto = int(mi_puerto)
        self.ip_rival = ip_rival if ip_rival else "127.0.0.1"
        self.puerto_rival = int(puerto_rival) if puerto_rival else None
        
        # Sockets de comunicación P2P
        self.sock_enviar = None
        self.conexion_establecida = False
        
        # Matriz requerida: Filas 4-6, Columnas 1-3
        self.tablero = {f: {c: " " for c in [1, 2, 3]} for f in [4, 5, 6]}
        self.coords_map = [(4,1), (4,2), (4,3), (5,1), (5,2), (5,3), (6,1), (6,2), (6,3)]
        
        # Regla de la nota: El primero (Modo 1) es el J1 ('X') y abre turno
        if self.modo == "1":
            self.mi_simbolo = "X"
            self.simbolo_rival = "O"
            self.mi_turno = True
        else:
            self.mi_simbolo = "O"
            self.simbolo_rival = "X"
            self.mi_turno = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="game-container"):
            yield Static(f"Tablero P2P - Eres Jugador [{self.mi_simbolo}]", classes="title")
            with Grid():
                for i in range(9):
                    f, c = self.coords_map[i]
                    yield Button(f"({f},{c})", id=f"btn_{i}")
            yield Static("Iniciando comunicación P2P...", id="status_log", classes="status-box")
        yield Footer()

    def on_mount(self) -> None:
        """PUNTO 1 y 5: Inicia el servidor de escucha local en segundo plano."""
        threading.Thread(target=self._servidor_escucha, daemon=True).start()
        
        # Si somos J2, disparamos la conexión activa hacia J1 de inmediato
        if self.modo == "2":
            threading.Thread(target=self._conectar_a_j1, daemon=True).start()
        else:
            self.query_one("#status_log").update("⏳ Esperando que el Jugador 2 se conecte por red...")

    def _servidor_escucha(self):
        """Hilo constante que oye las peticiones entrantes."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("0.0.0.0", self.mi_puerto))
        server_socket.listen(1)
        
        conn, addr = server_socket.accept()
        
        # Hilo de lectura para procesar los mensajes entrantes de este cliente
        threading.Thread(target=self._recibir_datos, args=(conn,), daemon=True).start()

    def _recibir_datos(self, conn):
        buffer = ""
        while True:
            try:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    self.call_from_thread(self.interpretar_paquete, linea)
            except Exception:
                break

    def _conectar_a_j1(self):
        """Lógica del J2 para enlazarse a J1 e informarle su propio puerto de escucha."""
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ip_rival, self.puerto_rival))
                self.sock_enviar = sock
                
                # Le enviamos a J1 nuestro puerto para que él se conecte con nosotros de vuelta
                self.sock_enviar.sendall(f"I:{self.mi_puerto}\n".encode('utf-8'))
                
                self.conexion_establecida = True
                self.call_from_thread(self.query_one("#status_log").update, "🟢 Enlazado con J1. Esperando que haga su movimiento...")
                break
            except Exception:
                time.sleep(0.5)

    def interpretar_paquete(self, linea):
        """Usa el diccionario del Punto 3 para procesar eventos de red."""
        if not ":" in linea: return
        prefijo, valor = linea.split(":", 1)
        accion = DICCIONARIO_FUNCIONES.get(prefijo)
        
        if accion == "INICIAR_JUEGO" and self.modo == "1":
            # El Jugador 1 recibe el puerto del Jugador 2 y abre su canal de envío hacia él
            puerto_j2 = int(valor)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ip_rival, puerto_j2))
                self.sock_enviar = sock
                self.conexion_establecida = True
                self.query_one("#status_log").update("🟢 ¡Contrincante sincronizado! Es TU turno (Haz tu jugada).")
            except Exception as e:
                self.query_one("#status_log").update(f"❌ Error al acoplar canal: {e}")
                
        elif accion == "PROCESAR_JUGADA":
            f, c = map(int, valor.split(","))
            self.marcar_tablero_local(f, c, self.simbolo_rival)
            
            # Evaluar si perdimos o empatamos tras el tiro del rival
            resultado = self.definir_logica_juego()
            if resultado:
                self.finalizar_pantalla(resultado)
            else:
                self.mi_turno = True
                self.query_one("#status_log").update("🟢 Tu rival ya jugó. ¡Es TU turno!")

    def marcar_tablero_local(self, f, c, simbolo):
        """Actualiza la matriz interna y deshabilita el botón visual."""
        self.tablero[f][c] = simbolo
        idx = self.coords_map.index((f, c))
        btn = self.query_one(f"#btn_{idx}", Button)
        btn.label = simbolo
        btn.disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Se ejecuta al presionar una casilla de coordenadas."""
        if not self.conexion_establecida or not self.sock_enviar:
            self.query_one("#status_log").update("⚠️ Esperando el enlace y saludo P2P del contrincante...")
            return
        if not self.mi_turno:
            self.query_one("#status_log").update("⏳ No es tu turno. Espera al contrincante.")
            return

        idx = int(event.button.id.split("_")[1])
        f, c = self.coords_map[idx]

        self.marcar_tablero_local(f, c, self.mi_simbolo)
        self.mi_turno = False
        self.query_one("#status_log").update("⏳ Enviando jugada... Esperando al rival.")

        # Transmitir paquete simplificado
        try:
            self.sock_enviar.sendall(f"J:{f},{c}\n".encode('utf-8'))
        except Exception:
            self.query_one("#status_log").update("❌ Error de red al enviar jugada.")
            return

        # Evaluar lógica del juego localmente (Si ganamos o empatamos)
        resultado = self.definir_logica_juego()
        if resultado:
            self.finalizar_pantalla(resultado)

    def definir_logica_juego(self):
        """PUNTO 4: Determina si el juego se ganó, se perdió o continúa."""
        t = self.tablero
        lineas = [
            [(4,1), (4,2), (4,3)], [(5,1), (5,2), (5,3)], [(6,1), (6,2), (6,3)], # Filas
            [(4,1), (5,1), (6,1)], [(4,2), (5,2), (6,2)], [(4,3), (5,3), (6,3)], # Columnas
            [(4,1), (5,2), (6,3)], [(4,3), (5,2), (6,1)]                         # Diagonales
        ]
        for linea in lineas:
            valores = [t[f][c] for f, c in linea]
            if valores[0] != " " and valores[0] == valores[1] == valores[2]:
                if valores[0] == self.mi_simbolo:
                    return "¡GANASTE EL JUEGO! 🎉"
                else:
                    return "¡PERDISTE EL JUEGO! ❌"
                    
        if all(t[f][c] != " " for f in [4,5,6] for c in [1,2,3]):
            return "¡EMPATE! No quedan casillas libres."
        return None

    def finalizar_pantalla(self, mensaje):
        self.query_one("#status_log").update(f"🏆 {mensaje}")
        self.mi_turno = False
        for i in range(9):
            self.query_one(f"#btn_{i}", Button).disabled = True

if __name__ == "__main__":
    os.system('clear')
    print("=== 🎮 CONFIGURACIÓN DEL GATO P2P DESCENTRALIZADO ===")
    print("1) Ser Jugador 1 (Esperar conexión / Símbolo X)")
    print("2) Ser Jugador 2 (Conectarse a J1 / Símbolo O)")
    modo_opcion = input("Selecciona una opción (1 o 2): ").strip()

    if modo_opcion == "1":
        puerto = input("Introduce TU PUERTO de escucha local (ej. 7000): ")
        app = GatoP2PApp(modo="1", mi_puerto=puerto)
        app.run()
    elif modo_opcion == "2":
        puerto_local = input("Introduce TU PUERTO de escucha local (ej. 7001): ")
        ip_r = input("Introduce la IP del Jugador 1 (ej. 127.0.0.1): ")
        puerto_r = input("Introduce el PUERTO del Jugador 1 (ej. 7000): ")
        app = GatoP2PApp(modo="2", mi_puerto=puerto_local, ip_rival=ip_r, puerto_rival=puerto_r)
        app.run()
    else:
        print("Opción inválida.")