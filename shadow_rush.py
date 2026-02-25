import pygame
import random
import json
import os
from datetime import date, datetime

# ── Inicialización ──────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

W, H = 480, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Shadow Rush")
clock = pygame.time.Clock()
FPS = 60

# ── Colores ─────────────────────────────────────────────────────────────────
BLACK   = (0,   0,   0)
WHITE   = (255, 255, 255)
GRAY    = (80,  80,  80)
DGRAY   = (40,  40,  40)
RED     = (220, 50,  50)
ORANGE  = (255, 160, 0)
YELLOW  = (255, 220, 0)
GREEN   = (50,  200, 80)
BLUE    = (50,  120, 255)
PURPLE  = (150, 50,  220)
CYAN    = (0,   200, 220)
GOLD    = (255, 200, 0)
BROWN   = (140, 90,  40)

# ── Fuentes ─────────────────────────────────────────────────────────────────
font_big   = pygame.font.SysFont("monospace", 48, bold=True)
font_med   = pygame.font.SysFont("monospace", 28, bold=True)
font_small = pygame.font.SysFont("monospace", 18)
font_tiny  = pygame.font.SysFont("monospace", 14)

# ── Datos persistentes ──────────────────────────────────────────────────────
SAVE_FILE = "shadow_rush_save.json"

def load_save():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE) as f:
            return json.load(f)
    return {
        "coins": 0,
        "best_endless": 0,
        "current_level": 1,
        "last_login": "",
        "streak": 0,
        "chest_available": False,
        "chest_collected": False,
        "level_done_today": False,
        "skin": 0,
        "owned_skins": [0],
    }

def save_game(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)

# ── Skins (colores de personaje) ─────────────────────────────────────────────
SKINS = [
    {"name": "Shadow",  "color": BLUE,   "price": 0},
    {"name": "Lava",    "color": RED,     "price": 150},
    {"name": "Ghost",   "color": WHITE,   "price": 200},
    {"name": "Toxic",   "color": GREEN,   "price": 250},
    {"name": "Royal",   "color": PURPLE,  "price": 350},
]

# ═══════════════════════════════════════════════════════════════════════════
#  ENTIDADES
# ═══════════════════════════════════════════════════════════════════════════

class Player(pygame.sprite.Sprite):
    W, H = 36, 48
    JUMP_V   = -15
    GRAVITY  = 0.7
    MAX_FALL = 18

    def __init__(self, x, y, skin_color=BLUE):
        super().__init__()
        self.color = skin_color
        self.image = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._draw()
        self.rect  = self.image.get_rect(midbottom=(x, y))
        self.vel_y = 0
        self.on_ground = False
        self.jumps_left = 2          # doble salto
        self.alive = True
        self.invincible = 0          # frames de invencibilidad

    def _draw(self):
        self.image.fill((0,0,0,0))
        # cuerpo
        pygame.draw.rect(self.image, self.color, (4, 10, 28, 34), border_radius=6)
        # cabeza
        pygame.draw.ellipse(self.image, self.color, (6, 0, 24, 22))
        # ojos
        pygame.draw.circle(self.image, WHITE, (14, 8), 4)
        pygame.draw.circle(self.image, WHITE, (22, 8), 4)
        pygame.draw.circle(self.image, BLACK, (15, 8), 2)
        pygame.draw.circle(self.image, BLACK, (23, 8), 2)

    def jump(self):
        if self.jumps_left > 0:
            self.vel_y = self.JUMP_V
            self.jumps_left -= 1

    def update(self, platforms):
        if self.invincible > 0:
            self.invincible -= 1

        self.vel_y = min(self.vel_y + self.GRAVITY, self.MAX_FALL)
        self.rect.y += self.vel_y

        self.on_ground = False
        for p in platforms:
            if (self.vel_y >= 0 and
                    self.rect.bottom >= p.rect.top and
                    self.rect.bottom <= p.rect.top + 16 and
                    self.rect.right > p.rect.left + 4 and
                    self.rect.left < p.rect.right - 4):
                self.rect.bottom = p.rect.top
                self.vel_y = 0
                self.on_ground = True
                self.jumps_left = 2

        if self.rect.top > H + 60:
            self.alive = False

    def draw(self, surf):
        if self.invincible % 6 < 3:
            surf.blit(self.image, self.rect)


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h=14, color=GRAY, speed=0):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        pygame.draw.rect(self.image, WHITE, (0,0,w,h), 1)
        self.rect  = self.image.get_rect(topleft=(x, y))
        self.speed = speed
        self.dir   = 1

    def update(self):
        if self.speed:
            self.rect.x += self.speed * self.dir
            if self.rect.right > W - 20 or self.rect.left < 20:
                self.dir *= -1


