import socket
import threading
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Header, Footer, Button, Static

class GatoClientApp(App):
    CSS = """
    Screen {
        align: center middle;
        background: $surface;
    }
    #game-container {
        width: 50;
        height: 30;
        border: heavy $primary;
        padding: 1;
    }
    Grid {
        grid-size: 3 3;
        grid-gutter: 1;
        margin: 1 0;
        height: 11;
    }
    Button {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-style: bold;
    }
    .status-box {
        background: $panel;
        color: $text;
        padding: 1;
        border: solid $accent;  /* 👈 Cambiado de 'sunken' a 'solid' */
        margin-top: 1;
        height: 6;
    }
    """
    
    TITLE = "🎮 Super Gato P2P/Client-Server"
    BINDINGS = [("q", "quit", "Salir")]

    def __init__(self, server_ip="127.0.0.1", server_port=7000):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        # Mapeo de botones visuales a las coordenadas reales exigidas por el profesor
        self.coords_map = [
            (4,1), (4,2), (4,3),
            (5,1), (5,2), (5,3),
            (6,1), (6,2), (6,3)
        ]
        self.mis_simbolo = ""
        self.mi_turno = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="game-container"):
            yield Static("Tablero Coordenadas (Filas 4-6, Columnas 1-3)", classes="title")
            with Grid():
                # Generamos los 9 botones del tablero
                for i in range(9):
                    f, c = self.coords_map[i]
                    yield Button(f"({f},{c})", id=f"btn_{i}")
            yield Static("Conectando al servidor...", id="status_log", classes="status-box")
        yield Footer()

    def on_mount(self) -> None:
        """Inicializa la conexión de red en un hilo separado al montar la UI."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.server_ip, self.server_port))
            threading.Thread(target=self.escuchar_servidor, daemon=True).start()
        except Exception as e:
            self.query_one("#status_log").update(f"❌ Error de conexión: {e}")

    def escuchar_servidor(self):
        # El socket lee continuamente líneas del servidor (Petición/Respuesta asíncrona)
        buffer = ""
        while True:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    self.call_from_thread(self.procesar_comando, linea)
            except Exception:
                break

    def procesar_comando(self, linea):
        if not linea: return
        partes = linea.split("|")
        comando = partes[0]

        if comando == "INFO":
            self.query_one("#status_log").update(f"ℹ️ {partes[1]}")
            if "Tu símbolo es" in partes[1]:
                self.mis_simbolo = partes[1].split()[-1]
                self.title = f"🎮 Gato Server - Jugador {self.mis_simbolo}"
                
        elif comando == "ERROR":
            self.query_one("#status_log").update(f"⚠️ ERROR: {partes[1]}")
            
        elif comando == "TURNO":
            turno_de = partes[1]
            if turno_de == self.mis_simbolo:
                self.mi_turno = True
                self.query_one("#status_log").update("🟢 ¡Es TU turno! Elige una coordenada.")
            else:
                self.mi_turno = False
                self.query_one("#status_log").update(f"⏳ Esperando turno del rival ({turno_de})...")
                
        elif comando == "TABLERO":
            # Actualiza el texto de los botones con el estado real de la matriz
            celdas = partes[1:]
            for i in range(9):
                btn = self.query_one(f"#btn_{i}", Button)
                if celdas[i] != " ":
                    btn.label = celdas[i]
                    btn.disabled = True  # Bloquea visualmente la celda ya ocupada
                    
        elif comando == "FIN":
            self.query_one("#status_log").update(f"🏆 {partes[1]}")
            self.mi_turno = False
            # Bloquear todo el tablero al terminar el juego
            for i in range(9):
                self.query_one(f"#btn_{i}", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Se ejecuta al dar clic sobre cualquier coordenada del tablero."""
        btn_id = event.button.id
        if not btn_id.startswith("btn_"):
            return
            
        if not self.mi_turno:
            self.query_one("#status_log").update("⚠️ ¡No es tu turno! Sé paciente.")
            return

        idx = int(btn_id.split("_")[1])
        f, c = self.coords_map[idx]
        
        # Envía la coordenada seleccionada al servidor central para validación de reglas
        try:
            self.sock.sendall(f"JUGADA:{f},{c}\n".encode('utf-8'))
        except Exception:
            self.query_one("#status_log").update("❌ Error al enviar jugada al servidor.")

    def on_unmount(self) -> None:
        if self.sock:
            self.sock.close()

if __name__ == "__main__":
    GatoClientApp().run()