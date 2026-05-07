import pygame
import sys
import random

pygame.init()

TAMANO_BLOQUE = 40
COLUMNAS, FILAS = 15, 11
ANCHO         = COLUMNAS * TAMANO_BLOQUE   # 600
ALTO_HUD      = 40
ALTO          = FILAS * TAMANO_BLOQUE + ALTO_HUD  # 480

RADIO_EXPLOSION    = 2
TIEMPO_BOMBA_MS    = 3000
DURACION_EXP_MS    = 400
VIDAS_INICIALES    = 3
DURACION_INVINC_MS = 2000

pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Data Blaster")
reloj    = pygame.time.Clock()
fuente   = pygame.font.SysFont("consolas", 18, bold=True)
fuente_g = pygame.font.SysFont("consolas", 32, bold=True)

# --- Paleta de colores ---
NEGRO         = (0,   0,   0)
VERDE_BIT     = (57,  255, 20)
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

# --- Configuracion de niveles ---
NIVELES = [
    {"nombre": "TUTORIAL",           "num_enemigos": 0, "velocidad_ms": 400, "densidad": 0.25},
    {"nombre": "INFECCION",          "num_enemigos": 2, "velocidad_ms": 400, "densidad": 0.35},
    {"nombre": "DEPURACION CRITICA", "num_enemigos": 3, "velocidad_ms": 230, "densidad": 0.45},
]


# ─── Clases de entidades ──────────────────────────────────────────────────────

class Bomba:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tiempo_det = pygame.time.get_ticks() + TIEMPO_BOMBA_MS


class Enemigo:
    def __init__(self, x, y, velocidad_ms):
        self.x           = x
        self.y           = y
        self.vel         = velocidad_ms
        self.direccion   = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
        self.ultimo_mov  = 0


# ─── Generación del mapa ──────────────────────────────────────────────────────

def generar_mapa(config):
    """Devuelve (mapa, puerta_pos). La puerta_pos esta oculta bajo un bloque destruible."""
    mapa = []
    candidatos = []
    for y in range(FILAS):
        fila = []
        for x in range(COLUMNAS):
            if x == 0 or x == COLUMNAS-1 or y == 0 or y == FILAS-1:
                fila.append(1)                       # muro borde
            elif x % 2 == 0 and y % 2 == 0:
                fila.append(1)                       # muro interior
            elif x < 3 and y < 3:
                fila.append(0)                       # zona segura spawn
            elif random.random() < config["densidad"]:
                fila.append(2)                       # bloque destruible
                if x > 5 or y > 5:                  # lejos del spawn
                    candidatos.append((x, y))
            else:
                fila.append(0)
        mapa.append(fila)

    if not candidatos:
        candidatos = [(x,y) for y in range(FILAS) for x in range(COLUMNAS)
                      if mapa[y][x] == 2]
    puerta_pos = random.choice(candidatos) if candidatos else (COLUMNAS-2, FILAS-2)
    return mapa, puerta_pos


# ─── Estado del juego ─────────────────────────────────────────────────────────

