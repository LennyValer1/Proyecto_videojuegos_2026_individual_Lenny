import pygame
import sys
import random

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)

# ─── Constantes ───────────────────────────────────────────────────────────────

TAMANO_BLOQUE = 56
COLUMNAS, FILAS = 15, 11
ANCHO         = COLUMNAS * TAMANO_BLOQUE   # 840
ALTO_HUD      = 56
ALTO          = FILAS * TAMANO_BLOQUE + ALTO_HUD  # 672

RADIO_EXPLOSION    = 2
TIEMPO_BOMBA_MS    = 3000
DURACION_EXP_MS    = 400
VIDAS_INICIALES    = 3
DURACION_INVINC_MS = 2000
MAX_BOMBAS         = 1          # límite de bombas simultáneas
PUNTOS_ENEMIGO     = 100
PUNTOS_NIVEL       = 500

pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Data Blaster")
reloj    = pygame.time.Clock()
fuente   = pygame.font.SysFont("consolas", 20, bold=True)
fuente_m = pygame.font.SysFont("consolas", 28, bold=True)
fuente_g = pygame.font.SysFont("consolas", 42, bold=True)
fuente_t = pygame.font.SysFont("consolas", 62, bold=True)

# ─── Paleta de colores ────────────────────────────────────────────────────────

NEGRO         = (0,   0,   0)
VERDE_BIT     = (57,  255, 20)
VERDE_OSCURO  = (0,   120, 0)
GRIS_MURO     = (70,  70,  70)
GRIS_BORDE    = (95,  95,  95)
MARRON_BLOQUE = (150, 75,  0)
ROJO_VIRUS    = (255, 50,  50)
AMARILLO_BOMBA= (255, 220, 0)
NARANJA_EXP   = (255, 140, 0)
AZUL_PUERTA   = (30,  144, 255)
BLANCO        = (255, 255, 255)
GRIS_OSCURO   = (20,  20,  20)
CYAN          = (0,   220, 220)
MORADO        = (180, 0,   255)

# ─── Configuracion de niveles ─────────────────────────────────────────────────

NIVELES = [
    {"nombre": "TUTORIAL",           "num_enemigos": 0, "velocidad_ms": 400, "densidad": 0.25},
    {"nombre": "INFECCION",          "num_enemigos": 2, "velocidad_ms": 400, "densidad": 0.35},
    {"nombre": "DEPURACION CRITICA", "num_enemigos": 3, "velocidad_ms": 230, "densidad": 0.45},
]


# ─── Generación de sonidos procedurales ──────────────────────────────────────

def generar_sonido(frecuencia, duracion_ms, volumen=0.4, forma="cuadrada", decay=True):
    """Genera un sonido sintético sin archivos externos."""
    sample_rate = 22050
    n_samples   = int(sample_rate * duracion_ms / 1000)
    buf         = []
    for i in range(n_samples):
        t = i / sample_rate
        if forma == "cuadrada":
            val = 1.0 if (i % int(sample_rate / frecuencia)) < int(sample_rate / frecuencia / 2) else -1.0
        elif forma == "ruido":
            val = random.uniform(-1, 1)
        else:
            val = 0.0
        if decay:
            val *= max(0, 1 - i / n_samples)
        val *= volumen
        val  = max(-1.0, min(1.0, val))
        sample = int(val * 32767)
        buf.append(sample)

    arr = pygame.sndarray.make_sound(
        pygame.sndarray.array(
            __import__("array").array("h", buf)
        )
    )
    return arr

# Precarga de sonidos
try:
    SND_BOMBA     = generar_sonido(180,  600, 0.5, "cuadrada")   # colocar bomba
    SND_EXPLOSION = generar_sonido(80,   500, 0.6, "ruido")      # explosión
    SND_MUERTE    = generar_sonido(120,  700, 0.5, "cuadrada")   # jugador muere
    SND_ENEMIGO   = generar_sonido(300,  200, 0.4, "cuadrada")   # enemigo eliminado
    SND_VICTORIA  = generar_sonido(440,  800, 0.5, "cuadrada", decay=False)  # ganar
    SND_PUERTA    = generar_sonido(520,  300, 0.4, "cuadrada")   # puerta revelada
    SONIDO_OK     = True
except Exception:
    SONIDO_OK     = False