class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, y, kind="spike"):
        super().__init__()
        self.kind = kind
        if kind == "spike":
            self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
            pts = [(12,0),(24,24),(0,24)]
            pygame.draw.polygon(self.image, RED, pts)
        elif kind == "box":
            self.image = pygame.Surface((28, 28))
            self.image.fill(BROWN)
            pygame.draw.rect(self.image, ORANGE, (0,0,28,28), 2)
        elif kind == "saw":
            self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(self.image, GRAY, (15,15), 14)
            for i in range(8):
                angle = i * 45
                import math
                ex = int(15 + 15*math.cos(math.radians(angle)))
                ey = int(15 + 15*math.sin(math.radians(angle)))
                pygame.draw.circle(self.image, WHITE, (ex,ey), 3)
        self.rect = self.image.get_rect(topleft=(x, y))


class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(self.image, GOLD, (9,9), 9)
        pygame.draw.circle(self.image, YELLOW, (9,9), 6)
        self.rect = self.image.get_rect(center=(x, y))
        self.bob  = 0

    def update(self):
        self.bob = (self.bob + 0.1) % (2*3.14159)
        import math
        self.rect.y += int(math.sin(self.bob)*0.5)


class Star(pygame.sprite.Sprite):
    """Meta del nivel"""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        pts = []
        import math
        for i in range(10):
            r = 16 if i%2==0 else 7
            a = math.radians(i*36 - 90)
            pts.append((16+r*math.cos(a), 16+r*math.sin(a)))
        pygame.draw.polygon(self.image, YELLOW, pts)
        pygame.draw.polygon(self.image, GOLD, pts, 2)
        self.rect = self.image.get_rect(center=(x, y))

# ═══════════════════════════════════════════════════════════════════════════
#  GENERADOR DE NIVELES
# ═══════════════════════════════════════════════════════════════════════════

def build_level(level_num):
    """Devuelve (platforms, obstacles, coins, star, scroll_speed)"""
    platforms = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    coins     = pygame.sprite.Group()

    # Suelo inicial
    platforms.add(Platform(0, H-40, W, 40, DGRAY))

    # Parámetros escalonados
    plat_count   = 6 + level_num * 2
    obs_chance   = min(0.1 + level_num * 0.04, 0.55)
    moving_chance= min(0.1 + level_num * 0.03, 0.4)
    coin_chance  = 0.5
    scroll_speed = 1 + level_num * 0.3

    # Plataformas
    y = H - 140
    prev_x = W//2
    for i in range(plat_count):
        w   = random.randint(80, 160)
        x   = max(10, min(W-w-10, prev_x + random.randint(-100, 100)))
        spd = random.uniform(1,2)*random.choice([-1,1]) if random.random()<moving_chance else 0
        p   = Platform(x, y, w, speed=spd)
        platforms.add(p)

        # obstáculo sobre plataforma
        if random.random() < obs_chance:
            kind = random.choice(["spike","box","saw"])
            ox = x + random.randint(4, max(5, w-28))
            obstacles.add(Obstacle(ox, y - (24 if kind=="spike" else 28), kind))

        # monedas
        if random.random() < coin_chance:
            for _ in range(random.randint(1,3)):
                cx = x + random.randint(4, max(5,w-18))
                coins.add(Coin(cx, y - 40))

        prev_x = x
        y -= random.randint(80, 130)

    star = Star(prev_x + 40, y + 20)
    return platforms, obstacles, coins, star, scroll_speed

# ═══════════════════════════════════════════════════════════════════════════
#  ESCENAS
# ═══════════════════════════════════════════════════════════════════════════