class Juego:
    def __init__(self):
        self.nivel_idx = 0
        self.vidas     = VIDAS_INICIALES
        self._cargar_nivel()

    # ── Inicialización de nivel ──
    def _cargar_nivel(self):
        cfg = NIVELES[self.nivel_idx]
        self.mapa, self.puerta_pos = generar_mapa(cfg)
        self.jugador_x   = 1
        self.jugador_y   = 1
        self.bombas      = []
        self.enemigos    = self._colocar_enemigos(cfg["num_enemigos"], cfg["velocidad_ms"])
        self.explosiones = []           # lista de (x, y, tiempo_fin)
        self.puerta_vis  = False        # si el bloque de la puerta fue destruido
        self.activo      = True
        self.estado      = "jugando"   # jugando | nivel_claro | game_over | victoria
        self.mensaje     = ""
        self.t_invinc    = pygame.time.get_ticks() + 1500  # invencibilidad inicial

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

    # ── Lógica de explosión ──
    def explotar(self, bomba):
        """Calcula las celdas afectadas respetando muros; maneja destruccion, muertes y cadena."""
        celdas = {(bomba.x, bomba.y)}

        for ddx, ddy in [(1,0),(-1,0),(0,1),(0,-1)]:
            for paso in range(1, RADIO_EXPLOSION + 1):
                nx = bomba.x + ddx * paso
                ny = bomba.y + ddy * paso
                if not (0 <= nx < COLUMNAS and 0 <= ny < FILAS):
                    break
                if self.mapa[ny][nx] == 1:          # muro indestructible → corta
                    break
                celdas.add((nx, ny))
                if self.mapa[ny][nx] == 2:          # bloque destruible → destruye y corta
                    if (nx, ny) == self.puerta_pos:
                        self.puerta_vis   = True
                        self.mapa[ny][nx] = 3       # revela la puerta
                    else:
                        self.mapa[ny][nx] = 0
                    break

        # Efecto visual de explosión
        t_fin = pygame.time.get_ticks() + DURACION_EXP_MS
        for pos in celdas:
            self.explosiones.append((*pos, t_fin))

        # Reacción en cadena: bombas dentro del área explotan de inmediato
        for otra in self.bombas[:]:
            if (otra.x, otra.y) in celdas:
                self.bombas.remove(otra)
                self.explotar(otra)

        # Matar enemigos en la explosión
        for e in self.enemigos[:]:
            if (e.x, e.y) in celdas:
                self.enemigos.remove(e)

        # Verificar si el jugador es alcanzado
        if (self.jugador_x, self.jugador_y) in celdas:
            self._perder_vida("ERROR CRITICO - Archivo Corrupto")

    # ── Vidas y respawn ──
    def _perder_vida(self, mensaje):
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

    # ── Acciones del jugador ──
    def mover(self, dx, dy):
        if not self.activo or self.estado != "jugando":
            return
        nx, ny = self.jugador_x + dx, self.jugador_y + dy
        if not (0 <= nx < COLUMNAS and 0 <= ny < FILAS):
            return
        if self.mapa[ny][nx] in (1, 2):
            return
        if any(b.x == nx and b.y == ny for b in self.bombas):
            return  # no atravesar bombas propias
        self.jugador_x, self.jugador_y = nx, ny

    def poner_bomba(self):
        if not self.activo or self.estado != "jugando":
            return
        px, py = self.jugador_x, self.jugador_y
        if not any(b.x == px and b.y == py for b in self.bombas):
            self.bombas.append(Bomba(px, py))

    # ── Update frame ──
    def update(self, t):
        if not self.activo or self.estado != "jugando":
            return

        # Detonar bombas que llegaron a su tiempo
        for b in self.bombas[:]:
            if b not in self.bombas:    # ya fue detonada por cadena
                continue
            if t > b.tiempo_det:
                self.bombas.remove(b)
                self.explotar(b)

        # Limpiar efectos de explosión vencidos
        self.explosiones = [e for e in self.explosiones if t < e[2]]

        # IA enemigos
        for e in self.enemigos:
            if t - e.ultimo_mov > e.vel:
                nx, ny = e.x + e.direccion[0], e.y + e.direccion[1]
                if 0 <= nx < COLUMNAS and 0 <= ny < FILAS and self.mapa[ny][nx] in (0, 3):
                    e.x, e.y = nx, ny
                else:
                    e.direccion = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
                e.ultimo_mov = t

        # Colision jugador–enemigo (sin invencibilidad)
        if t > self.t_invinc:
            for e in self.enemigos:
                if self.jugador_x == e.x and self.jugador_y == e.y:
                    self._perder_vida("SISTEMA INFECTADO")
                    return

        # Condicion de victoria del nivel: sin enemigos + jugador pisa la puerta
        if len(self.enemigos) == 0 and self.puerta_vis:
            if self.jugador_x == self.puerta_pos[0] and self.jugador_y == self.puerta_pos[1]:
                self.activo = False
                if self.nivel_idx + 1 >= len(NIVELES):
                    self.estado = "victoria"
                else:
                    self.estado = "nivel_claro"

    # ── Transiciones ──
    def siguiente_nivel(self):
        self.nivel_idx += 1
        self._cargar_nivel()

    def reiniciar(self):
        self.__init__()


# ─── Funciones de dibujo ──────────────────────────────────────────────────────