def play(snd):
    if SONIDO_OK:
        try:
            snd.play()
        except Exception:
            pass


# ─── Clases de entidades ──────────────────────────────────────────────────────

class Bomba:
    def __init__(self, x, y):
        self.x          = x
        self.y          = y
        self.tiempo_det = pygame.time.get_ticks() + TIEMPO_BOMBA_MS


class Enemigo:
    def __init__(self, x, y, velocidad_ms):
        self.x          = x
        self.y          = y
        self.vel        = velocidad_ms
        self.direccion  = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
        self.ultimo_mov = 0


# ─── Generación del mapa ──────────────────────────────────────────────────────

def generar_mapa(config):
    mapa       = []
    candidatos = []
    for y in range(FILAS):
        fila = []
        for x in range(COLUMNAS):
            if x == 0 or x == COLUMNAS-1 or y == 0 or y == FILAS-1:
                fila.append(1)
            elif x % 2 == 0 and y % 2 == 0:
                fila.append(1)
            elif x < 3 and y < 3:
                fila.append(0)
            elif random.random() < config["densidad"]:
                fila.append(2)
                if x > 5 or y > 5:
                    candidatos.append((x, y))
            else:
                fila.append(0)
        mapa.append(fila)

    if not candidatos:
        candidatos = [(x,y) for y in range(FILAS) for x in range(COLUMNAS) if mapa[y][x] == 2]
    puerta_pos = random.choice(candidatos) if candidatos else (COLUMNAS-2, FILAS-2)
    return mapa, puerta_pos


# ─── Estado del juego ─────────────────────────────────────────────────────────