def draw_bg(surf, scroll):
    surf.fill((10, 10, 25))
    # estrellas de fondo
    random.seed(42)
    for _ in range(60):
        sx = random.randint(0, W)
        sy = (random.randint(0, H*3) + scroll//3) % H
        r  = random.randint(1,2)
        pygame.draw.circle(surf, (200,200,255), (sx,sy), r)
    random.seed()

def draw_hud(surf, coins_collected, total_coins, score, lives=None):
    # monedas
    pygame.draw.circle(surf, GOLD, (20, 20), 10)
    pygame.draw.circle(surf, YELLOW, (20, 20), 7)
    txt = font_small.render(f"{coins_collected}/{total_coins}", True, WHITE)
    surf.blit(txt, (36, 12))
    # score
    stxt = font_small.render(f"Score:{score}", True, CYAN)
    surf.blit(stxt, (W//2 - stxt.get_width()//2, 8))
    if lives is not None:
        for i in range(lives):
            pygame.draw.circle(surf, RED, (W-20-i*22, 20), 8)


def run_level(save, level_num, skin_color):
    """Juega un nivel. Devuelve 'win'|'lose'|'quit'"""
    platforms, obstacles, coins_grp, star, scroll_speed = build_level(level_num)
    all_coins = len(coins_grp.sprites())

    cam_y  = 0
    scroll = 0
    player = Player(W//2, H-80, skin_color)
    coins_collected = 0
    score  = 0
    lives  = 3
    won    = False

    running = True
    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    player.jump()
            if event.type == pygame.MOUSEBUTTONDOWN:
                player.jump()

        # cámara suave
        target_cam = player.rect.centery - H//2
        cam_y += (target_cam - cam_y) * 0.08
        scroll += scroll_speed

        # mover todo según cámara
        offset = cam_y

        # actualizar
        plat_list = platforms.sprites()
        player.update(plat_list)
        coins_grp.update()
        for p in platforms:
            p.update()

        # colisión monedas
        for c in list(coins_grp.sprites()):
            if player.rect.colliderect(c.rect.move(0, -int(offset))):
                coins_grp.remove(c)
                coins_collected += 1
                score += 10

        # colisión obstáculos
        if player.invincible == 0:
            for o in obstacles.sprites():
                if player.rect.colliderect(o.rect.move(0, -int(offset))):
                    lives -= 1
                    player.invincible = 90
                    if lives <= 0:
                        player.alive = False
                    break

        # colisión estrella (meta)
        star_screen = star.rect.move(0, -int(offset))
        if player.rect.colliderect(star_screen):
            won = True
            running = False

        if not player.alive:
            running = False

        # dibujar
        draw_bg(screen, scroll)

        # plataformas
        for p in platforms:
            r = p.rect.move(0, -int(offset))
            screen.blit(p.image, r)
        # obstáculos
        for o in obstacles:
            r = o.rect.move(0, -int(offset))
            screen.blit(o.image, r)
        # monedas
        for c in coins_grp:
            r = c.rect.move(0, -int(offset))
            screen.blit(c.image, r)
        # estrella
        screen.blit(star.image, star_screen)

        # player (ya tiene offset en rect porque se mueve con cam)
        pr = player.rect.move(0, -int(offset))
        if player.invincible % 6 < 3:
            screen.blit(player.image, pr)

        draw_hud(screen, coins_collected, all_coins, score, lives)

        # nivel
        ltxt = font_tiny.render(f"Nivel {level_num}", True, GRAY)
        screen.blit(ltxt, (W - ltxt.get_width() - 8, 8))

        pygame.display.flip()

    # resultado
    save["coins"] += coins_collected
    if won:
        save["coins"] += level_num * 20
        return "win"
    return "lose"


def run_endless(save, skin_color):
    """Modo endless con scroll automático hacia arriba."""
    SCROLL_BASE = 2
    platforms   = pygame.sprite.Group()
    obstacles   = pygame.sprite.Group()
    coins_grp   = pygame.sprite.Group()

    # suelo
    platforms.add(Platform(0, H-40, W, 40, DGRAY))

    def spawn_row(y):
        w   = random.randint(70, 160)
        x   = random.randint(10, W-w-10)
        spd = random.uniform(1,2)*random.choice([-1,1]) if random.random()<0.3 else 0
        p   = Platform(x, y, w, speed=spd)
        platforms.add(p)
        if random.random() < 0.35:
            kind = random.choice(["spike","box","saw"])
            ox   = x + random.randint(4, max(5,w-28))
            obstacles.add(Obstacle(ox, y-(24 if kind=="spike" else 28), kind))
        if random.random() < 0.5:
            for _ in range(random.randint(1,2)):
                cx = x + random.randint(4, max(5,w-18))
                coins_grp.add(Coin(cx, y-40))

    next_y = H - 180
    for _ in range(14):
        spawn_row(next_y)
        next_y -= random.randint(90, 130)

    player = Player(W//2, H-80, skin_color)
    cam_y  = 0
    score  = 0
    coins_collected = 0
    scroll = 0
    speed  = SCROLL_BASE
    lives  = 3
    running = True

    while running:
        clock.tick(FPS)
        speed = SCROLL_BASE + score / 500

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    player.jump()
            if event.type == pygame.MOUSEBUTTONDOWN:
                player.jump()

        # scroll del mundo
        for p in platforms:
            p.rect.y += speed
            p.update()
        for o in obstacles:
            o.rect.y += speed
        for c in coins_grp:
            c.rect.y += speed
            c.update()

        score += 1
        scroll += speed

        # spawning
        top_y = min(p.rect.top for p in platforms) if platforms else H
        while top_y > -200:
            next_y = top_y - random.randint(90, 130)
            spawn_row(next_y)
            top_y = next_y

        # limpiar lo que salió por abajo
        for p in list(platforms.sprites()):
            if p.rect.top > H + 60:
                platforms.remove(p)
        for o in list(obstacles.sprites()):
            if o.rect.top > H + 60:
                obstacles.remove(o)
        for c in list(coins_grp.sprites()):
            if c.rect.top > H + 60:
                coins_grp.remove(c)

        plat_list = platforms.sprites()
        player.update(plat_list)

        # caída por abajo
        if player.rect.top > H:
            lives -= 1
            player.invincible = 90
            if lives <= 0:
                player.alive = False
            else:
                player.rect.midbottom = (W//2, H-60)
                player.vel_y = 0

        # monedas
        for c in list(coins_grp.sprites()):
            if player.rect.colliderect(c.rect):
                coins_grp.remove(c)
                coins_collected += 1

        # obstáculos
        if player.invincible == 0:
            for o in obstacles.sprites():
                if player.rect.colliderect(o.rect):
                    lives -= 1
                    player.invincible = 90
                    if lives <= 0:
                        player.alive = False
                    break

        if not player.alive:
            running = False

        draw_bg(screen, int(scroll))
        for p in platforms: screen.blit(p.image, p.rect)
        for o in obstacles: screen.blit(o.image, o.rect)
        for c in coins_grp: screen.blit(c.image, c.rect)
        if player.invincible % 6 < 3:
            screen.blit(player.image, player.rect)

        draw_hud(screen, coins_collected, "?", score, lives)
        etxt = font_tiny.render("♾ ENDLESS", True, CYAN)
        screen.blit(etxt, (W - etxt.get_width() - 8, 8))

        pygame.display.flip()

    save["coins"] += coins_collected
    if score > save.get("best_endless", 0):
        save["best_endless"] = score
    return score


# ─── Pantalla de resultado ───────────────────────────────────────────────────

def result_screen(win, coins_gained=0, score=0, new_record=False):
    alpha = 0
    surf  = pygame.Surface((W, H), pygame.SRCALPHA)
    timer = 180
    while timer > 0:
        timer -= 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return "menu"
        alpha = min(alpha+6, 200)
        surf.fill((0,0,0,alpha))
        screen.blit(surf, (0,0))

        if win:
            t = font_big.render("¡GANASTE!", True, YELLOW)
        else:
            t = font_big.render("PERDISTE", True, RED)
        screen.blit(t, t.get_rect(center=(W//2, H//2-80)))

        if coins_gained:
            c = font_med.render(f"+{coins_gained} monedas", True, GOLD)
            screen.blit(c, c.get_rect(center=(W//2, H//2-20)))
        if score:
            s = font_med.render(f"Score: {score}", True, CYAN)
            screen.blit(s, s.get_rect(center=(W//2, H//2+30)))
        if new_record:
            r = font_med.render("¡NUEVO RÉCORD!", True, ORANGE)
            screen.blit(r, r.get_rect(center=(W//2, H//2+80)))

        cont = font_small.render("Toca para continuar", True, GRAY)
        screen.blit(cont, cont.get_rect(center=(W//2, H//2+140)))
        pygame.display.flip()
        clock.tick(FPS)
    return "menu"


# ─── Pantalla de cofre ───────────────────────────────────────────────────────

def chest_screen(save):
    reward_type = random.choice(["coins","coins","coins","bonus"])
    reward = random.randint(50, 150) if reward_type=="coins" else 200
    save["coins"] += reward
    save["chest_collected"] = True

    done = False
    angle = 0
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                done = True

        screen.fill((10,10,25))
        # cofre animado
        angle = (angle+2)%360
        import math
        sc = 1 + 0.05*math.sin(math.radians(angle))
        cx, cy = W//2, H//2-60
        bw, bh = int(80*sc), int(60*sc)
        pygame.draw.rect(screen, BROWN, (cx-bw//2, cy-bh//2, bw, bh), border_radius=6)
        pygame.draw.rect(screen, GOLD,  (cx-bw//2, cy-bh//2, bw, bh), 3, border_radius=6)
        pygame.draw.rect(screen, ORANGE,(cx-20, cy-bh//2-12, 40, 20), border_radius=4)
        pygame.draw.circle(screen, GOLD, (cx, cy-bh//2-4), 6)

        t = font_big.render("¡COFRE!", True, GOLD)
        screen.blit(t, t.get_rect(center=(W//2, H//2+40)))
        r = font_med.render(f"+{reward} monedas", True, YELLOW)
        screen.blit(r, r.get_rect(center=(W//2, H//2+90)))
        c = font_small.render("Toca para continuar", True, GRAY)
        screen.blit(c, c.get_rect(center=(W//2, H//2+150)))
        pygame.display.flip()
        clock.tick(FPS)


# ─── Tienda de skins ─────────────────────────────────────────────────────────

def shop_screen(save):
    selected = save.get("skin", 0)
    running  = True
    msg      = ""
    msg_timer= 0

    while running:
        screen.fill((10,10,25))
        t = font_big.render("TIENDA", True, GOLD)
        screen.blit(t, t.get_rect(center=(W//2, 40)))

        coins_txt = font_med.render(f"Monedas: {save['coins']}", True, YELLOW)
        screen.blit(coins_txt, (20, 90))

        for i, skin in enumerate(SKINS):
            y   = 150 + i*90
            owned = i in save.get("owned_skins",[0])
            active= i == selected
            color = GOLD if active else (GREEN if owned else GRAY)
            pygame.draw.rect(screen, color, (20, y, W-40, 80), border_radius=8)
            pygame.draw.rect(screen, DGRAY, (22, y+2, W-44, 76), border_radius=6)

            # preview skin
            pygame.draw.ellipse(screen, skin["color"], (36, y+16, 40, 48))

            name_t = font_med.render(skin["name"], True, WHITE)
            screen.blit(name_t, (90, y+12))

            if owned:
                st = "EQUIPADO" if active else "Equipar"
                st_t = font_small.render(st, True, GREEN if active else CYAN)
            else:
                st_t = font_small.render(f"{skin['price']} monedas", True, ORANGE)
            screen.blit(st_t, (90, y+46))

            # área clickeable
            skin["rect"] = pygame.Rect(20, y, W-40, 80)

        back = font_small.render("ESC = Volver", True, GRAY)
        screen.blit(back, (20, H-30))

        if msg_timer > 0:
            mt = font_small.render(msg, True, YELLOW)
            screen.blit(mt, mt.get_rect(center=(W//2, H-60)))
            msg_timer -= 1

        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                for i, skin in enumerate(SKINS):
                    if "rect" in skin and skin["rect"].collidepoint(mx, my):
                        owned = i in save.get("owned_skins",[0])
                        if owned:
                            selected = i
                            save["skin"] = i
                            msg = f"¡{skin['name']} equipado!"
                            msg_timer = 90
                        else:
                            if save["coins"] >= skin["price"]:
                                save["coins"] -= skin["price"]
                                save.setdefault("owned_skins",[0]).append(i)
                                selected = i
                                save["skin"] = i
                                msg = f"¡Comprado!"
                                msg_timer = 90
                            else:
                                msg = "No tienes suficientes monedas"
                                msg_timer = 90
        save_game(save)


# ─── Menú principal ──────────────────────────────────────────────────────────

def menu(save):
    today = str(date.today())

    # Login diario
    if save["last_login"] != today:
        if save["last_login"] == str(date.fromordinal(date.today().toordinal()-1)):
            save["streak"] += 1
        else:
            save["streak"] = 1
        save["last_login"]        = today
        save["chest_available"]   = False
        save["chest_collected"]   = False
        save["level_done_today"]  = False
        save_game(save)

    BW, BH = 300, 54
    BX = W//2 - BW//2
    buttons = [
        {"label": f"Nivel {save['current_level']}",  "y": H//2 - 20,  "action": "level"},
        {"label": "♾ Modo Endless",                   "y": H//2 + 50,  "action": "endless"},
        {"label": "🎨 Tienda de Skins",               "y": H//2 + 120, "action": "shop"},
    ]
    if save["chest_available"] and not save["chest_collected"]:
        buttons.insert(0, {"label": "📦 ¡Cofre disponible!", "y": H//2 - 90, "action": "chest"})

    running = True
    anim = 0
    while running:
        anim += 1
        screen.fill((10,10,25))

        # título
        import math
        off = int(4*math.sin(anim*0.04))
        t1 = font_big.render("SHADOW", True, CYAN)
        t2 = font_big.render("RUSH",   True, BLUE)
        screen.blit(t1, t1.get_rect(center=(W//2-2, 70+off)))
        screen.blit(t2, t2.get_rect(center=(W//2+2, 115-off)))

        # info
        ci = font_small.render(f"Monedas: {save['coins']}", True, GOLD)
        screen.blit(ci, (20, 165))
        bi = font_small.render(f"Mejor Endless: {save['best_endless']}", True, CYAN)
        screen.blit(bi, (20, 185))
        si = font_small.render(f"Racha: {save['streak']} días 🔥", True, ORANGE)
        screen.blit(si, (20, 205))

        # botones
        mx, my = pygame.mouse.get_pos()
        for btn in buttons:
            r = pygame.Rect(BX, btn["y"], BW, BH)
            hover = r.collidepoint(mx, my)
            color = BLUE if btn["action"]!="chest" else ORANGE
            pygame.draw.rect(screen, color if hover else DGRAY, r, border_radius=10)
            pygame.draw.rect(screen, color, r, 2, border_radius=10)
            lt = font_small.render(btn["label"], True, WHITE)
            screen.blit(lt, lt.get_rect(center=r.center))
            btn["rect"] = r

        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_game(save)
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN:
                for btn in buttons:
                    if btn.get("rect") and btn["rect"].collidepoint(event.pos):
                        return btn["action"]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_game(save)
                    return "quit"


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def main():
    save = load_save()
    skin_color = SKINS[save.get("skin",0)]["color"]

    while True:
        action = menu(save)
        skin_color = SKINS[save.get("skin",0)]["color"]

        if action == "quit":
            break

        elif action == "level":
            prev_coins = save["coins"]
            result = run_level(save, save["current_level"], skin_color)
            if result == "quit":
                save_game(save)
                break
            gained = save["coins"] - prev_coins
            if result == "win":
                save["level_done_today"] = True
                save["chest_available"]  = True
                save["current_level"]   += 1
                save_game(save)
                result_screen(True, gained)
            else:
                save_game(save)
                result_screen(False)

        elif action == "endless":
            prev_best = save.get("best_endless",0)
            score = run_endless(save, skin_color)
            if score == "quit":
                save_game(save)
                break
            new_rec = score > prev_best
            save_game(save)
            result_screen(False, save["coins"]-save["coins"], score, new_rec)

        elif action == "chest":
            chest_screen(save)
            save_game(save)

        elif action == "shop":
            r = shop_screen(save)
            if r == "quit":
                break

    save_game(save)
    pygame.quit()

if __name__ == "__main__":
    main()
