import pygame
import sys
import random

pygame.init()

# ─── Resolución base FIJA del juego ──────────────────────────────────────────
COLUMNAS, FILAS   = 15, 11
TAMANO_BLOQUE     = 56
ANCHO             = COLUMNAS * TAMANO_BLOQUE
ALTO_HUD          = TAMANO_BLOQUE
ALTO              = FILAS * TAMANO_BLOQUE + ALTO_HUD

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

superficie_juego = pygame.Surface((ANCHO, ALTO))
modo_fs  = False
pantalla = pygame.display.set_mode((ANCHO, ALTO))

def _calcular_rect_escalado():
    real = pygame.display.get_surface()
    pw, ph  = real.get_size()
    escala  = min(pw / ANCHO, ph / ALTO)
    nw, nh  = int(ANCHO * escala), int(ALTO * escala)
    return pygame.Rect((pw-nw)//2, (ph-nh)//2, nw, nh), escala

def toggle_fullscreen():
    global modo_fs
    modo_fs = not modo_fs
    if modo_fs:
        info = pygame.display.Info()
        pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
    else:
        pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Data Blaster")

def mouse_a_juego(pos):
    rect, escala = _calcular_rect_escalado()
    return ((pos[0]-rect.x)/escala, (pos[1]-rect.y)/escala)

def presentar():
    real = pygame.display.get_surface()
    rect, _ = _calcular_rect_escalado()
    real.fill((0,0,0))
    real.blit(pygame.transform.scale(superficie_juego, (rect.width, rect.height)), (rect.x, rect.y))
    pygame.display.flip()

pygame.display.set_caption("Data Blaster")
reloj   = pygame.time.Clock()
pantalla = superficie_juego

# ─── Paleta ───────────────────────────────────────────────────────────────────
NEGRO          = (0,   0,   0)
VERDE_BIT      = (57,  255, 20)
VERDE_OSCURO   = (0,   120, 0)
GRIS_MURO      = (70,  70,  70)
GRIS_BORDE     = (95,  95,  95)
MARRON_BLOQUE  = (150, 75,  0)
ROJO_VIRUS     = (255, 50,  50)
AMARILLO_BOMBA = (255, 220, 0)
NARANJA_EXP    = (255, 140, 0)
AZUL_PUERTA    = (30,  144, 255)
BLANCO         = (255, 255, 255)
GRIS_OSCURO    = (20,  20,  20)
CYAN           = (0,   220, 220)
MORADO         = (180, 0,   220)
AZUL_ITEM      = (80,  180, 255)
DORADO         = (255, 215, 0)

# ─── Ítems ────────────────────────────────────────────────────────────────────
ITEM_BOMBA     = "bomba"
ITEM_RANGO     = "rango"
ITEM_VELOCIDAD = "velocidad"
ITEM_ESCUDO    = "escudo"
ITEMS_CONFIG   = {
    ITEM_BOMBA:     {"simbolo": "+B", "color": AMARILLO_BOMBA},
    ITEM_RANGO:     {"simbolo": "+R", "color": NARANJA_EXP},
    ITEM_VELOCIDAD: {"simbolo": "+V", "color": AZUL_ITEM},
    ITEM_ESCUDO:    {"simbolo": "ES", "color": DORADO},
}
ITEMS_POR_NIVEL = [2, 3, 4, 6]   # nivel 4 tiene 6 ítems — el más difícil merece más recompensas

# ─── Niveles ──────────────────────────────────────────────────────────────────
NIVELES = [
    {"nombre": "TUTORIAL",           "num_enemigos": 0, "velocidad_ms": 400, "densidad": 0.25, "copias": False, "col":4, "fil":8},
    {"nombre": "INFECCION",          "num_enemigos": 2, "velocidad_ms": 400, "densidad": 0.35, "copias": False, "col":4, "fil":8},
    {"nombre": "DEPURACION CRITICA", "num_enemigos": 3, "velocidad_ms": 230, "densidad": 0.45, "copias": False, "col":4, "fil":8},
    {"nombre": "PROTOCOLO ESPEJO",   "num_enemigos": 3, "velocidad_ms": 280, "densidad": 0.40, "copias": True,  "col":4, "fil":8},
]

# Dimensiones del mapa — nivel 4 usa mapa más grande
MAPA_NORMAL = (15, 11)   # columnas, filas niveles 1-3
MAPA_BOSS   = (21, 15)   # columnas, filas nivel 4 (mapa grande)

RADIO_EXPLOSION    = 1
TIEMPO_BOMBA_MS    = 3000
DURACION_EXP_MS    = 400
VIDAS_INICIALES    = 3
DURACION_INVINC_MS = 2000
PUNTOS_ENEMIGO     = 100
PUNTOS_NIVEL       = 500
debug_activo       = False

# Variables de mapa activo (cambian al cargar nivel 4)
COLUMNAS_ACT = COLUMNAS
FILAS_ACT    = FILAS
TB_ACT       = TAMANO_BLOQUE   # tamaño de bloque activo

def _dimensiones_nivel(nivel_idx):
    """Devuelve (columnas, filas, tamano_bloque) según el nivel."""
    if nivel_idx == 3:
        col, fil = MAPA_BOSS
        tb = min((ANCHO-2) // col, (ALTO - TAMANO_BLOQUE - 2) // fil)
        return col, fil, max(32, tb)
    return COLUMNAS, FILAS, TAMANO_BLOQUE

# ─── Sonidos ──────────────────────────────────────────────────────────────────
SONIDO_OK = False
SND_BOMBA = SND_EXPLOSION = SND_MUERTE = SND_ENEMIGO = None
SND_VICTORIA = SND_PUERTA = SND_ITEM = None

try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
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
        try:
            canal = pygame.mixer.find_channel()
            if canal: canal.play(snd)
        except: pass

# ─── Ranking ──────────────────────────────────────────────────────────────────
ranking_sesion = []
def registrar_puntaje(pts):
    global ranking_sesion
    ranking_sesion.append(pts)
    ranking_sesion = sorted(ranking_sesion, reverse=True)[:5]

# ─── Entidades ────────────────────────────────────────────────────────────────
class Bomba:
    def __init__(self, x, y, radio):
        self.x = x; self.y = y
        self.tiempo_det = pygame.time.get_ticks() + TIEMPO_BOMBA_MS
        self.radio = radio

class Enemigo:
    def __init__(self, x, y, vel, es_copia=False):
        self.x = x; self.y = y; self.vel = vel
        self.direccion      = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
        self.ultimo_mov     = 0
        self.es_copia       = es_copia
        self.vidas          = 3 if es_copia else 1
        self.radio_bomba    = 2
        self.t_ultima_bomba = 0
        self.delay_bomba    = random.randint(3000, 6000)

# ─── Mapa ─────────────────────────────────────────────────────────────────────
def generar_mapa(config, nivel_idx=0):
    col, fil, _ = _dimensiones_nivel(nivel_idx)
    mapa = []; candidatos = []; bloques_pos = []
    for y in range(fil):
        fila = []
        for x in range(col):
            if x==0 or x==col-1 or y==0 or y==fil-1:
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
        candidatos = [(x,y) for y in range(fil) for x in range(col) if mapa[y][x]==2]
    puerta_pos = random.choice(candidatos) if candidatos else (col-2, fil-2)
    max_items  = ITEMS_POR_NIVEL[min(nivel_idx, len(ITEMS_POR_NIVEL)-1)]
    cands_item = [p for p in bloques_pos if p != puerta_pos]
    random.shuffle(cands_item)
    if nivel_idx == 0:   pool = [ITEM_RANGO, ITEM_ESCUDO]
    elif nivel_idx == 1: pool = [ITEM_BOMBA, ITEM_RANGO, ITEM_ESCUDO, ITEM_VELOCIDAD]
    elif nivel_idx == 2: pool = [ITEM_BOMBA, ITEM_RANGO, ITEM_ESCUDO, ITEM_VELOCIDAD, ITEM_RANGO]
    else:                pool = [ITEM_BOMBA, ITEM_RANGO, ITEM_ESCUDO, ITEM_VELOCIDAD, ITEM_BOMBA, ITEM_RANGO]
    # Para nivel 4 mezclar aleatoriamente el pool para que no siempre salgan en el mismo orden
    if nivel_idx == 3:   random.shuffle(pool)
    items_ocultos = {pos: pool[i % len(pool)] for i, pos in enumerate(cands_item[:max_items])}
    return mapa, puerta_pos, items_ocultos

# ─── Juego ────────────────────────────────────────────────────────────────────
class Juego:
    def __init__(self):
        self.nivel_idx   = 0
        self.vidas       = VIDAS_INICIALES
        self.puntos      = 0
        self.max_bombas  = 1
        self.radio_exp   = RADIO_EXPLOSION
        self.vel_jugador = 0
        self.tiene_escudo = False
        self._cargar_nivel()

    def _cargar_nivel(self):
        global superficie_juego, pantalla, COLUMNAS_ACT, FILAS_ACT, TB_ACT
        cfg = NIVELES[self.nivel_idx]
        COLUMNAS_ACT, FILAS_ACT, TB_ACT = _dimensiones_nivel(self.nivel_idx)
        # Redimensionar superficie lógica si el nivel 4 tiene mapa más grande
        ancho_nv = COLUMNAS_ACT * TB_ACT
        alto_nv  = FILAS_ACT * TB_ACT + ALTO_HUD
        if superficie_juego.get_size() != (ancho_nv, alto_nv):
            superficie_juego = pygame.Surface((ancho_nv, alto_nv))
            pantalla = superficie_juego
        self.mapa, self.puerta_pos, self.items_ocultos = generar_mapa(cfg, self.nivel_idx)
        self.items_visibles  = {}
        self.jugador_x = 1;  self.jugador_y = 1
        self.bombas          = []
        self.bombas_enemigas = []
        self.enemigos        = self._colocar_enemigos(cfg["num_enemigos"], cfg["velocidad_ms"], cfg.get("copias", False))
        self.explosiones     = []
        self.puerta_vis      = False
        self.activo          = True
        self.estado          = "jugando"
        self.mensaje         = ""
        self.t_invinc        = pygame.time.get_ticks() + 1500
        self.t_ultimo_mov    = 0
        self.notif_item      = ""
        self.notif_t         = 0
        if self.nivel_idx == 3:
            self.vidas = 1

    def _colocar_enemigos(self, num, vel, es_copia=False):
        esquinas = [(COLUMNAS-2,FILAS-2),(COLUMNAS-2,1),(1,FILAS-2),(COLUMNAS-2,FILAS//2)]
        enemigos = []
        for ex,ey in esquinas[:num]:
            ok = False
            for dy in range(-2,3):
                for dx in range(-2,3):
                    nx,ny = ex+dx, ey+dy
                    if 0<=nx<COLUMNAS and 0<=ny<FILAS and self.mapa[ny][nx]==0:
                        enemigos.append(Enemigo(nx,ny,vel,es_copia)); ok=True; break
                if ok: break
        return enemigos

    def explotar(self, bomba, es_enemiga=False):
        col_a = len(self.mapa[0]) if self.mapa else COLUMNAS_ACT
        fil_a = len(self.mapa)    if self.mapa else FILAS_ACT
        celdas = {(bomba.x, bomba.y)}; puerta_nueva = False
        for ddx,ddy in [(1,0),(-1,0),(0,1),(0,-1)]:
            for paso in range(1, bomba.radio+1):
                nx = bomba.x+ddx*paso; ny = bomba.y+ddy*paso
                if not (0<=nx<col_a and 0<=ny<fil_a): break
                if self.mapa[ny][nx]==1: break
                celdas.add((nx,ny))
                if self.mapa[ny][nx]==2:
                    if (nx,ny)==self.puerta_pos:
                        self.puerta_vis=True; self.mapa[ny][nx]=3; puerta_nueva=True
                    else:
                        self.mapa[ny][nx]=0
                        if (nx,ny) in self.items_ocultos:
                            self.items_visibles[(nx,ny)] = self.items_ocultos.pop((nx,ny))
                    break
        play(SND_EXPLOSION)
        if puerta_nueva: play(SND_PUERTA)
        t_fin = pygame.time.get_ticks() + DURACION_EXP_MS
        for pos in celdas: self.explosiones.append((*pos, t_fin))
        for otra in self.bombas[:]:
            if (otra.x,otra.y) in celdas: self.bombas.remove(otra); self.explotar(otra, es_enemiga=False)
        for otra in self.bombas_enemigas[:]:
            if (otra.x,otra.y) in celdas: self.bombas_enemigas.remove(otra); self.explotar(otra, es_enemiga=True)
        elim = 0
        for e in self.enemigos[:]:
            if (e.x,e.y) in celdas:
                if e.es_copia:
                    if es_enemiga: continue   # inmunes a sus propias bombas
                    e.vidas -= 1
                    if e.vidas <= 0: self.enemigos.remove(e); elim += 1
                    else: play(SND_ENEMIGO)
                else:
                    self.enemigos.remove(e); elim += 1
        if elim: self.puntos += elim*PUNTOS_ENEMIGO; play(SND_ENEMIGO)
        if (self.jugador_x,self.jugador_y) in celdas:
            self._perder_vida("ERROR CRITICO - Archivo Corrupto")

    def _perder_vida(self, msg):
        if self.tiene_escudo:
            self.tiene_escudo = False
            self.notif_item = "ESCUDO ABSORBIO EL GOLPE"
            self.notif_t    = pygame.time.get_ticks() + 1800
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
        play(SND_ITEM); self.puntos += 50
        if   tipo == ITEM_BOMBA:     self.max_bombas  = min(self.max_bombas+1, 2);  self.notif_item = "+BOMBA! (max: %d)" % self.max_bombas
        elif tipo == ITEM_RANGO:     self.radio_exp   = min(self.radio_exp+1, 3);   self.notif_item = "+RANGO! (radio: %d)" % self.radio_exp
        elif tipo == ITEM_VELOCIDAD: self.vel_jugador = min(self.vel_jugador+1, 2); self.notif_item = "+VELOCIDAD! (niv: %d)" % self.vel_jugador
        elif tipo == ITEM_ESCUDO:    self.tiene_escudo = True;                       self.notif_item = "ESCUDO ACTIVADO!"
        self.notif_t = pygame.time.get_ticks() + 2000

    def mover(self, dx, dy):
        if not self.activo or self.estado!="jugando": return
        t = pygame.time.get_ticks()
        delay = 160 - self.vel_jugador * 45
        if t - self.t_ultimo_mov < delay: return
        nx,ny = self.jugador_x+dx, self.jugador_y+dy
        col_a = len(self.mapa[0]) if self.mapa else COLUMNAS
        fil_a = len(self.mapa)    if self.mapa else FILAS
        if not (0<=nx<col_a and 0<=ny<fil_a): return
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
            self.bombas.append(Bomba(px,py,self.radio_exp)); play(SND_BOMBA)

    def update(self, t):
        if not self.activo or self.estado!="jugando": return
        for b in self.bombas[:]:
            if b not in self.bombas: continue
            if t > b.tiempo_det: self.bombas.remove(b); self.explotar(b, es_enemiga=False)
        for b in self.bombas_enemigas[:]:
            if b not in self.bombas_enemigas: continue
            if t > b.tiempo_det: self.bombas_enemigas.remove(b); self.explotar(b, es_enemiga=True)
        self.explosiones = [e for e in self.explosiones if t < e[2]]
        todas_bombas = self.bombas + self.bombas_enemigas
        col_a = len(self.mapa[0]) if self.mapa else COLUMNAS
        fil_a = len(self.mapa)    if self.mapa else FILAS
        for e in self.enemigos:
            if t - e.ultimo_mov > e.vel:
                nx,ny = e.x+e.direccion[0], e.y+e.direccion[1]
                hay_bomba = any(b.x==nx and b.y==ny for b in todas_bombas)
                if 0<=nx<col_a and 0<=ny<fil_a and self.mapa[ny][nx] in (0,3) and not hay_bomba:
                    e.x,e.y = nx,ny
                else:
                    e.direccion = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
                e.ultimo_mov = t
            if e.es_copia and t - e.t_ultima_bomba > e.delay_bomba:
                if not any(b.x==e.x and b.y==e.y for b in self.bombas_enemigas):
                    self.bombas_enemigas.append(Bomba(e.x, e.y, e.radio_bomba))
                    e.t_ultima_bomba = t
                    e.delay_bomba    = random.randint(3000, 6000)
        if t > self.t_invinc:
            for e in self.enemigos:
                if self.jugador_x==e.x and self.jugador_y==e.y:
                    self._perder_vida("SISTEMA INFECTADO"); return
        if len(self.enemigos)==0 and self.puerta_vis:
            if self.jugador_x==self.puerta_pos[0] and self.jugador_y==self.puerta_pos[1]:
                self.puntos += PUNTOS_NIVEL; play(SND_VICTORIA); self.activo=False
                self.estado = "victoria" if self.nivel_idx+1>=len(NIVELES) else "nivel_claro"

    def siguiente_nivel(self): self.nivel_idx += 1; self._cargar_nivel()
    def reiniciar(self):        self.__init__()

# ─── Dibujo ───────────────────────────────────────────────────────────────────
BTN_FS_RECT = pygame.Rect(0,0,1,1)

def dibujar_btn_fullscreen():
    global BTN_FS_RECT
    tam  = max(24, ALTO_HUD-10)
    rx   = ANCHO-tam-6; ry = (ALTO_HUD-tam)//2
    rect = pygame.Rect(rx,ry,tam,tam); BTN_FS_RECT = rect
    mx,my = mouse_a_juego(pygame.mouse.get_pos())
    col_bg = (50,50,50) if rect.collidepoint(mx,my) else (30,30,30)
    pygame.draw.rect(pantalla, col_bg,    rect, border_radius=4)
    pygame.draw.rect(pantalla, VERDE_BIT, rect, 1, border_radius=4)
    cx,cy = rect.centerx, rect.centery; s=tam//5; g=tam//5
    if not modo_fs:
        for dx,dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            ox,oy = cx+dx*g, cy+dy*g
            pygame.draw.line(pantalla,VERDE_BIT,(ox,oy),(ox+dx*s,oy),2)
            pygame.draw.line(pantalla,VERDE_BIT,(ox,oy),(ox,oy+dy*s),2)
    else:
        for dx,dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            ox,oy = cx+dx*(g+s), cy+dy*(g+s)
            pygame.draw.line(pantalla,VERDE_BIT,(ox,oy),(ox-dx*s,oy),2)
            pygame.draw.line(pantalla,VERDE_BIT,(ox,oy),(ox,oy-dy*s),2)


def dibujar_hud(juego, t):
    pygame.draw.rect(pantalla, GRIS_OSCURO, (0,0,ANCHO,ALTO_HUD))
    pygame.draw.line(pantalla, VERDE_BIT, (0,ALTO_HUD-1),(ANCHO,ALTO_HUD-1),2)
    cfg = NIVELES[juego.nivel_idx]
    pantalla.blit(fuente.render(f"SECTOR {juego.nivel_idx+1}: {cfg['nombre']}", True, VERDE_BIT), (10,6))
    escudo_str = " [ESCUDO]" if juego.tiene_escudo else ""
    vidas_str  = "■"*juego.vidas + "□"*(VIDAS_INICIALES-juego.vidas)
    col_v = DORADO if juego.tiene_escudo else ROJO_VIRUS
    pantalla.blit(fuente.render(f"VIDAS: {vidas_str}{escudo_str}", True, col_v), (10,ALTO_HUD//2+2))
    t_pts = fuente.render(f"PTS: {juego.puntos:06d}", True, AMARILLO_BOMBA)
    pantalla.blit(t_pts, (ANCHO//2-t_pts.get_width()//2, 6))
    num_e = len(juego.enemigos)
    if num_e>0:             msg,col = f"VIRUS: {num_e}  ELIMINALOS!", ROJO_VIRUS
    elif juego.puerta_vis:  msg,col = ">>> ENCUENTRA LA SALIDA [EXIT] <<<", AZUL_PUERTA
    elif cfg["num_enemigos"]==0: msg,col = "DESTRUYE BLOQUES PARA HALLAR LA SALIDA", CYAN
    else:                   msg,col = "DESTRUYE BLOQUES PARA HALLAR LA SALIDA", AZUL_PUERTA
    t_c = fuente.render(msg, True, col)
    pantalla.blit(t_c, t_c.get_rect(center=(ANCHO//2, ALTO_HUD*3//4)))
    px = ANCHO - max(24,ALTO_HUD-10) - 14
    inds = [(f"BOMBA x{juego.max_bombas}", AMARILLO_BOMBA), (f"RANGO:{juego.radio_exp}", NARANJA_EXP)]
    if juego.vel_jugador>0: inds.append((f"VEL+{juego.vel_jugador}", AZUL_ITEM))
    for idx,(txt,col) in enumerate(reversed(inds)):
        s=fuente.render(txt,True,col); pantalla.blit(s,(px-s.get_width(),6+idx*18))
    dibujar_btn_fullscreen()
    if juego.notif_item and t < juego.notif_t:
        s=fuente_m.render(juego.notif_item,True,DORADO); s.set_alpha(min(255,int(255*(juego.notif_t-t)/800)))
        pantalla.blit(s, s.get_rect(center=(ANCHO//2, ALTO_HUD+TAMANO_BLOQUE*2)))


def dibujar_mapa(juego):
    tb = TB_ACT
    for y,fila in enumerate(juego.mapa):
        for x,celda in enumerate(fila):
            rx=x*tb; ry=y*tb+ALTO_HUD
            r=pygame.Rect(rx,ry,tb,tb)
            if celda==1:
                pygame.draw.rect(pantalla,GRIS_MURO,r)
                pygame.draw.rect(pantalla,GRIS_BORDE,r,1)
                ins=tb//7
                pygame.draw.rect(pantalla,(90,90,90),r.inflate(-ins*2,-ins*2),1)
            elif celda==2:
                pygame.draw.rect(pantalla,MARRON_BLOQUE,r,border_radius=4)
                ins=tb//9
                pygame.draw.rect(pantalla,(180,100,20),r.inflate(-ins*2,-ins*2),border_radius=3)
                t=fuente.render("DAT",True,(200,140,80)); pantalla.blit(t,t.get_rect(center=r.center))
            elif celda==3:
                pygame.draw.rect(pantalla,AZUL_PUERTA,r,border_radius=4)
                pygame.draw.rect(pantalla,CYAN,r.inflate(-4,-4),2,border_radius=4)
                t=fuente.render("EXIT",True,BLANCO); pantalla.blit(t,t.get_rect(center=r.center))
    for (ix,iy),tipo in juego.items_visibles.items():
        cfg_i=ITEMS_CONFIG[tipo]; rx=ix*tb; ry=iy*tb+ALTO_HUD
        r=pygame.Rect(rx,ry,tb,tb); pad=tb//6; ri=r.inflate(-pad*2,-pad*2)
        pygame.draw.rect(pantalla,NEGRO,ri,border_radius=4)
        pygame.draw.rect(pantalla,cfg_i["color"],ri,2,border_radius=4)
        t=fuente.render(cfg_i["simbolo"],True,cfg_i["color"]); pantalla.blit(t,t.get_rect(center=r.center))


def _dibujar_pixel_art(grid, colores, ox, oy, ps):
    for gy,fila in enumerate(grid):
        for gx,v in enumerate(fila):
            if v!=0: pantalla.fill(colores[v],(ox+gx*ps, oy+gy*ps, ps, ps))


def _dibujar_copia(gx, gy, vidas, tb=None):
    if tb is None: tb=TB_ACT
    ps=max(2,(tb-6)//10); aw=ps*8; ah=ps*10
    ox=gx*tb+(tb-aw)//2; oy=gy*tb+ALTO_HUD+(tb-ah)//2
    if   vidas==3: col_c=(50,200,50);    col_v=CYAN;          col_b=(20,120,20)
    elif vidas==2: col_c=AMARILLO_BOMBA; col_v=(255,140,0);   col_b=(180,140,0)
    else:          col_c=ROJO_VIRUS;     col_v=(255,80,80);   col_b=(150,20,20)
    grid=[[0,0,0,1,1,0,0,0],[0,0,1,1,1,1,0,0],[0,1,2,2,2,2,1,0],[0,1,3,2,2,3,1,0],
          [0,1,2,2,2,2,1,0],[0,0,1,1,1,1,0,0],[0,1,1,1,1,1,1,0],[0,1,4,1,1,4,1,0],
          [0,0,1,0,0,1,0,0],[0,1,1,0,0,1,1,0]]
    _dibujar_pixel_art(grid,{1:col_c,2:(220,220,220),3:col_v,4:col_b},ox,oy,ps)
    for i in range(vidas):
        pygame.draw.circle(pantalla,col_c,(ox+aw//2-(vidas-1)*4+i*8, oy-5),3)


def _dibujar_jugador(gx, gy, tiene_escudo, t, tb=None):
    if tb is None: tb=TB_ACT
    ps=max(2,(tb-6)//10); aw=ps*8; ah=ps*10
    ox=gx*tb+(tb-aw)//2; oy=gy*tb+ALTO_HUD+(tb-ah)//2
    col_c=DORADO if tiene_escudo else VERDE_BIT
    col_p=(255,240,180) if tiene_escudo else (180,255,160)
    col_b=(180,140,0) if tiene_escudo else VERDE_OSCURO
    grid=[[0,0,0,1,1,0,0,0],[0,0,1,1,1,1,0,0],[0,1,2,2,2,2,1,0],[0,1,3,2,2,3,1,0],
          [0,1,2,2,2,2,1,0],[0,0,1,1,1,1,0,0],[0,1,1,1,1,1,1,0],[0,1,4,1,1,4,1,0],
          [0,0,1,0,0,1,0,0],[0,1,1,0,0,1,1,0]]
    _dibujar_pixel_art(grid,{1:col_c,2:col_p,3:CYAN,4:col_b},ox,oy,ps)
    if tiene_escudo and (t//200)%2==0:
        pygame.draw.rect(pantalla,BLANCO,(ox-1,oy-1,aw+2,ah+2),1)


def _dibujar_enemigo(gx, gy, tb=None):
    if tb is None: tb=TB_ACT
    ps=max(2,(tb-6)//9); aw=ps*8; ah=ps*9
    ox=gx*tb+(tb-aw)//2; oy=gy*tb+ALTO_HUD+(tb-ah)//2
    grid=[[0,0,1,1,1,1,0,0],[0,1,1,1,1,1,1,0],[1,1,2,1,1,2,1,1],[1,1,3,1,1,3,1,1],
          [1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1],[1,0,1,0,0,1,0,1],[1,0,1,0,0,1,0,1]]
    _dibujar_pixel_art(grid,{1:ROJO_VIRUS,2:BLANCO,3:NEGRO},ox,oy,ps)


def dibujar_juego(juego, t):
    tb = TB_ACT
    rb = max(tb//4, 8)   # radio bomba proporcional
    dibujar_mapa(juego)
    for ex,ey,_ in juego.explosiones:
        pad=tb//14
        r=pygame.Rect(ex*tb+pad,ey*tb+pad+ALTO_HUD,tb-pad*2,tb-pad*2)
        pygame.draw.rect(pantalla,NARANJA_EXP,r,border_radius=3)
        inn=tb//5; pygame.draw.rect(pantalla,AMARILLO_BOMBA,r.inflate(-inn,-inn),border_radius=2)
    for b in juego.bombas:
        cx=b.x*tb+tb//2; cy=b.y*tb+tb//2+ALTO_HUD
        restante=max(0,b.tiempo_det-t); vis=True
        if restante<1000: vis=(t//100)%2==0
        if vis:
            pygame.draw.circle(pantalla,AMARILLO_BOMBA,(cx,cy),rb)
            pygame.draw.circle(pantalla,NEGRO,(cx,cy),rb//2)
            pygame.draw.circle(pantalla,ROJO_VIRUS,(cx-rb//4,cy-rb//4),max(2,rb//4))
        bw=int(tb*restante/TIEMPO_BOMBA_MS); by=b.y*tb+tb-(tb//10)+ALTO_HUD; bh=max(3,tb//14)
        pygame.draw.rect(pantalla,GRIS_OSCURO,(b.x*tb,by,tb,bh))
        col_b=VERDE_BIT if restante>1500 else (AMARILLO_BOMBA if restante>800 else ROJO_VIRUS)
        pygame.draw.rect(pantalla,col_b,(b.x*tb,by,bw,bh))
    for b in juego.bombas_enemigas:
        cx=b.x*tb+tb//2; cy=b.y*tb+tb//2+ALTO_HUD
        restante=max(0,b.tiempo_det-t); vis=True
        if restante<1000: vis=(t//100)%2==0
        if vis:
            pygame.draw.circle(pantalla,MORADO,(cx,cy),rb)
            pygame.draw.circle(pantalla,NEGRO,(cx,cy),rb//2)
            pygame.draw.circle(pantalla,(200,100,255),(cx-rb//4,cy-rb//4),max(2,rb//4))
        bw=int(tb*restante/TIEMPO_BOMBA_MS); by=b.y*tb+tb-(tb//10)+ALTO_HUD; bh=max(3,tb//14)
        pygame.draw.rect(pantalla,GRIS_OSCURO,(b.x*tb,by,tb,bh))
        pygame.draw.rect(pantalla,MORADO,(b.x*tb,by,bw,bh))
    for e in juego.enemigos:
        if e.es_copia: _dibujar_copia(e.x,e.y,e.vidas,tb)
        else:          _dibujar_enemigo(e.x,e.y,tb)
    inv=t<juego.t_invinc; mostrar=not inv or (t//150)%2==0
    if mostrar and (juego.activo or juego.estado in ("nivel_claro","victoria")):
        _dibujar_jugador(juego.jugador_x,juego.jugador_y,juego.tiene_escudo,t,tb)


def dibujar_overlay(l1,l2,c1=VERDE_BIT,l3=""):
    ov=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA); ov.fill((0,0,0,200)); pantalla.blit(ov,(0,0))
    t1=fuente_g.render(l1,True,c1); t2=fuente_m.render(l2,True,BLANCO)
    pantalla.blit(t1,t1.get_rect(center=(ANCHO//2,ALTO//2-40)))
    pantalla.blit(t2,t2.get_rect(center=(ANCHO//2,ALTO//2+10)))
    if l3:
        t3=fuente.render(l3,True,CYAN); pantalla.blit(t3,t3.get_rect(center=(ANCHO//2,ALTO//2+50)))


def dibujar_pantalla_fin(juego, t, es_victoria):
    ov=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA); ov.fill((0,0,0,210)); pantalla.blit(ov,(0,0))
    cy=ALTO//2; color_titulo=CYAN if es_victoria else ROJO_VIRUS
    titulo="SISTEMA RESTAURADO" if es_victoria else juego.mensaje
    pulso=abs((t%1000)-500)/500; ec=int(200+55*pulso)
    col_a=(0,ec,ec) if es_victoria else (ec,50,50)
    t1=fuente_g.render(titulo,True,col_a); pantalla.blit(t1,t1.get_rect(center=(ANCHO//2,cy-130)))
    sub="Todos los sectores depurados" if es_victoria else "El sistema ha sido comprometido"
    ts=fuente.render(sub,True,BLANCO); pantalla.blit(ts,ts.get_rect(center=(ANCHO//2,cy-88)))
    aw=min(500,ANCHO-80); px=ANCHO//2-aw//2; py=cy-65; ph=90
    pygame.draw.rect(pantalla,(15,15,15),(px,py,aw,ph),border_radius=8)
    pygame.draw.rect(pantalla,color_titulo,(px,py,aw,ph),1,border_radius=8)
    tl=fuente.render("PUNTUACION FINAL",True,color_titulo); pantalla.blit(tl,tl.get_rect(center=(ANCHO//2,py+22)))
    tv=fuente_g.render(f"{juego.puntos:06d}",True,AMARILLO_BOMBA); pantalla.blit(tv,tv.get_rect(center=(ANCHO//2,py+58)))
    sy=py+ph+16
    stats=[(f"Nivel alcanzado: Sector {juego.nivel_idx+1} de {len(NIVELES)}",VERDE_BIT),
           (f"Vidas restantes: {'■'*juego.vidas+'□'*(VIDAS_INICIALES-juego.vidas)}",ROJO_VIRUS),
           (f"Power-ups: Bombas x{juego.max_bombas}  Rango {juego.radio_exp}  Vel+{juego.vel_jugador}",AZUL_ITEM)]
    for txt,col in stats:
        s=fuente.render(txt,True,col); pantalla.blit(s,s.get_rect(center=(ANCHO//2,sy))); sy+=26
    pygame.draw.line(pantalla,(60,60,60),(px,sy+14),(px+aw,sy+14),1); sy+=28
    tr=fuente.render("MEJORES PUNTAJES DE LA SESION",True,AMARILLO_BOMBA); pantalla.blit(tr,tr.get_rect(center=(ANCHO//2,sy))); sy+=28
    for i,pts in enumerate(ranking_sesion[:5]):
        es_act=(pts==juego.puntos and i==0)
        txt_r=fuente.render(f"  {i+1}.  {pts:06d}{'  << TU' if es_act else ''}",True,AMARILLO_BOMBA if es_act else BLANCO)
        pantalla.blit(txt_r,txt_r.get_rect(center=(ANCHO//2,sy))); sy+=24
    if not ranking_sesion:
        s=fuente.render("(sin partidas registradas)",True,(80,80,80)); pantalla.blit(s,s.get_rect(center=(ANCHO//2,sy)))
    if (t//500)%2==0:
        s=fuente_m.render("Presiona R para volver al menu",True,CYAN); pantalla.blit(s,s.get_rect(center=(ANCHO//2,ALTO-45)))


def dibujar_debug():
    fps=reloj.get_fps(); ms=reloj.get_time()
    try:
        import psutil, os as _os
        mem=psutil.Process(_os.getpid()).memory_info().rss/1024/1024
    except: mem=0.0
    nv=juego.nivel_idx+1 if juego else 0
    lineas=[f"FPS : {fps:.1f}", f"MS  : {ms} ms/frame", f"RAM : {mem:.1f} MB", f"NVL : {nv}"]
    pad=8; lh=20; aw=130; ah=pad*2+lh*len(lineas)
    pygame.draw.rect(pantalla,(0,0,0),(4,4,aw,ah),border_radius=4)
    pygame.draw.rect(pantalla,VERDE_BIT,(4,4,aw,ah),1,border_radius=4)
    for i,txt in enumerate(lineas):
        s=fuente.render(txt,True,VERDE_BIT); pantalla.blit(s,(4+pad,4+pad+i*lh))


PAUSA_OPCIONES=["CONTINUAR","REINICIAR NIVEL","VOLVER AL MENU","SALIR"]
pausa_sel=0

def dibujar_pausa():
    ov=pygame.Surface((ANCHO,ALTO),pygame.SRCALPHA); ov.fill((0,0,0,180)); pantalla.blit(ov,(0,0))
    t1=fuente_g.render("PAUSA",True,AMARILLO_BOMBA); pantalla.blit(t1,t1.get_rect(center=(ANCHO//2,ALTO//2-120)))
    pygame.draw.line(pantalla,VERDE_OSCURO,(ANCHO//2-100,ALTO//2-88),(ANCHO//2+100,ALTO//2-88),1)
    for i,op in enumerate(PAUSA_OPCIONES):
        sel=i==pausa_sel
        col_t=NEGRO if sel else BLANCO; bg=VERDE_BIT if sel else (40,40,40)
        s=fuente_m.render(op,True,col_t); rw=s.get_width()+32; rh=s.get_height()+12
        rx=ANCHO//2-rw//2; ry=ALTO//2-60+i*52
        pygame.draw.rect(pantalla,bg,(rx,ry,rw,rh),border_radius=6)
        pygame.draw.rect(pantalla,VERDE_BIT,(rx,ry,rw,rh),1,border_radius=6)
        pantalla.blit(s,(rx+16,ry+6))
    hint=fuente.render("Flechas Navegar  |  ENTER Confirmar  |  ESC Continuar",True,(80,80,80))
    pantalla.blit(hint,hint.get_rect(center=(ANCHO//2,ALTO-30)))


# ─── Menú ─────────────────────────────────────────────────────────────────────
opcion_menu=0
nivel_inicio=0   # nivel seleccionado para iniciar directamente

def dibujar_menu(t):
    global opcion_menu, nivel_inicio
    pantalla.fill(NEGRO)
    off=(t//40)%TAMANO_BLOQUE
    for x in range(-TAMANO_BLOQUE,ANCHO+TAMANO_BLOQUE,TAMANO_BLOQUE):
        pygame.draw.line(pantalla,(0,35,0),(x+off,0),(x+off,ALTO),1)
    for y in range(-TAMANO_BLOQUE,ALTO+TAMANO_BLOQUE,TAMANO_BLOQUE):
        pygame.draw.line(pantalla,(0,35,0),(0,y+off),(ANCHO,y+off),1)
    tit=fuente_t.render("DATA BLASTER",True,NEGRO); pantalla.blit(tit,tit.get_rect(center=(ANCHO//2+3,100)))
    tit=fuente_t.render("DATA BLASTER",True,VERDE_BIT); pantalla.blit(tit,tit.get_rect(center=(ANCHO//2,97)))
    sub=fuente_m.render("- Purga el sistema. Elimina el malware. -",True,CYAN)
    pantalla.blit(sub,sub.get_rect(center=(ANCHO//2,150)))
    pygame.draw.line(pantalla,VERDE_OSCURO,(60,172),(ANCHO-60,172),1)

    # ── Selector de nivel de inicio ──────────────────────────────────────────
    y_base=182
    lbl=fuente_m.render("INICIAR DESDE NIVEL",True,AMARILLO_BOMBA)
    pantalla.blit(lbl,lbl.get_rect(center=(ANCHO//2,y_base))); y_base+=36
    nombres_nv=["1 TUTORIAL","2 INFECCION","3 DEPURACION","4 BOSS"]
    total_w = len(nombres_nv)*130 + (len(nombres_nv)-1)*10
    sx = ANCHO//2 - total_w//2
    for i,nm in enumerate(nombres_nv):
        sel=i==nivel_inicio
        cf=VERDE_BIT if sel else (40,40,40); ct=NEGRO if sel else BLANCO
        s=fuente.render(nm,True,ct); rw=130; rh=34
        rx=sx+i*140; ry=y_base
        pygame.draw.rect(pantalla,cf,(rx,ry,rw,rh),border_radius=6)
        pygame.draw.rect(pantalla,VERDE_BIT,(rx,ry,rw,rh),1,border_radius=6)
        pantalla.blit(s,(rx+rw//2-s.get_width()//2,ry+7))
    y_base+=50

    # ── Modo pantalla ────────────────────────────────────────────────────────
    pygame.draw.line(pantalla,VERDE_OSCURO,(60,y_base),(ANCHO-60,y_base),1); y_base+=14
    modo_lbl=fuente_m.render("MODO DE PANTALLA",True,AMARILLO_BOMBA)
    pantalla.blit(modo_lbl,modo_lbl.get_rect(center=(ANCHO//2,y_base))); y_base+=34
    for i,op in enumerate(["  VENTANA  ","  PANTALLA COMPLETA  "]):
        sel=i==opcion_menu
        cf=VERDE_BIT if sel else GRIS_OSCURO; ct=NEGRO if sel else GRIS_BORDE
        s=fuente_m.render(op,True,ct); rw=s.get_width()+24; rh=s.get_height()+10
        rx=ANCHO//2-rw//2+(i)*220-110; ry=y_base
        pygame.draw.rect(pantalla,cf,(rx,ry,rw,rh),border_radius=6)
        pygame.draw.rect(pantalla,VERDE_BIT,(rx,ry,rw,rh),1 if not sel else 0,border_radius=6)
        pantalla.blit(s,(rx+12,ry+5))
    y_base+=48

    # ── Controles ────────────────────────────────────────────────────────────
    pygame.draw.line(pantalla,VERDE_OSCURO,(60,y_base),(ANCHO-60,y_base),1); y_base+=14
    controles=[
        ("CONTROLES",VERDE_BIT),
        ("Flechas o WASD Mover  |  ESPACIO Bomba  |  ESC Pausa  |  T Debug  |  F11 Fullscreen",BLANCO),
        ("+B=bombas  +R=rango  +V=velocidad  ES=escudo   (items ocultos en bloques)",AMARILLO_BOMBA),
    ]
    for txt,col in controles:
        s=fuente.render(txt,True,col); pantalla.blit(s,s.get_rect(center=(ANCHO//2,y_base))); y_base+=24

    if (t//500)%2==0:
        s=fuente_m.render(">>> PRESIONA ENTER PARA INICIAR <<<",True,VERDE_BIT)
        pantalla.blit(s,s.get_rect(center=(ANCHO//2,ALTO-48)))
    s=fuente.render("Lenny Valer  |  Videojuegos y Aplicaciones Moviles  |  2026",True,(60,60,60))
    pantalla.blit(s,s.get_rect(center=(ANCHO//2,ALTO-16)))
    dibujar_btn_fullscreen(); presentar()

# ─── Bucle principal ──────────────────────────────────────────────────────────
estado_app="menu"; juego=None; opcion_menu=0

import os as _os
_mp3=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),"mysterious_sewer_overture.mp3")
if not _os.path.exists(_mp3): _mp3=_os.path.join(_os.getcwd(),"mysterious_sewer_overture.mp3")
if _os.path.exists(_mp3):
    try:
        if not pygame.mixer.get_init(): pygame.mixer.init(frequency=44100,size=-16,channels=2,buffer=4096)
        pygame.mixer.music.load(_mp3); pygame.mixer.music.set_volume(0.4); pygame.mixer.music.play(-1)
    except Exception as e: print(f"[MUSICA] Error: {e}")

while True:
    t=pygame.time.get_ticks()
    for ev in pygame.event.get():
        if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            if BTN_FS_RECT.collidepoint(mouse_a_juego(ev.pos)): toggle_fullscreen()
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_F11: toggle_fullscreen()
            elif estado_app=="menu":
                if ev.key==pygame.K_LEFT:
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        opcion_menu=1-opcion_menu
                    else:
                        nivel_inicio=max(0,nivel_inicio-1)
                elif ev.key==pygame.K_RIGHT:
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        opcion_menu=1-opcion_menu
                    else:
                        nivel_inicio=min(len(NIVELES)-1,nivel_inicio+1)
                elif ev.key==pygame.K_TAB:
                    opcion_menu=1-opcion_menu
                elif ev.key==pygame.K_RETURN:
                    if (opcion_menu==1)!=modo_fs: toggle_fullscreen()
                    juego=Juego()
                    juego.nivel_idx=nivel_inicio
                    # Si empieza en nivel 4, 1 vida; si no, vidas normales
                    juego.vidas = 1 if nivel_inicio==3 else VIDAS_INICIALES
                    juego._cargar_nivel()
                    estado_app="jugando"
            elif estado_app=="pausa":
                if ev.key==pygame.K_ESCAPE: estado_app="jugando"
                elif ev.key==pygame.K_UP:   pausa_sel=(pausa_sel-1)%len(PAUSA_OPCIONES)
                elif ev.key==pygame.K_DOWN: pausa_sel=(pausa_sel+1)%len(PAUSA_OPCIONES)
                elif ev.key==pygame.K_RETURN:
                    if   pausa_sel==0: estado_app="jugando"
                    elif pausa_sel==1: juego._cargar_nivel(); estado_app="jugando"
                    elif pausa_sel==2:
                        if modo_fs: toggle_fullscreen()
                        estado_app="menu"
                    elif pausa_sel==3: pygame.quit(); sys.exit()
            elif estado_app=="jugando":
                if ev.key==pygame.K_ESCAPE and juego.estado=="jugando":
                    estado_app="pausa"; pausa_sel=0
                elif ev.key==pygame.K_t: debug_activo=not debug_activo
                elif ev.key==pygame.K_UP    or ev.key==pygame.K_w: juego.mover(0,-1)
                elif ev.key==pygame.K_DOWN  or ev.key==pygame.K_s: juego.mover(0, 1)
                elif ev.key==pygame.K_LEFT  or ev.key==pygame.K_a: juego.mover(-1,0)
                elif ev.key==pygame.K_RIGHT or ev.key==pygame.K_d: juego.mover(1,0)
                elif ev.key==pygame.K_SPACE: juego.poner_bomba()
                elif ev.key==pygame.K_RETURN and juego.estado=="nivel_claro": juego.siguiente_nivel()
                elif ev.key==pygame.K_r and juego.estado in ("game_over","victoria"):
                    if modo_fs: toggle_fullscreen()
                    estado_app="menu"

    if estado_app=="jugando" and juego and juego.estado=="jugando":
        teclas=pygame.key.get_pressed()
        if   teclas[pygame.K_UP]    or teclas[pygame.K_w]: juego.mover(0,-1)
        elif teclas[pygame.K_DOWN]  or teclas[pygame.K_s]: juego.mover(0, 1)
        elif teclas[pygame.K_LEFT]  or teclas[pygame.K_a]: juego.mover(-1,0)
        elif teclas[pygame.K_RIGHT] or teclas[pygame.K_d]: juego.mover(1,0)

    if estado_app=="menu": dibujar_menu(t); continue

    if estado_app in ("jugando","pausa"):
        if estado_app=="jugando": juego.update(t)
        pantalla.fill(NEGRO)
        dibujar_hud(juego,t)
        dibujar_juego(juego,t)
        if juego.estado=="nivel_claro":
            dibujar_overlay("SECTOR LIMPIO",f"Puntuacion: {juego.puntos:06d}",VERDE_BIT,"Presiona ENTER para continuar")
        elif juego.estado=="game_over":
            if not getattr(juego,'_pr',False): registrar_puntaje(juego.puntos); juego._pr=True
            dibujar_pantalla_fin(juego,t,False)
        elif juego.estado=="victoria":
            if not getattr(juego,'_pr',False): registrar_puntaje(juego.puntos); juego._pr=True
            dibujar_pantalla_fin(juego,t,True)
        if estado_app=="pausa": dibujar_pausa()
        if debug_activo: dibujar_debug()

    presentar()
    reloj.tick(60)