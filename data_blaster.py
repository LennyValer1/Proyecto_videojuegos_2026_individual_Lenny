import pygame
import sys
import random

pygame.init()

# ─── Resolución base FIJA del juego ──────────────────────────────────────────
# El juego SIEMPRE se dibuja en esta superficie lógica.
# En pantalla completa se escala para llenar la pantalla manteniendo proporción.
COLUMNAS, FILAS   = 15, 11
TAMANO_BLOQUE     = 56
ANCHO             = COLUMNAS * TAMANO_BLOQUE   # 840
ALTO_HUD          = TAMANO_BLOQUE              # 56
ALTO              = FILAS * TAMANO_BLOQUE + ALTO_HUD  # 672

# Proporciones (fijas, basadas en TAMANO_BLOQUE)
MARGEN_SPRITE = TAMANO_BLOQUE // 7
TAM_SPRITE    = TAMANO_BLOQUE - MARGEN_SPRITE * 2
RADIO_BOMBA   = TAMANO_BLOQUE // 4
OJO_OFFSET    = TAM_SPRITE  // 4
OJO_RADIO     = max(3, TAMANO_BLOQUE // 14)
ANTENA_LARGO  = TAMANO_BLOQUE // 7

fuente   = pygame.font.SysFont("consolas", 18, bold=True)
fuente_m = pygame.font.SysFont("consolas", 26, bold=True)
fuente_g = pygame.font.SysFont("consolas", 40, bold=True)
fuente_t = pygame.font.SysFont("consolas", 60, bold=True)

# Superficie lógica — todo se dibuja aquí siempre
superficie_juego = pygame.Surface((ANCHO, ALTO))

modo_fs  = False
pantalla = pygame.display.set_mode((ANCHO, ALTO))

def _calcular_rect_escalado():
    """Calcula dónde colocar superficie_juego centrada en la pantalla real."""
    real = pygame.display.get_surface()
    pw, ph  = real.get_size()
    escala  = min(pw / ANCHO, ph / ALTO)
    nw      = int(ANCHO * escala)
    nh      = int(ALTO  * escala)
    ox      = (pw - nw) // 2
    oy      = (ph - nh) // 2
    return pygame.Rect(ox, oy, nw, nh), escala

def toggle_fullscreen():
    global modo_fs
    modo_fs = not modo_fs
    if modo_fs:
        info = pygame.display.Info()
        pygame.display.set_mode(
            (info.current_w, info.current_h), pygame.FULLSCREEN)
    else:
        pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Data Blaster")

def mouse_a_juego(pos):
    """Convierte coordenadas del mouse real a coordenadas lógicas del juego."""
    rect, escala = _calcular_rect_escalado()
    lx = (pos[0] - rect.x) / escala
    ly = (pos[1] - rect.y) / escala
    return (lx, ly)

_pantalla_real = pygame.display.get_surface()   # referencia a la pantalla real

def presentar():
    """Escala superficie_juego a la pantalla real y la muestra."""
    real = pygame.display.get_surface()
    rect, _ = _calcular_rect_escalado()
    real.fill((0, 0, 0))
    escalada = pygame.transform.scale(superficie_juego, (rect.width, rect.height))
    real.blit(escalada, (rect.x, rect.y))
    pygame.display.flip()

pygame.display.set_caption("Data Blaster")
reloj = pygame.time.Clock()

# Alias: todo el código de dibujo usa 'pantalla' — lo redirigimos a superficie_juego
pantalla = superficie_juego   # los draw van aquí; presentar() lo vuelca a la real

# ─── Paleta ───────────────────────────────────────────────────────────────────
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
MORADO        = (180, 0,   220)
VERDE_ITEM    = (100, 255, 100)
NARANJA_ITEM  = (255, 160, 0)
AZUL_ITEM     = (80,  180, 255)
DORADO        = (255, 215, 0)

# ─── Ítems ────────────────────────────────────────────────────────────────────
ITEM_BOMBA     = "bomba"
ITEM_RANGO     = "rango"
ITEM_VELOCIDAD = "velocidad"
ITEM_ESCUDO    = "escudo"

ITEMS_CONFIG = {
    ITEM_BOMBA:     {"simbolo": "+B", "color": AMARILLO_BOMBA, "desc": "+BOMBA"},
    ITEM_RANGO:     {"simbolo": "+R", "color": NARANJA_EXP,    "desc": "+RANGO"},
    ITEM_VELOCIDAD: {"simbolo": "+V", "color": AZUL_ITEM,      "desc": "+VEL"},
    ITEM_ESCUDO:    {"simbolo": "ES", "color": DORADO,         "desc": "ESCUDO"},
}

# Ítems máximos permitidos por nivel (controlado, no aleatorio ilimitado)
ITEMS_POR_NIVEL = [2, 3, 4]   # nivel 1, 2, 3

# ─── Niveles ──────────────────────────────────────────────────────────────────
NIVELES = [
    {"nombre": "TUTORIAL",           "num_enemigos": 0, "velocidad_ms": 400, "densidad": 0.25},
    {"nombre": "INFECCION",          "num_enemigos": 2, "velocidad_ms": 400, "densidad": 0.35},
    {"nombre": "DEPURACION CRITICA", "num_enemigos": 3, "velocidad_ms": 230, "densidad": 0.45},
]

RADIO_EXPLOSION    = 1          # radio inicial: 1 celda en cada dirección (cruz básica)
TIEMPO_BOMBA_MS    = 3000
DURACION_EXP_MS    = 400
VIDAS_INICIALES    = 3
DURACION_INVINC_MS = 2000
PUNTOS_ENEMIGO     = 100
PUNTOS_NIVEL       = 500

# ─── Sonidos ──────────────────────────────────────────────────────────────────
SONIDO_OK = False
SND_BOMBA = SND_EXPLOSION = SND_MUERTE = SND_ENEMIGO = None
SND_VICTORIA = SND_PUERTA = SND_ITEM = None

try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    def _gen(freq, dur, vol=0.4, forma="cuadrada", decay=True):
        import array as arr
        sr = 44100; n = int(sr * dur / 1000)
        per = int(sr / max(freq, 1)); buf = []
        for i in range(n):
            v = (1.0 if (i % per) < per // 2 else -1.0) if forma == "cuadrada" else random.uniform(-1, 1)
            if decay: v *= max(0.0, 1.0 - i / n)
            v = max(-1.0, min(1.0, v * vol))
            buf += [int(v * 32767)] * 2
        return pygame.sndarray.make_sound(pygame.sndarray.array(arr.array("h", buf)))
    SND_BOMBA     = _gen(180, 300, 0.4)
    SND_EXPLOSION = _gen(90,  400, 0.5, "ruido")
    SND_MUERTE    = _gen(120, 600, 0.4)
    SND_ENEMIGO   = _gen(320, 180, 0.4)
    SND_VICTORIA  = _gen(480, 700, 0.4, decay=False)
    SND_PUERTA    = _gen(540, 250, 0.4)
    SND_ITEM      = _gen(660, 200, 0.35)
    SONIDO_OK     = True
except Exception:
    pass

def play(snd):
    if SONIDO_OK and snd:
        try: snd.play()
        except: pass

# ─── Entidades ────────────────────────────────────────────────────────────────
class Bomba:
    def __init__(self, x, y, radio):
        self.x = x; self.y = y
        self.tiempo_det = pygame.time.get_ticks() + TIEMPO_BOMBA_MS
        self.radio = radio

class Enemigo:
    def __init__(self, x, y, vel):
        self.x = x; self.y = y; self.vel = vel
        self.direccion  = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
        self.ultimo_mov = 0

# ─── Mapa ─────────────────────────────────────────────────────────────────────
def generar_mapa(config, nivel_idx=0):
    mapa = []; candidatos = []; bloques_pos = []
    for y in range(FILAS):
        fila = []
        for x in range(COLUMNAS):
            if x==0 or x==COLUMNAS-1 or y==0 or y==FILAS-1:
                fila.append(1)
            elif x%2==0 and y%2==0:
                fila.append(1)
            elif x<3 and y<3:
                fila.append(0)
            elif random.random() < config["densidad"]:
                fila.append(2)
                bloques_pos.append((x,y))
                if x>5 or y>5: candidatos.append((x,y))
            else:
                fila.append(0)
        mapa.append(fila)
    if not candidatos:
        candidatos = [(x,y) for y in range(FILAS) for x in range(COLUMNAS) if mapa[y][x]==2]
    puerta_pos = random.choice(candidatos) if candidatos else (COLUMNAS-2, FILAS-2)

    # Cantidad fija de ítems por nivel — controlada
    max_items = ITEMS_POR_NIVEL[min(nivel_idx, len(ITEMS_POR_NIVEL)-1)]
    cands_item = [p for p in bloques_pos if p != puerta_pos]
    random.shuffle(cands_item)
    posiciones_item = cands_item[:max_items]

    # Pool balanceado por nivel
    if nivel_idx == 0:
        pool = [ITEM_RANGO, ITEM_ESCUDO]
    elif nivel_idx == 1:
        pool = [ITEM_BOMBA, ITEM_RANGO, ITEM_ESCUDO, ITEM_VELOCIDAD]
    else:
        pool = [ITEM_BOMBA, ITEM_RANGO, ITEM_ESCUDO, ITEM_VELOCIDAD, ITEM_RANGO]

    items_ocultos = {}
    for i, pos in enumerate(posiciones_item):
        items_ocultos[pos] = pool[i % len(pool)]

    return mapa, puerta_pos, items_ocultos

# ─── Juego ────────────────────────────────────────────────────────────────────
class Juego:
    def __init__(self):
        self.nivel_idx    = 0
        self.vidas        = VIDAS_INICIALES
        self.puntos       = 0
        # Power-ups acumulados entre niveles
        self.max_bombas   = 1
        self.radio_exp    = RADIO_EXPLOSION
        self.vel_jugador  = 0        # ms adicionales (negativo = más rápido)
        self.tiene_escudo = False
        self._cargar_nivel()

    def _cargar_nivel(self):
        cfg = NIVELES[self.nivel_idx]
        self.mapa, self.puerta_pos, self.items_ocultos = generar_mapa(cfg, self.nivel_idx)
        self.items_visibles = {}     # (x,y) -> tipo ítem ya revelado
        self.jugador_x  = 1; self.jugador_y = 1
        self.bombas     = []
        self.enemigos   = self._colocar_enemigos(cfg["num_enemigos"], cfg["velocidad_ms"])
        self.explosiones= []
        self.puerta_vis = False
        self.activo     = True
        self.estado     = "jugando"
        self.mensaje    = ""
        self.t_invinc   = pygame.time.get_ticks() + 1500
        self.t_ultimo_mov = 0
        # Notificación flotante de ítem recogido
        self.notif_item = ""
        self.notif_t    = 0

    def _colocar_enemigos(self, num, vel):
        esquinas = [(COLUMNAS-2, FILAS-2),(COLUMNAS-2,1),(1,FILAS-2),(COLUMNAS-2,FILAS//2)]
        enemigos = []
        for ex,ey in esquinas[:num]:
            ok = False
            for dy in range(-2,3):
                for dx in range(-2,3):
                    nx,ny = ex+dx, ey+dy
                    if 0<=nx<COLUMNAS and 0<=ny<FILAS and self.mapa[ny][nx]==0:
                        enemigos.append(Enemigo(nx,ny,vel)); ok=True; break
                if ok: break
        return enemigos

    def explotar(self, bomba):
        celdas = {(bomba.x, bomba.y)}; puerta_nueva = False
        for ddx,ddy in [(1,0),(-1,0),(0,1),(0,-1)]:
            for paso in range(1, bomba.radio + 1):
                nx = bomba.x + ddx*paso; ny = bomba.y + ddy*paso
                if not (0<=nx<COLUMNAS and 0<=ny<FILAS): break
                if self.mapa[ny][nx]==1: break
                celdas.add((nx,ny))
                if self.mapa[ny][nx]==2:
                    if (nx,ny)==self.puerta_pos:
                        self.puerta_vis=True; self.mapa[ny][nx]=3; puerta_nueva=True
                    else:
                        self.mapa[ny][nx]=0
                        # Revelar ítem si lo había
                        if (nx,ny) in self.items_ocultos:
                            self.items_visibles[(nx,ny)] = self.items_ocultos.pop((nx,ny))
                    break
        play(SND_EXPLOSION)
        if puerta_nueva: play(SND_PUERTA)
        t_fin = pygame.time.get_ticks() + DURACION_EXP_MS
        for pos in celdas: self.explosiones.append((*pos, t_fin))
        for otra in self.bombas[:]:
            if (otra.x,otra.y) in celdas:
                self.bombas.remove(otra); self.explotar(otra)
        elim = 0
        for e in self.enemigos[:]:
            if (e.x,e.y) in celdas:
                self.enemigos.remove(e); elim+=1
        if elim: self.puntos += elim*PUNTOS_ENEMIGO; play(SND_ENEMIGO)
        if (self.jugador_x,self.jugador_y) in celdas:
            self._perder_vida("ERROR CRITICO - Archivo Corrupto")

    def _perder_vida(self, msg):
        if self.tiene_escudo:
            self.tiene_escudo = False
            self.notif_item   = "ESCUDO ABSORBIO EL GOLPE"
            self.notif_t      = pygame.time.get_ticks() + 1800
            self.jugador_x=1; self.jugador_y=1
            self.t_invinc = pygame.time.get_ticks() + DURACION_INVINC_MS
            return
        play(SND_MUERTE); self.vidas -= 1
        if self.vidas<=0:
            self.activo=False; self.estado="game_over"; self.mensaje=msg
        else:
            self.jugador_x=1; self.jugador_y=1; self.bombas=[]
            self.t_invinc = pygame.time.get_ticks() + DURACION_INVINC_MS

    def _recoger_item(self, x, y):
        tipo = self.items_visibles.pop((x,y), None)
        if tipo is None: return
        play(SND_ITEM)
        self.puntos += 50
        if tipo == ITEM_BOMBA:
            self.max_bombas = min(self.max_bombas + 1, 2)   # máx 2 bombas
            self.notif_item = "+BOMBA! (max: %d)" % self.max_bombas
        elif tipo == ITEM_RANGO:
            self.radio_exp = min(self.radio_exp + 1, 3)     # máx radio 3
            self.notif_item = "+RANGO! (radio: %d)" % self.radio_exp
        elif tipo == ITEM_VELOCIDAD:
            self.vel_jugador = min(self.vel_jugador + 1, 2) # máx 2 niveles de vel
            self.notif_item = "+VELOCIDAD! (niv: %d)" % self.vel_jugador
        elif tipo == ITEM_ESCUDO:
            self.tiene_escudo = True
            self.notif_item = "ESCUDO ACTIVADO!"
        self.notif_t = pygame.time.get_ticks() + 2000

    def mover(self, dx, dy):
        if not self.activo or self.estado!="jugando": return
        t = pygame.time.get_ticks()
        # Delay base 160ms — vel=1: 110ms, vel=2: 70ms (nunca 0)
        delay = 160 - self.vel_jugador * 45
        if t - self.t_ultimo_mov < delay: return
        nx,ny = self.jugador_x+dx, self.jugador_y+dy
        if not (0<=nx<COLUMNAS and 0<=ny<FILAS): return
        if self.mapa[ny][nx] in (1,2): return
        if any(b.x==nx and b.y==ny for b in self.bombas): return
        self.jugador_x,self.jugador_y = nx,ny
        self.t_ultimo_mov = t
        self._recoger_item(nx, ny)

    def poner_bomba(self):
        if not self.activo or self.estado!="jugando": return
        if len(self.bombas) >= self.max_bombas: return
        px,py = self.jugador_x, self.jugador_y
        if not any(b.x==px and b.y==py for b in self.bombas):
            self.bombas.append(Bomba(px, py, self.radio_exp)); play(SND_BOMBA)

    def update(self, t):
        if not self.activo or self.estado!="jugando": return
        for b in self.bombas[:]:
            if b not in self.bombas: continue
            if t > b.tiempo_det: self.bombas.remove(b); self.explotar(b)
        self.explosiones = [e for e in self.explosiones if t < e[2]]
        for e in self.enemigos:
            if t - e.ultimo_mov > e.vel:
                nx,ny = e.x+e.direccion[0], e.y+e.direccion[1]
                hay_bomba = any(b.x==nx and b.y==ny for b in self.bombas)
                if 0<=nx<COLUMNAS and 0<=ny<FILAS and self.mapa[ny][nx] in (0,3) and not hay_bomba:
                    e.x,e.y = nx,ny
                else:
                    e.direccion = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
                e.ultimo_mov = t
        if t > self.t_invinc:
            for e in self.enemigos:
                if self.jugador_x==e.x and self.jugador_y==e.y:
                    self._perder_vida("SISTEMA INFECTADO"); return
        if len(self.enemigos)==0 and self.puerta_vis:
            if self.jugador_x==self.puerta_pos[0] and self.jugador_y==self.puerta_pos[1]:
                self.puntos += PUNTOS_NIVEL; play(SND_VICTORIA); self.activo=False
                self.estado = "victoria" if self.nivel_idx+1>=len(NIVELES) else "nivel_claro"

    def siguiente_nivel(self):
        self.nivel_idx += 1; self._cargar_nivel()

    def reiniciar(self):
        self.__init__()

# ─── Dibujo ───────────────────────────────────────────────────────────────────
BTN_FS_RECT = pygame.Rect(0, 0, 1, 1)

def dibujar_btn_fullscreen():
    global BTN_FS_RECT
    tam  = max(24, ALTO_HUD - 10)
    rx   = ANCHO - tam - 6
    ry   = (ALTO_HUD - tam) // 2
    rect = pygame.Rect(rx, ry, tam, tam)
    BTN_FS_RECT = rect
    mx, my = mouse_a_juego(pygame.mouse.get_pos())
    hover  = rect.collidepoint(mx, my)
    col_bg = (50, 50, 50) if hover else (30, 30, 30)
    pygame.draw.rect(pantalla, col_bg,    rect, border_radius=4)
    pygame.draw.rect(pantalla, VERDE_BIT, rect, 1, border_radius=4)
    cx, cy = rect.centerx, rect.centery
    s = tam // 5
    g = tam // 5
    if not modo_fs:
        for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            ox, oy = cx + dx*g, cy + dy*g
            pygame.draw.line(pantalla, VERDE_BIT, (ox, oy), (ox+dx*s, oy), 2)
            pygame.draw.line(pantalla, VERDE_BIT, (ox, oy), (ox, oy+dy*s), 2)
    else:
        for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            ox, oy = cx + dx*(g+s), cy + dy*(g+s)
            pygame.draw.line(pantalla, VERDE_BIT, (ox, oy), (ox-dx*s, oy), 2)
            pygame.draw.line(pantalla, VERDE_BIT, (ox, oy), (ox, oy-dy*s), 2)
    return rect


def dibujar_hud(juego, t):
    pygame.draw.rect(pantalla, GRIS_OSCURO, (0,0,ANCHO,ALTO_HUD))
    pygame.draw.line(pantalla, VERDE_BIT, (0,ALTO_HUD-1),(ANCHO,ALTO_HUD-1),2)
    cfg = NIVELES[juego.nivel_idx]

    t_niv = fuente.render(f"SECTOR {juego.nivel_idx+1}: {cfg['nombre']}", True, VERDE_BIT)
    pantalla.blit(t_niv, (10, 6))
    vidas_str  = "■"*juego.vidas + "□"*(VIDAS_INICIALES-juego.vidas)
    escudo_str = " [ESCUDO]" if juego.tiene_escudo else ""
    t_v = fuente.render(f"VIDAS: {vidas_str}{escudo_str}", True, ROJO_VIRUS if not juego.tiene_escudo else DORADO)
    pantalla.blit(t_v, (10, ALTO_HUD//2+2))

    t_pts = fuente.render(f"PTS: {juego.puntos:06d}", True, AMARILLO_BOMBA)
    pantalla.blit(t_pts, (ANCHO//2 - t_pts.get_width()//2, 6))

    num_e = len(juego.enemigos)
    if num_e>0: msg,col = f"VIRUS: {num_e}  ELIMINALOS!", ROJO_VIRUS
    elif juego.puerta_vis: msg,col = ">>> ENCUENTRA LA SALIDA [EXIT] <<<", AZUL_PUERTA
    elif cfg["num_enemigos"]==0: msg,col = "DESTRUYE BLOQUES PARA HALLAR LA SALIDA", CYAN
    else: msg,col = "DESTRUYE BLOQUES PARA HALLAR LA SALIDA", AZUL_PUERTA
    t_c = fuente.render(msg, True, col)
    pantalla.blit(t_c, t_c.get_rect(center=(ANCHO//2, ALTO_HUD*3//4)))

    # Power-ups (dejando espacio para el botón)
    px = ANCHO - max(24, ALTO_HUD-10) - 14
    indicadores = [(f"BOMBA x{juego.max_bombas}", AMARILLO_BOMBA),
                   (f"RANGO:{juego.radio_exp}", NARANJA_EXP)]
    if juego.vel_jugador>0:
        indicadores.append((f"VEL+{juego.vel_jugador}", AZUL_ITEM))
    for idx,(txt,col) in enumerate(reversed(indicadores)):
        surf = fuente.render(txt, True, col)
        pantalla.blit(surf, (px - surf.get_width(), 6 + idx*18))

    # Botón pantalla completa (siempre encima)
    dibujar_btn_fullscreen()

    # Notificación flotante de ítem
    if juego.notif_item and t < juego.notif_t:
        alpha = min(255, int(255 * (juego.notif_t - t) / 800))
        surf  = fuente_m.render(juego.notif_item, True, DORADO)
        surf.set_alpha(alpha)
        pantalla.blit(surf, surf.get_rect(center=(ANCHO//2, ALTO_HUD + TAMANO_BLOQUE*2)))


def dibujar_mapa(juego):
    for y,fila in enumerate(juego.mapa):
        for x,celda in enumerate(fila):
            rx = x*TAMANO_BLOQUE; ry = y*TAMANO_BLOQUE+ALTO_HUD
            r  = pygame.Rect(rx,ry,TAMANO_BLOQUE,TAMANO_BLOQUE)
            if celda==1:
                pygame.draw.rect(pantalla, GRIS_MURO, r)
                pygame.draw.rect(pantalla, GRIS_BORDE, r, 1)
                ins = TAMANO_BLOQUE//7
                pygame.draw.rect(pantalla,(90,90,90), r.inflate(-ins*2,-ins*2), 1)
            elif celda==2:
                pygame.draw.rect(pantalla, MARRON_BLOQUE, r, border_radius=4)
                ins = TAMANO_BLOQUE//9
                pygame.draw.rect(pantalla,(180,100,20), r.inflate(-ins*2,-ins*2), border_radius=3)
                t = fuente.render("DAT", True,(200,140,80))
                pantalla.blit(t, t.get_rect(center=r.center))
            elif celda==3:
                pygame.draw.rect(pantalla, AZUL_PUERTA, r, border_radius=4)
                pygame.draw.rect(pantalla, CYAN, r.inflate(-4,-4), 2, border_radius=4)
                t = fuente.render("EXIT", True, BLANCO)
                pantalla.blit(t, t.get_rect(center=r.center))

    # Ítems visibles en el mapa
    for (ix,iy),tipo in juego.items_visibles.items():
        cfg_i = ITEMS_CONFIG[tipo]
        rx = ix*TAMANO_BLOQUE; ry = iy*TAMANO_BLOQUE+ALTO_HUD
        r  = pygame.Rect(rx,ry,TAMANO_BLOQUE,TAMANO_BLOQUE)
        pad = TAMANO_BLOQUE//6
        ri  = r.inflate(-pad*2,-pad*2)
        pygame.draw.rect(pantalla, NEGRO, ri, border_radius=4)
        pygame.draw.rect(pantalla, cfg_i["color"], ri, 2, border_radius=4)
        t = fuente.render(cfg_i["simbolo"], True, cfg_i["color"])
        pantalla.blit(t, t.get_rect(center=r.center))


def _dibujar_pixel_art(grid, colores, ox, oy, ps):
    """Dibuja una cuadrícula de pixel art. grid=lista de filas de ints, ps=tamaño de pixel."""
    for gy, fila in enumerate(grid):
        for gx, v in enumerate(fila):
            if v == 0: continue
            col = colores[v]
            pantalla.fill(col, (ox + gx*ps, oy + gy*ps, ps, ps))


def _dibujar_jugador(gx, gy, tiene_escudo, t):
    """Sprite jugador estilo Bomberman — 8x10 pixels."""
    # ps se calcula para que 8 pixels entren en el bloque con margen
    ps  = max(2, (TAMANO_BLOQUE - 6) // 10)   # 10 filas de alto
    ancho_sprite = ps * 8
    alto_sprite  = ps * 10
    ox = gx * TAMANO_BLOQUE + (TAMANO_BLOQUE - ancho_sprite) // 2
    oy = gy * TAMANO_BLOQUE + ALTO_HUD + (TAMANO_BLOQUE - alto_sprite) // 2

    col_cuerpo = DORADO    if tiene_escudo else VERDE_BIT
    col_piel   = (180,255,160) if not tiene_escudo else (255,240,180)
    col_visor  = CYAN
    col_borde  = VERDE_OSCURO if not tiene_escudo else (180,140,0)

    # 0=transparente 1=cuerpo 2=piel/cara 3=visor 4=borde/sombra
    grid = [
        [0,0,0,1,1,0,0,0],   # antena base
        [0,0,1,1,1,1,0,0],   # cabeza top
        [0,1,2,2,2,2,1,0],   # cara
        [0,1,3,2,2,3,1,0],   # ojos
        [0,1,2,2,2,2,1,0],   # cara bottom
        [0,0,1,1,1,1,0,0],   # cuello
        [0,1,1,1,1,1,1,0],   # hombros
        [0,1,4,1,1,4,1,0],   # cuerpo
        [0,0,1,0,0,1,0,0],   # piernas
        [0,1,1,0,0,1,1,0],   # pies
    ]
    colores = {1: col_cuerpo, 2: col_piel, 3: col_visor, 4: col_borde}
    _dibujar_pixel_art(grid, colores, ox, oy, ps)

    # Escudo: borde brillante parpadeante
    if tiene_escudo and (t // 200) % 2 == 0:
        pygame.draw.rect(pantalla, BLANCO,
                         (ox-1, oy-1, ancho_sprite+2, alto_sprite+2), 1)


def _dibujar_enemigo(gx, gy):
    """Sprite enemigo estilo fantasma — 8x9 pixels."""
    ps  = max(2, (TAMANO_BLOQUE - 6) // 9)    # 9 filas de alto
    ancho_sprite = ps * 8
    alto_sprite  = ps * 9
    ox = gx * TAMANO_BLOQUE + (TAMANO_BLOQUE - ancho_sprite) // 2
    oy = gy * TAMANO_BLOQUE + ALTO_HUD + (TAMANO_BLOQUE - alto_sprite) // 2

    # 0=transparente 1=cuerpo 2=ojo blanco 3=pupila 4=tentáculo
    grid = [
        [0,0,1,1,1,1,0,0],   # cabeza top
        [0,1,1,1,1,1,1,0],   # cabeza
        [1,1,2,1,1,2,1,1],   # ojos
        [1,1,3,1,1,3,1,1],   # pupilas
        [1,1,1,1,1,1,1,1],   # cuerpo
        [1,1,1,1,1,1,1,1],   # cuerpo
        [1,1,1,1,1,1,1,1],   # faldón
        [1,0,1,0,0,1,0,1],   # tentáculos
        [1,0,1,0,0,1,0,1],   # tentáculos
    ]
    colores = {1: ROJO_VIRUS, 2: BLANCO, 3: NEGRO, 4: (200,20,20)}
    _dibujar_pixel_art(grid, colores, ox, oy, ps)


def dibujar_juego(juego, t):
    dibujar_mapa(juego)
    # Explosiones
    for ex,ey,_ in juego.explosiones:
        pad = TAMANO_BLOQUE//14
        r = pygame.Rect(ex*TAMANO_BLOQUE+pad, ey*TAMANO_BLOQUE+pad+ALTO_HUD,
                        TAMANO_BLOQUE-pad*2, TAMANO_BLOQUE-pad*2)
        pygame.draw.rect(pantalla, NARANJA_EXP, r, border_radius=3)
        inn = TAMANO_BLOQUE//5
        pygame.draw.rect(pantalla, AMARILLO_BOMBA, r.inflate(-inn,-inn), border_radius=2)
    # Bombas
    for b in juego.bombas:
        cx = b.x*TAMANO_BLOQUE+TAMANO_BLOQUE//2
        cy = b.y*TAMANO_BLOQUE+TAMANO_BLOQUE//2+ALTO_HUD
        restante = max(0, b.tiempo_det-t)
        vis = True
        if restante<1000: vis=(t//100)%2==0
        if vis:
            pygame.draw.circle(pantalla,AMARILLO_BOMBA,(cx,cy),RADIO_BOMBA)
            pygame.draw.circle(pantalla,NEGRO,(cx,cy),RADIO_BOMBA//2)
            pygame.draw.circle(pantalla,ROJO_VIRUS,(cx-RADIO_BOMBA//4,cy-RADIO_BOMBA//4),RADIO_BOMBA//4)
        bw = int(TAMANO_BLOQUE*restante/TIEMPO_BOMBA_MS)
        by = b.y*TAMANO_BLOQUE+TAMANO_BLOQUE-(TAMANO_BLOQUE//10)+ALTO_HUD
        bh = max(3,TAMANO_BLOQUE//14)
        pygame.draw.rect(pantalla,GRIS_OSCURO,(b.x*TAMANO_BLOQUE,by,TAMANO_BLOQUE,bh))
        col_b = VERDE_BIT if restante>1500 else (AMARILLO_BOMBA if restante>800 else ROJO_VIRUS)
        pygame.draw.rect(pantalla,col_b,(b.x*TAMANO_BLOQUE,by,bw,bh))
    # Enemigos — sprite pixel art estilo fantasma (opción B)
    for e in juego.enemigos:
        _dibujar_enemigo(e.x, e.y)
    # Jugador — sprite pixel art estilo Bomberman (opción B)
    inv=t<juego.t_invinc; mostrar=not inv or (t//150)%2==0
    if mostrar and (juego.activo or juego.estado in ("nivel_claro","victoria")):
        _dibujar_jugador(juego.jugador_x, juego.jugador_y,
                         juego.tiene_escudo, t)


def dibujar_overlay(linea1, linea2, color1=VERDE_BIT, linea3=""):
    ov=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA); ov.fill((0,0,0,200))
    pantalla.blit(ov,(0,0))
    t1=fuente_g.render(linea1,True,color1)
    t2=fuente_m.render(linea2,True,BLANCO)
    pantalla.blit(t1,t1.get_rect(center=(ANCHO//2,ALTO//2-40)))
    pantalla.blit(t2,t2.get_rect(center=(ANCHO//2,ALTO//2+10)))
    if linea3:
        t3=fuente.render(linea3,True,CYAN)
        pantalla.blit(t3,t3.get_rect(center=(ANCHO//2,ALTO//2+50)))

# ─── Menú ─────────────────────────────────────────────────────────────────────
opcion_menu = 0   # 0 = ventana, 1 = pantalla completa

def dibujar_menu(t):
    global opcion_menu
    pantalla.fill(NEGRO)
    off=(t//40)%TAMANO_BLOQUE
    for x in range(-TAMANO_BLOQUE,ANCHO+TAMANO_BLOQUE,TAMANO_BLOQUE):
        pygame.draw.line(pantalla,(0,35,0),(x+off,0),(x+off,ALTO),1)
    for y in range(-TAMANO_BLOQUE,ALTO+TAMANO_BLOQUE,TAMANO_BLOQUE):
        pygame.draw.line(pantalla,(0,35,0),(0,y+off),(ANCHO,y+off),1)

    tit=fuente_t.render("DATA BLASTER",True,NEGRO)
    pantalla.blit(tit,tit.get_rect(center=(ANCHO//2+3,103)))
    tit=fuente_t.render("DATA BLASTER",True,VERDE_BIT)
    pantalla.blit(tit,tit.get_rect(center=(ANCHO//2,100)))
    sub=fuente_m.render("- Purga el sistema. Elimina el malware. -",True,CYAN)
    pantalla.blit(sub,sub.get_rect(center=(ANCHO//2,155)))
    pygame.draw.line(pantalla,VERDE_OSCURO,(60,178),(ANCHO-60,178),1)

    # Selector de modo de pantalla
    y_base = 195
    modo_lbl = fuente_m.render("MODO DE PANTALLA", True, AMARILLO_BOMBA)
    pantalla.blit(modo_lbl, modo_lbl.get_rect(center=(ANCHO//2, y_base)))
    y_base += 38

    opciones = ["  VENTANA  ", "  PANTALLA COMPLETA  "]
    for i, op in enumerate(opciones):
        sel = i == opcion_menu
        col_fondo = VERDE_BIT if sel else GRIS_OSCURO
        col_texto  = NEGRO    if sel else GRIS_BORDE
        surf = fuente_m.render(op, True, col_texto)
        rw = surf.get_width()+24; rh = surf.get_height()+10
        rx = ANCHO//2 - rw//2 + (i-0)*220 - 110
        ry = y_base
        pygame.draw.rect(pantalla, col_fondo, (rx, ry, rw, rh), border_radius=6)
        pygame.draw.rect(pantalla, VERDE_BIT, (rx,ry,rw,rh), 1 if not sel else 0, border_radius=6)
        pantalla.blit(surf, (rx+12, ry+5))

    y_base += 52
    pygame.draw.line(pantalla,VERDE_OSCURO,(60,y_base),(ANCHO-60,y_base),1)
    y_base += 18

    controles=[
        ("CONTROLES", VERDE_BIT),
        ("Flechas  →  Mover a Bit-E",               BLANCO),
        ("ESPACIO  →  Colocar bomba de codigo",      BLANCO),
        ("ENTER    →  Iniciar / avanzar sector",     BLANCO),
        ("F11      →  Alternar pantalla completa",   CYAN),
        ("R        →  Reiniciar / volver al menu",   BLANCO),
    ]
    for txt,col in controles:
        s=fuente.render(txt,True,col)
        pantalla.blit(s,s.get_rect(center=(ANCHO//2,y_base))); y_base+=26

    pygame.draw.line(pantalla,VERDE_OSCURO,(60,y_base+4),(ANCHO-60,y_base+4),1)
    y_base+=18
    items_info=[
        ("ITEMS (aparecen al destruir bloques)", AMARILLO_BOMBA),
        ("+B = mas bombas    +R = mayor rango    +V = velocidad    ES = escudo", BLANCO),
    ]
    for txt,col in items_info:
        s=fuente.render(txt,True,col)
        pantalla.blit(s,s.get_rect(center=(ANCHO//2,y_base))); y_base+=24

    if (t//500)%2==0:
        s=fuente_m.render(">>> PRESIONA ENTER PARA INICIAR <<<",True,VERDE_BIT)
        pantalla.blit(s,s.get_rect(center=(ANCHO//2,ALTO-48)))
    s=fuente.render("Lenny Valer  |  Videojuegos y Aplicaciones Moviles  |  2026",True,(60,60,60))
    pantalla.blit(s,s.get_rect(center=(ANCHO//2,ALTO-16)))

    # Botón pantalla completa en el menú también
    dibujar_btn_fullscreen()

    presentar()

# ─── Bucle principal ──────────────────────────────────────────────────────────
estado_app = "menu"
juego      = None
opcion_menu = 0

while True:
    t = pygame.time.get_ticks()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        # Click en el botón de pantalla completa (funciona en menú y en juego)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            pos_logica = mouse_a_juego(ev.pos)
            if BTN_FS_RECT.collidepoint(pos_logica):
                toggle_fullscreen()

        if ev.type == pygame.KEYDOWN:

            # F11 alterna pantalla completa en cualquier momento
            if ev.key == pygame.K_F11:
                toggle_fullscreen()

            elif estado_app == "menu":
                if ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    opcion_menu = 1 - opcion_menu   # alterna entre 0 y 1
                elif ev.key == pygame.K_RETURN:
                    # Aplicar modo seleccionado
                    fs_elegido = (opcion_menu == 1)
                    if fs_elegido != modo_fs:
                        toggle_fullscreen()
                    juego      = Juego()
                    estado_app = "jugando"

            elif estado_app == "jugando":
                if   ev.key == pygame.K_UP:    juego.mover(0,-1)
                elif ev.key == pygame.K_DOWN:  juego.mover(0, 1)
                elif ev.key == pygame.K_LEFT:  juego.mover(-1,0)
                elif ev.key == pygame.K_RIGHT: juego.mover( 1,0)
                elif ev.key == pygame.K_SPACE: juego.poner_bomba()
                elif ev.key == pygame.K_RETURN and juego.estado=="nivel_claro":
                    juego.siguiente_nivel()
                elif ev.key == pygame.K_r and juego.estado in ("game_over","victoria"):
                    if modo_fs: toggle_fullscreen()
                    estado_app = "menu"

    # Movimiento continuo si se mantiene la tecla presionada
    if estado_app == "jugando" and juego and juego.estado == "jugando":
        teclas = pygame.key.get_pressed()
        if   teclas[pygame.K_UP]:    juego.mover(0,-1)
        elif teclas[pygame.K_DOWN]:  juego.mover(0, 1)
        elif teclas[pygame.K_LEFT]:  juego.mover(-1,0)
        elif teclas[pygame.K_RIGHT]: juego.mover( 1,0)

    if estado_app == "menu":
        dibujar_menu(t); continue

    juego.update(t)
    pantalla.fill(NEGRO)
    dibujar_hud(juego, t)
    dibujar_juego(juego, t)

    if juego.estado == "nivel_claro":
        dibujar_overlay("SECTOR LIMPIO", f"Puntuacion: {juego.puntos:06d}",
                        VERDE_BIT, "Presiona ENTER para continuar")
    elif juego.estado == "game_over":
        dibujar_overlay(juego.mensaje, f"Puntuacion final: {juego.puntos:06d}",
                        ROJO_VIRUS, "Presiona R para volver al menu")
    elif juego.estado == "victoria":
        dibujar_overlay("SISTEMA RESTAURADO", f"Puntuacion final: {juego.puntos:06d}",
                        CYAN, "Presiona R para volver al menu")

    presentar()
    reloj.tick(60)