def dibujar_hud(juego):
    pygame.draw.rect(pantalla, GRIS_OSCURO, (0, 0, ANCHO, ALTO_HUD))
    pygame.draw.line(pantalla, VERDE_BIT, (0, ALTO_HUD-1), (ANCHO, ALTO_HUD-1), 1)

    cfg = NIVELES[juego.nivel_idx]
    t_nivel = fuente.render(f"SECTOR {juego.nivel_idx+1}: {cfg['nombre']}", True, VERDE_BIT)

    bloques_vidas = "■" * juego.vidas + "□" * (VIDAS_INICIALES - juego.vidas)
    t_vidas = fuente.render(f"VIDAS: {bloques_vidas}", True, ROJO_VIRUS)

    pantalla.blit(t_nivel, (10, 11))
    pantalla.blit(t_vidas, (ANCHO - t_vidas.get_width() - 10, 11))

    # Mensaje central según estado
    num_e = len(juego.enemigos)
    if num_e > 0:
        msg, col = f"VIRUS: {num_e}", ROJO_VIRUS
    elif juego.puerta_vis:
        msg, col = "ENCUENTRA LA SALIDA [EXIT]", AZUL_PUERTA
    elif cfg["num_enemigos"] == 0:
        msg, col = "USA BOMBAS PARA HALLAR LA SALIDA", CYAN
    else:
        msg, col = "DESTRUYE BLOQUES PARA HALLAR LA SALIDA", AZUL_PUERTA
    t_c = fuente.render(msg, True, col)
    pantalla.blit(t_c, t_c.get_rect(center=(ANCHO//2, 20)))


def dibujar_mapa(juego):
    for y, fila in enumerate(juego.mapa):
        for x, celda in enumerate(fila):
            rx = x * TAMANO_BLOQUE
            ry = y * TAMANO_BLOQUE + ALTO_HUD
            r  = pygame.Rect(rx, ry, TAMANO_BLOQUE, TAMANO_BLOQUE)
            if celda == 1:
                pygame.draw.rect(pantalla, GRIS_MURO, r)
                pygame.draw.rect(pantalla, GRIS_BORDE, r, 1)
            elif celda == 2:
                pygame.draw.rect(pantalla, MARRON_BLOQUE, r, border_radius=4)
            elif celda == 3:               # puerta revelada
                pygame.draw.rect(pantalla, AZUL_PUERTA, r, border_radius=4)
                t = fuente.render("EXIT", True, BLANCO)
                pantalla.blit(t, t.get_rect(center=r.center))


def dibujar_juego(juego, t):
    dibujar_mapa(juego)

    # Efectos de explosión
    for ex, ey, _ in juego.explosiones:
        r = pygame.Rect(ex*TAMANO_BLOQUE+2, ey*TAMANO_BLOQUE+2+ALTO_HUD,
                        TAMANO_BLOQUE-4, TAMANO_BLOQUE-4)
        pygame.draw.rect(pantalla, NARANJA_EXP, r, border_radius=3)

    # Bombas + barra de tiempo
    for b in juego.bombas:
        cx = b.x * TAMANO_BLOQUE + TAMANO_BLOQUE // 2
        cy = b.y * TAMANO_BLOQUE + TAMANO_BLOQUE // 2 + ALTO_HUD
        pygame.draw.circle(pantalla, AMARILLO_BOMBA, (cx, cy), 13)
        restante = max(0, b.tiempo_det - t)
        bw = int(TAMANO_BLOQUE * restante / TIEMPO_BOMBA_MS)
        by = b.y * TAMANO_BLOQUE + TAMANO_BLOQUE - 5 + ALTO_HUD
        pygame.draw.rect(pantalla, AMARILLO_BOMBA, (b.x*TAMANO_BLOQUE, by, bw, 4))

    # Enemigos
    for e in juego.enemigos:
        r = pygame.Rect(e.x*TAMANO_BLOQUE+4, e.y*TAMANO_BLOQUE+4+ALTO_HUD, 32, 32)
        pygame.draw.rect(pantalla, ROJO_VIRUS, r, border_radius=4)

    # Jugador (parpadea durante invencibilidad)
    inv      = t < juego.t_invinc
    mostrar  = not inv or (t // 150) % 2 == 0
    if mostrar and (juego.activo or juego.estado in ("nivel_claro", "victoria")):
        r = pygame.Rect(juego.jugador_x*TAMANO_BLOQUE+4,
                        juego.jugador_y*TAMANO_BLOQUE+4+ALTO_HUD, 32, 32)
        pygame.draw.rect(pantalla, VERDE_BIT, r, border_radius=4)


def dibujar_overlay(linea1, linea2, color1=VERDE_BIT):
    overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    pantalla.blit(overlay, (0, 0))
    t1 = fuente_g.render(linea1, True, color1)
    t2 = fuente.render(linea2, True, BLANCO)
    pantalla.blit(t1, t1.get_rect(center=(ANCHO//2, ALTO//2 - 25)))
    pantalla.blit(t2, t2.get_rect(center=(ANCHO//2, ALTO//2 + 20)))


# ─── Bucle principal ──────────────────────────────────────────────────────────

juego = Juego()

while True:
    t = pygame.time.get_ticks()

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.KEYDOWN:
            if   evento.key == pygame.K_UP:    juego.mover(0, -1)
            elif evento.key == pygame.K_DOWN:  juego.mover(0,  1)
            elif evento.key == pygame.K_LEFT:  juego.mover(-1, 0)
            elif evento.key == pygame.K_RIGHT: juego.mover( 1, 0)
            elif evento.key == pygame.K_SPACE: juego.poner_bomba()
            elif evento.key == pygame.K_RETURN and juego.estado == "nivel_claro":
                juego.siguiente_nivel()
            elif evento.key == pygame.K_r and juego.estado in ("game_over", "victoria"):
                juego.reiniciar()

    juego.update(t)

    pantalla.fill(NEGRO)
    dibujar_hud(juego)
    dibujar_juego(juego, t)

    if juego.estado == "nivel_claro":
        dibujar_overlay("SECTOR LIMPIO", "Presiona ENTER para continuar", VERDE_BIT)
    elif juego.estado == "game_over":
        dibujar_overlay(juego.mensaje, "Presiona R para reiniciar", ROJO_VIRUS)
    elif juego.estado == "victoria":
        dibujar_overlay("SISTEMA RESTAURADO", "Presiona R para jugar de nuevo", CYAN)

    pygame.display.flip()
    reloj.tick(60)
