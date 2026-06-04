# 💣 DATA BLASTER

> *Purga el sistema. Sobrevive a tus propias bombas.*

Juego de acción y laberintos en 2D con vista superior, inspirado en **Bomberman**.  
El jugador controla a **Bit-E**, un bot de limpieza lógica que debe purgar sectores infectados usando bombas de código — con el riesgo de eliminarse a sí mismo si no se posiciona correctamente.

**Curso:** Videojuegos y Aplicaciones Móviles  
**Autor:** Piero Lenny Valer Atahuaman  
**Universidad:** UNMSM — 2026

---

## 🎮 Características principales

- 4 niveles con dificultad progresiva (Tutorial → Infección → Depuración Crítica → Protocolo Espejo)
- Sistema de bombas temporizadas con explosión en cruz y reacción en cadena
- 4 power-ups coleccionables ocultos en bloques (+Bomba, +Rango, +Velocidad, Escudo)
- Nivel 4 boss con **Copias de Bit-E**: 3 vidas, cambian de color y colocan sus propias bombas
- Sprites pixel art estilo Bomberman dibujados en código (sin imágenes externas)
- Menú de pausa (ESC), panel de debug en tiempo real (T) y selector de nivel
- Música de fondo + 7 efectos de sonido procedurales
- Pantalla completa / ventana con escalado proporcional automático (F11 o botón en HUD)
- Ranking de puntajes de sesión

---

## 🛠️ Requisitos

### Python
Versión recomendada: **Python 3.10 o superior**

Verificá tu versión con:
```bash
python --version
```

### Dependencias
Solo se requiere **Pygame**:

```bash
pip install pygame
```

> El juego no usa imágenes externas ni assets adicionales. Todos los gráficos se generan por código.  
> La música requiere tener el archivo `mysterious_sewer_overture.mp3` en la misma carpeta que el `.py` (ver sección de archivos).

---

## 📁 Estructura del proyecto

```
Proyecto_videojuegos_2026_individual_Lenny/
│
├── data_blaster.py                   # Código principal del juego
├── mysterious_sewer_overture.mp3     # Música de fondo (requerida para audio)
└── README.md                         # Este archivo
```

> ⚠️ El archivo `.mp3` debe estar en la **misma carpeta** que `data_blaster.py` para que la música funcione. Si no está presente, el juego corre normalmente pero sin música.

---

## ▶️ Cómo ejecutar

### Opción 1 — Desde la terminal

```bash
# Clona el repositorio
git clone https://github.com/LennyValer1/Proyecto_videojuegos_2026_individual_Lenny.git

# Entra a la carpeta
cd Proyecto_videojuegos_2026_individual_Lenny

# Instala Pygame si no lo tenés
pip install pygame

# Ejecuta el juego
python data_blaster.py
```

### Opción 2 — Desde VS Code

1. Abre la carpeta del proyecto en VS Code
2. Asegurate de tener el intérprete de Python seleccionado (esquina inferior izquierda)
3. Abre `data_blaster.py`
4. Presiona `F5` o el botón ▶️ de Run

---

## ⌨️ Controles

| Tecla | Acción |
|-------|--------|
| `↑ ↓ ← →` o `W A S D` | Mover a Bit-E |
| `ESPACIO` | Colocar bomba de código |
| `ENTER` | Iniciar / avanzar al siguiente sector |
| `ESC` | Menú de pausa |
| `R` | Volver al menú principal |
| `T` | Activar/desactivar panel de debug (FPS · RAM · MS/frame) |
| `F11` | Alternar pantalla completa / ventana |

---

## 🗺️ Niveles

| # | Nombre | Enemigos | Vidas | Detalle |
|---|--------|----------|-------|---------|
| 1 | Tutorial | 0 | 3 | Aprende a colocar bombas. Sin enemigos. |
| 2 | Infección | 2 Virus | 3 | Primeros Gusanos de Red y bloques con ítems. |
| 3 | Depuración Crítica | 3 Virus | 3 | Enemigos rápidos, mapa denso, alta tensión. |
| 4 | Protocolo Espejo | 3 Copias | ⚠️ 1 | Boss final. Mapa grande (21×15). Copias con 3 vidas y bombas propias. |

**Condición de victoria por nivel:**  
Eliminar todos los enemigos → Destruir bloques para revelar la salida `[EXIT]` → Pisarla para avanzar.

---

## 🎁 Sistema de ítems

Los ítems aparecen al destruir bloques. Se recogen pisando la celda.

| Símbolo | Nombre | Efecto | Límite |
|---------|--------|--------|--------|
| `+B` | +Bomba | Aumenta bombas simultáneas | Máx 2 |
| `+R` | +Rango | Aumenta radio de explosión | Máx radio 3 |
| `+V` | +Velocidad | Movimiento más rápido | 2 niveles |
| `ES` | Escudo | Absorbe un golpe sin perder vida | 1 uso |

---

## 🔧 Detalles técnicos

- **Motor gráfico:** Pygame (SDL2)
- **Lenguaje:** Python 3
- **Resolución lógica:** 840 × 672 px (escalado automático a cualquier pantalla)
- **FPS objetivo:** 60
- **Sonidos:** Generados matemáticamente en código (onda cuadrada + ruido)
- **Sprites:** Pixel art dibujado con `Surface.fill()` — sin archivos de imagen
- **Mapa nivel 4:** 21 × 15 celdas (vs 15 × 11 en niveles 1-3)
- **IA enemigos:** Movimiento autónomo con detección de colisiones y evasión de bombas

---

## 📸 Capturas

> *Podés agregar capturas del juego aquí. En GitHub: arrastrá las imágenes al README o subílas a una carpeta `/screenshots`.*

---

## 📄 Licencia

Proyecto académico — Videojuegos y Aplicaciones Móviles · UNMSM · 2026  
Uso educativo exclusivo.