class Juego:
    def __init__(self):
        self.nivel_idx = 0
        self.vidas     = VIDAS_INICIALES
        self.puntos    = 0
        self._cargar_nivel()

    def _cargar_nivel(self):
        cfg = NIVELES[self.nivel_idx]
        self.mapa, self.puerta_pos = generar_mapa(cfg)
        self.jugador_x   = 1
        self.jugador_y   = 1
        self.bombas      = []
        self.enemigos    = self._colocar_enemigos(cfg["num_enemigos"], cfg["velocidad_ms"])
        self.explosiones = []
        self.puerta_vis  = False
        self.activo      = True
        self.estado      = "jugando"
        self.mensaje     = ""
        self.t_invinc    = pygame.time.get_ticks() + 1500

    def _colocar_enemigos(self, num, vel):
        esquinas = [(COLUMNAS-2, FILAS-2), (COLUMNAS-2, 1),
                    (1, FILAS-2),          (COLUMNAS-2, FILAS//2)]
        enemigos = []
        for ex, ey in esquinas[:num]:
            colocado = False
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = ex+dx, ey+dy
                    if 0 <= nx < COLUMNAS and 0 <= ny < FILAS and self.mapa[ny][nx] == 0:
                        enemigos.append(Enemigo(nx, ny, vel))
                        colocado = True
                        break
                if colocado:
                    break
        return enemigos

    def explotar(self, bomba):
        celdas       = {(bomba.x, bomba.y)}
        puerta_nueva = False

        for ddx, ddy in [(1,0),(-1,0),(0,1),(0,-1)]:
            for paso in range(1, RADIO_EXPLOSION + 1):
                nx = bomba.x + ddx * paso
                ny = bomba.y + ddy * paso
                if not (0 <= nx < COLUMNAS and 0 <= ny < FILAS):
                    break
                if self.mapa[ny][nx] == 1:
                    break
                celdas.add((nx, ny))
                if self.mapa[ny][nx] == 2:
                    if (nx, ny) == self.puerta_pos:
                        self.puerta_vis   = True
                        self.mapa[ny][nx] = 3
                        puerta_nueva      = True
                    else:
                        self.mapa[ny][nx] = 0
                    break

        play(SND_EXPLOSION)
        if puerta_nueva:
            play(SND_PUERTA)

        t_fin = pygame.time.get_ticks() + DURACION_EXP_MS
        for pos in celdas:
            self.explosiones.append((*pos, t_fin))

        # Reacción en cadena
        for otra in self.bombas[:]:
            if (otra.x, otra.y) in celdas:
                self.bombas.remove(otra)
                self.explotar(otra)

        # Eliminar enemigos
        eliminados = 0
        for e in self.enemigos[:]:
            if (e.x, e.y) in celdas:
                self.enemigos.remove(e)
                eliminados += 1
        if eliminados:
            self.puntos += eliminados * PUNTOS_ENEMIGO
            play(SND_ENEMIGO)

        # Verificar jugador
        if (self.jugador_x, self.jugador_y) in celdas:
            self._perder_vida("ERROR CRITICO - Archivo Corrupto")

    def _perder_vida(self, mensaje):
        play(SND_MUERTE)
        self.vidas -= 1
        if self.vidas <= 0:
            self.activo  = False
            self.estado  = "game_over"
            self.mensaje = mensaje
        else:
            self.jugador_x = 1
            self.jugador_y = 1
            self.bombas    = []
            self.t_invinc  = pygame.time.get_ticks() + DURACION_INVINC_MS

    def mover(self, dx, dy):
        if not self.activo or self.estado != "jugando":
            return
        nx, ny = self.jugador_x + dx, self.jugador_y + dy
        if not (0 <= nx < COLUMNAS and 0 <= ny < FILAS):
            return
        if self.mapa[ny][nx] in (1, 2):
            return
        if any(b.x == nx and b.y == ny for b in self.bombas):
            return
        self.jugador_x, self.jugador_y = nx, ny

    def poner_bomba(self):
        if not self.activo or self.estado != "jugando":
            return
        # Límite de bombas simultáneas
        if len(self.bombas) >= MAX_BOMBAS:
            return
        px, py = self.jugador_x, self.jugador_y
        if not any(b.x == px and b.y == py for b in self.bombas):
            self.bombas.append(Bomba(px, py))
            play(SND_BOMBA)

    def update(self, t):
        if not self.activo or self.estado != "jugando":
            return

        # Detonar bombas
        for b in self.bombas[:]:
            if b not in self.bombas:
                continue
            if t > b.tiempo_det:
                self.bombas.remove(b)
                self.explotar(b)

        # Limpiar explosiones vencidas
        self.explosiones = [e for e in self.explosiones if t < e[2]]

        # IA enemigos
        for e in self.enemigos:
            if t - e.ultimo_mov > e.vel:
                nx, ny = e.x + e.direccion[0], e.y + e.direccion[1]
                hay_bomba = any(b.x == nx and b.y == ny for b in self.bombas)
                if 0 <= nx < COLUMNAS and 0 <= ny < FILAS and self.mapa[ny][nx] in (0, 3) and not hay_bomba:
                    e.x, e.y = nx, ny
                else:
                    e.direccion = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
                e.ultimo_mov = t

        # Colisión jugador–enemigo
        if t > self.t_invinc:
            for e in self.enemigos:
                if self.jugador_x == e.x and self.jugador_y == e.y:
                    self._perder_vida("SISTEMA INFECTADO")
                    return

        # Victoria de nivel
        if len(self.enemigos) == 0 and self.puerta_vis:
            if self.jugador_x == self.puerta_pos[0] and self.jugador_y == self.puerta_pos[1]:
                self.puntos += PUNTOS_NIVEL
                play(SND_VICTORIA)
                self.activo = False
                if self.nivel_idx + 1 >= len(NIVELES):
                    self.estado = "victoria"
                else:
                    self.estado = "nivel_claro"

    def siguiente_nivel(self):
        self.nivel_idx += 1
        self._cargar_nivel()

    def reiniciar(self):
        self.__init__()


# ─── Dibujo ───────────────────────────────────────────────────────────────────

def dibujar_hud(juego):
    pygame.draw.rect(pantalla, GRIS_OSCURO, (0, 0, ANCHO, ALTO_HUD))
    pygame.draw.line(pantalla, VERDE_BIT, (0, ALTO_HUD-1), (ANCHO, ALTO_HUD-1), 2)

    cfg    = NIVELES[juego.nivel_idx]
    t_niv  = fuente.render(f"SECTOR {juego.nivel_idx+1}: {cfg['nombre']}", True, VERDE_BIT)
    pantalla.blit(t_niv, (10, 6))

    # Vidas con bloques visuales
    bloques_vidas = "■" * juego.vidas + "□" * (VIDAS_INICIALES - juego.vidas)
    t_vidas = fuente.render(f"VIDAS: {bloques_vidas}", True, ROJO_VIRUS)
    pantalla.blit(t_vidas, (10, 28))

    # Puntuación
    t_pts = fuente.render(f"PTS: {juego.puntos:06d}", True, AMARILLO_BOMBA)
    pantalla.blit(t_pts, (ANCHO//2 - t_pts.get_width()//2, 6))

    # Bombas disponibles
    bombas_disp  = MAX_BOMBAS - len(juego.bombas)
    icono_bombas = "●" * bombas_disp + "○" * (MAX_BOMBAS - bombas_disp)
    t_bomb = fuente.render(f"BOMBA: {icono_bombas}", True, AMARILLO_BOMBA)
    pantalla.blit(t_bomb, (ANCHO - t_bomb.get_width() - 10, 6))

    # Mensaje central de objetivo
    num_e = len(juego.enemigos)
    if num_e > 0:
        msg, col = f"VIRUS ACTIVOS: {num_e}  |  ELIMINALOS!", ROJO_VIRUS
    elif juego.puerta_vis:
        msg, col = ">>> ENCUENTRA LA SALIDA [EXIT] <<<", AZUL_PUERTA
    elif cfg["num_enemigos"] == 0:
        msg, col = "DESTRUYE BLOQUES PARA HALLAR LA SALIDA", CYAN
    else:
        msg, col = "DESTRUYE BLOQUES PARA HALLAR LA SALIDA", AZUL_PUERTA
    t_c = fuente.render(msg, True, col)
    pantalla.blit(t_c, t_c.get_rect(center=(ANCHO//2, 38)))


def dibujar_mapa(juego):
    for y, fila in enumerate(juego.mapa):
        for x, celda in enumerate(fila):
            rx = x * TAMANO_BLOQUE
            ry = y * TAMANO_BLOQUE + ALTO_HUD
            r  = pygame.Rect(rx, ry, TAMANO_BLOQUE, TAMANO_BLOQUE)
            if celda == 1:
                pygame.draw.rect(pantalla, GRIS_MURO, r)
                pygame.draw.rect(pantalla, GRIS_BORDE, r, 1)
                # Detalle de circuito en muros
                pygame.draw.rect(pantalla, (90,90,90), r.inflate(-8,-8), 1)
            elif celda == 2:
                pygame.draw.rect(pantalla, MARRON_BLOQUE, r, border_radius=4)
                # Textura de bloque de datos
                pygame.draw.rect(pantalla, (180,100,20), r.inflate(-6,-6), border_radius=3)
                t = fuente.render("DAT", True, (200,140,80))
                pantalla.blit(t, t.get_rect(center=r.center))
            elif celda == 3:
                pygame.draw.rect(pantalla, AZUL_PUERTA, r, border_radius=4)
                pygame.draw.rect(pantalla, CYAN, r.inflate(-4,-4), 2, border_radius=4)
                t = fuente.render("EXIT", True, BLANCO)
                pantalla.blit(t, t.get_rect(center=r.center))


def dibujar_juego(juego, t):
    dibujar_mapa(juego)

    # Explosiones
    for ex, ey, _ in juego.explosiones:
        r = pygame.Rect(ex*TAMANO_BLOQUE+2, ey*TAMANO_BLOQUE+2+ALTO_HUD,
                        TAMANO_BLOQUE-4, TAMANO_BLOQUE-4)
        pygame.draw.rect(pantalla, NARANJA_EXP, r, border_radius=3)
        pygame.draw.rect(pantalla, AMARILLO_BOMBA, r.inflate(-8,-8), border_radius=2)

    # Bombas con barra de tiempo
    for b in juego.bombas:
        cx = b.x * TAMANO_BLOQUE + TAMANO_BLOQUE // 2
        cy = b.y * TAMANO_BLOQUE + TAMANO_BLOQUE // 2 + ALTO_HUD
        # Parpadeo acelerado en los últimos 1000ms
        restante = max(0, b.tiempo_det - t)
        visible  = True
        if restante < 1000:
            visible = (t // 100) % 2 == 0
        if visible:
            pygame.draw.circle(pantalla, AMARILLO_BOMBA, (cx, cy), 13)
            pygame.draw.circle(pantalla, NEGRO, (cx, cy), 7)
            pygame.draw.circle(pantalla, ROJO_VIRUS, (cx-3, cy-3), 3)
        # Barra de tiempo bajo la bomba
        bw = int(TAMANO_BLOQUE * restante / TIEMPO_BOMBA_MS)
        by = b.y * TAMANO_BLOQUE + TAMANO_BLOQUE - 5 + ALTO_HUD
        pygame.draw.rect(pantalla, GRIS_OSCURO, (b.x*TAMANO_BLOQUE, by, TAMANO_BLOQUE, 4))
        color_barra = VERDE_BIT if restante > 1500 else (AMARILLO_BOMBA if restante > 800 else ROJO_VIRUS)
        pygame.draw.rect(pantalla, color_barra, (b.x*TAMANO_BLOQUE, by, bw, 4))

    # Enemigos
    for e in juego.enemigos:
        r = pygame.Rect(e.x*TAMANO_BLOQUE+4, e.y*TAMANO_BLOQUE+4+ALTO_HUD, 32, 32)
        pygame.draw.rect(pantalla, ROJO_VIRUS, r, border_radius=4)
        # "Ojos" del virus
        pygame.draw.circle(pantalla, BLANCO, (r.left+9,  r.top+10), 4)
        pygame.draw.circle(pantalla, BLANCO, (r.right-9, r.top+10), 4)
        pygame.draw.circle(pantalla, NEGRO,  (r.left+9,  r.top+10), 2)
        pygame.draw.circle(pantalla, NEGRO,  (r.right-9, r.top+10), 2)

    # Jugador
    inv     = t < juego.t_invinc
    mostrar = not inv or (t // 150) % 2 == 0
    if mostrar and (juego.activo or juego.estado in ("nivel_claro", "victoria")):
        r = pygame.Rect(juego.jugador_x*TAMANO_BLOQUE+4,
                        juego.jugador_y*TAMANO_BLOQUE+4+ALTO_HUD, 32, 32)
        pygame.draw.rect(pantalla, VERDE_BIT, r, border_radius=6)
        # Antena
        pygame.draw.line(pantalla, VERDE_BIT,
                         (r.centerx, r.top),
                         (r.centerx, r.top - 7), 2)
        pygame.draw.circle(pantalla, CYAN, (r.centerx, r.top - 8), 3)


def dibujar_overlay(linea1, linea2, color1=VERDE_BIT, linea3=""):
    overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    pantalla.blit(overlay, (0, 0))
    t1 = fuente_g.render(linea1, True, color1)
    t2 = fuente_m.render(linea2, True, BLANCO)
    pantalla.blit(t1, t1.get_rect(center=(ANCHO//2, ALTO//2 - 35)))
    pantalla.blit(t2, t2.get_rect(center=(ANCHO//2, ALTO//2 + 15)))
    if linea3:
        t3 = fuente.render(linea3, True, CYAN)
        pantalla.blit(t3, t3.get_rect(center=(ANCHO//2, ALTO//2 + 50)))


# ─── Pantalla de inicio ───────────────────────────────────────────────────────

def dibujar_menu(t):
    pantalla.fill(NEGRO)

    # Cuadrícula de fondo animada
    offset = (t // 40) % TAMANO_BLOQUE
    for x in range(-TAMANO_BLOQUE, ANCHO + TAMANO_BLOQUE, TAMANO_BLOQUE):
        pygame.draw.line(pantalla, (0, 35, 0), (x + offset, 0), (x + offset, ALTO), 1)
    for y in range(-TAMANO_BLOQUE, ALTO + TAMANO_BLOQUE, TAMANO_BLOQUE):
        pygame.draw.line(pantalla, (0, 35, 0), (0, y + offset), (ANCHO, y + offset), 1)

    # Título principal con sombra
    titulo = fuente_t.render("DATA BLASTER", True, NEGRO)
    pantalla.blit(titulo, titulo.get_rect(center=(ANCHO//2 + 3, 103)))
    titulo = fuente_t.render("DATA BLASTER", True, VERDE_BIT)
    pantalla.blit(titulo, titulo.get_rect(center=(ANCHO//2, 100)))

    # Subtítulo
    sub = fuente_m.render("- Purga el sistema. Elimina el malware. -", True, CYAN)
    pantalla.blit(sub, sub.get_rect(center=(ANCHO//2, 155)))

    # Línea divisoria
    pygame.draw.line(pantalla, VERDE_OSCURO, (60, 175), (ANCHO-60, 175), 1)

    # Instrucciones de controles
    controles = [
        ("CONTROLES", VERDE_BIT),
        ("↑ ↓ ← →   Mover a Bit-E", BLANCO),
        ("ESPACIO    Colocar bomba de código", BLANCO),
        ("ENTER      Continuar al siguiente sector", BLANCO),
        ("R          Reiniciar partida", BLANCO),
    ]
    y_base = 200
    for texto, color in controles:
        t_ctrl = fuente.render(texto, True, color)
        pantalla.blit(t_ctrl, t_ctrl.get_rect(center=(ANCHO//2, y_base)))
        y_base += 28

    # Línea divisoria
    pygame.draw.line(pantalla, VERDE_OSCURO, (60, y_base + 5), (ANCHO-60, y_base + 5), 1)

    # Objetivo del juego
    y_base += 20
    obj = [
        ("OBJETIVO", AMARILLO_BOMBA),
        ("Elimina todos los virus del sector,", BLANCO),
        ("destruye bloques para revelar la salida [EXIT]", BLANCO),
        ("y avanza al siguiente sector.", BLANCO),
    ]
    for texto, color in obj:
        t_o = fuente.render(texto, True, color)
        pantalla.blit(t_o, t_o.get_rect(center=(ANCHO//2, y_base)))
        y_base += 26

    # Parpadeo "Presiona ENTER"
    if (t // 500) % 2 == 0:
        t_enter = fuente_m.render(">>> PRESIONA ENTER PARA INICIAR <<<", True, VERDE_BIT)
        pantalla.blit(t_enter, t_enter.get_rect(center=(ANCHO//2, ALTO - 45)))

    # Crédito
    t_cr = fuente.render("Lenny Valer  |  Videojuegos y Aplicaciones Moviles  |  2026", True, (60, 60, 60))
    pantalla.blit(t_cr, t_cr.get_rect(center=(ANCHO//2, ALTO - 15)))

    pygame.display.flip()


# ─── Bucle principal ──────────────────────────────────────────────────────────

estado_app = "menu"   # "menu" | "jugando"
juego      = None

while True:
    t = pygame.time.get_ticks()

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.KEYDOWN:

            # ── Menú de inicio — solo ENTER arranca, nada más ──
            if estado_app == "menu":
                if evento.key == pygame.K_RETURN:
                    juego      = Juego()
                    estado_app = "jugando"
                # cualquier otra tecla en el menú se ignora completamente

            # ── En partida ──
            elif estado_app == "jugando":
                if   evento.key == pygame.K_UP:    juego.mover(0, -1)
                elif evento.key == pygame.K_DOWN:  juego.mover(0,  1)
                elif evento.key == pygame.K_LEFT:  juego.mover(-1, 0)
                elif evento.key == pygame.K_RIGHT: juego.mover( 1, 0)
                elif evento.key == pygame.K_SPACE:
                    # solo poner bomba si el juego está activo, nunca cerrar
                    if juego.estado == "jugando":
                        juego.poner_bomba()
                elif evento.key == pygame.K_RETURN and juego.estado == "nivel_claro":
                    juego.siguiente_nivel()
                elif evento.key == pygame.K_r and juego.estado in ("game_over", "victoria"):
                    estado_app = "menu"

    # ── Render ──
    if estado_app == "menu":
        dibujar_menu(t)
        continue

    # Partida activa
    juego.update(t)
    pantalla.fill(NEGRO)
    dibujar_hud(juego)
    dibujar_juego(juego, t)

    if juego.estado == "nivel_claro":
        dibujar_overlay(
            "SECTOR LIMPIO",
            f"Puntuacion: {juego.puntos:06d}",
            VERDE_BIT,
            "Presiona ENTER para continuar"
        )
    elif juego.estado == "game_over":
        dibujar_overlay(
            juego.mensaje,
            f"Puntuacion final: {juego.puntos:06d}",
            ROJO_VIRUS,
            "Presiona R para volver al menu"
        )
    elif juego.estado == "victoria":
        dibujar_overlay(
            "SISTEMA RESTAURADO",
            f"Puntuacion final: {juego.puntos:06d}",
            CYAN,
            "Presiona R para volver al menu"
        )

    pygame.display.flip()
    reloj.tick(60)