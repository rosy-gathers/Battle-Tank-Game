# Battle Tanks — Full Game: Levels 1–3 + Final Boss (Level 4)
# PyOpenGL + GLUT
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, random

# ---------- Window / world ----------
WINDOW_W, WINDOW_H = 1000, 800
GRID_LENGTH = 600
# --- FIX: Single constant used everywhere to make bullets disappear at the arena walls ---
BULLET_WALL_LIMIT = GRID_LENGTH - 8.0

# ---------- Player / tank state ----------
tank_pos = [0.0, 0.0, 20.0]  # x, y, z (z = hull half-height)
tank_yaw = 0.0              # hull heading in degrees (0 -> +X)
barrel_rel = 0.0            # turret rotation RELATIVE to hull (degrees)
tank_velocity = 0.0
strafe_velocity = 0.0

# movement parameters (tweak as needed)
max_speed = 4.0
accel = 0.18
decel = 0.22
friction = 0.08
turn_speed = 2.6
strafe_speed = 3.0

# ---------- Camera ----------
camera_mode_first_person = False
cam_orbit_deg = 90.0
cam_distance = 420.0
cam_height = 180.0
fp_eye_height = 28.0  # eye height above turret
mouse_toggle_debounce = False

# ---------- Mode/Cheat ----------
level_index = 1
mode_name = "Level 1"
cheat_invincible = False
cheat_no_cooldown = False

# ---------- Projectiles (player) ----------
projectiles = []  # list of dicts {x,y,z,vx,vy,ttl}

# ---------- Input ----------
keys_down = set()

# ---------- Game flags / counters ----------
PLAYER_MAX_HITS = 10        # player can take this many hits before freeze
player_hits_taken = 0       # enemy bullets that hit player
game_over_freeze = False    # freeze updates on player death
game_win_freeze = False     # freeze on final victory
killed_by_laser = False     # special banner for laser kill
player_blocked = False      # true when surrounded (movement locked)

# ---------- Utilities ----------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def rad(deg):
    return deg * math.pi / 180.0

def deg(angle_rad):
    return angle_rad * 180.0 / math.pi

def ang_norm(a):
    """Normalize to [-180,180)."""
    a = (a + 180.0) % 360.0 - 180.0
    return a

def dist2(ax, ay, bx, by):
    dx, dy = bx-ax, by-ay
    return dx*dx + dy*dy

def point_segment_dist2(px, py, ax, ay, bx, by):
    """Squared distance from point P to segment AB."""
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx*vx + vy*vy
    if vv <= 1e-8:
        return dist2(px, py, ax, ay)
    t = (wx*vx + wy*vy) / vv
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t*vx, ay + t*vy
    return dist2(px, py, cx, cy)

# ---------- Simple box helper ----------
def draw_box(width, depth, height):
    """Centered box: width->+X, depth->+Y, height->+Z."""
    glPushMatrix()
    glScalef(width, depth, height)
    glutSolidCube(1.0)
    glPopMatrix()

# ---------- HUD text ----------
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, r=1, g=1, b=1):
    glColor3f(r, g, b)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_center_banner(text, r, g, b, font=GLUT_BITMAP_TIMES_ROMAN_24):
    # fake "bold" by drawing twice with tiny offset
    w = len(text) * 12
    x = WINDOW_W//2 - w//2
    y = WINDOW_H//2 + 20
    draw_text(x, y, text, font, r, g, b)
    draw_text(x+1, y+1, text, font, r, g, b)

# ---------- Drawing: tank + projectiles ----------
def draw_tank():
    """Translate->rotate hull; turret rotates relative to hull."""
    glPushMatrix()
    glTranslatef(tank_pos[0], tank_pos[1], tank_pos[2])
    glRotatef(tank_yaw, 0, 0, 1)

    # Hull
    glPushMatrix()
    glColor3f(0.15, 0.45, 0.75)
    draw_box(80.0, 50.0, 30.0)
    glPopMatrix()

    # Treads / lower plate
    glPushMatrix()
    glTranslatef(0.0, 0.0, -15.0)
    glColor3f(0.08, 0.08, 0.08)
    draw_box(90.0, 62.0, 6.0)
    glPopMatrix()

    # Turret (relative)
    glPushMatrix()
    glTranslatef(0.0, 0.0, 17.0)
    glRotatef(barrel_rel, 0, 0, 1)

    # turret base
    glPushMatrix()
    glColor3f(0.25, 0.25, 0.30)
    draw_box(30.0, 30.0, 12.0)
    glPopMatrix()

    # barrel (+X)
    barrel_length = 48.0
    barrel_height = 6.0
    barrel_depth = 6.0
    glPushMatrix()
    glTranslatef(barrel_length * 0.5 + 8.0, 0.0, 0.0)
    glColor3f(0.9, 0.85, 0.25)
    draw_box(barrel_length, barrel_depth, barrel_height)
    glPopMatrix()

    # muzzle
    glPushMatrix()
    glTranslatef(barrel_length + 8.0 + 4.0, 0.0, 0.0)
    glColor3f(0.4, 0.1, 0.1)
    glutSolidSphere(3.5, 12, 8)
    glPopMatrix()

    glPopMatrix()  # turret
    glPopMatrix()  # world

def draw_projectiles():
    glColor3f(1.0, 0.4, 0.2)
    for p in projectiles:
        glPushMatrix()
        glTranslatef(p["x"], p["y"], p["z"])
        bullet_size = p.get("size", 4.0)
        glutSolidSphere(bullet_size, 8, 8)
        glPopMatrix()

def draw_ground():
    glBegin(GL_QUADS)
    glColor3f(0.0, 0.4, 0.4)
    glVertex3f(-GRID_LENGTH,  GRID_LENGTH, 0)
    glVertex3f( GRID_LENGTH,  GRID_LENGTH, 0)
    glVertex3f( GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glEnd()

# ---------- HARD RESET ----------
def hard_reset():
    global tank_pos, tank_yaw, barrel_rel, tank_velocity, strafe_velocity
    global projectiles, enemies_basic, enemy_bullets_basic, _enemies_basic_spawned, basic_kills
    global miniboss1, mb1_bullets, miniboss2, mb2_bullets, mb2_spawned
    global miniboss3, mb3_bullets, mb3_spawned
    global final_boss, fb_bullets, fb_spawned, fb_laser_active
    global player_hits_taken, game_over_freeze, game_win_freeze, player_blocked, killed_by_laser
    global level_index, mode_name
    global level1_complete_banner_ms, level2_complete_banner_ms, final_boss_banner_ms

    tank_pos[:] = [0.0, 0.0, 20.0]
    tank_yaw = 0.0
    barrel_rel = 0.0
    tank_velocity = 0.0
    strafe_velocity = 0.0
    projectiles.clear()
    enemies_basic.clear()
    enemy_bullets_basic.clear()
    _enemies_basic_spawned = False
    basic_kills = 0
    miniboss1 = None
    mb1_bullets.clear()
    miniboss2 = None
    mb2_bullets.clear()
    mb2_spawned = False
    miniboss3 = None
    mb3_bullets.clear()
    mb3_spawned = False
    final_boss = None
    fb_bullets.clear()
    fb_spawned = False
    fb_laser_active = False
    player_hits_taken = 0
    game_over_freeze = False
    game_win_freeze = False
    killed_by_laser = False
    player_blocked = False
    level1_complete_banner_ms = 0
    level2_complete_banner_ms = 0
    final_boss_banner_ms = 0
    set_level(1)
    spawn_five_enemies()

# ---------- Input handlers ----------
def keyboardListener(key, x, y):
    global keys_down, cheat_invincible, cheat_no_cooldown, camera_mode_first_person, game_over_freeze, player_hits_taken, game_win_freeze
    k = key.decode("utf-8").lower()
    keys_down.add(k)
    if k == 'c':
        cheat_invincible = not cheat_invincible
        cheat_no_cooldown = cheat_invincible
        if cheat_invincible and (game_over_freeze or game_win_freeze):
            game_over_freeze = False
            game_win_freeze = False
            player_hits_taken = 0
    elif k == 'r':
        hard_reset()
    elif k == 't':
        camera_mode_first_person = not camera_mode_first_person
    elif k in ('1', '2', '3', '4'):
        set_level(int(k))

def keyboardUpListener(key, x, y):
    k = key.decode("utf-8").lower()
    if k in keys_down:
        keys_down.remove(k)

def specialKeyListener(key, x, y):
    global cam_orbit_deg, cam_height, cam_distance, fp_eye_height
    if key == GLUT_KEY_LEFT:
        cam_orbit_deg -= 3.0
    if key == GLUT_KEY_RIGHT:
        cam_orbit_deg += 3.0
    if key == GLUT_KEY_UP:
        if camera_mode_first_person:
            fp_eye_height = clamp(fp_eye_height + 2.0, 2.0, 60.0)
        else:
            cam_height = clamp(cam_height + 6.0, 30.0, 600.0)
            cam_distance = clamp(cam_distance - 6.0, 120.0, 1200.0)
    if key == GLUT_KEY_DOWN:
        if camera_mode_first_person:
            fp_eye_height = clamp(fp_eye_height - 2.0, 2.0, 60.0)
        else:
            cam_height = clamp(cam_height - 6.0, 30.0, 600.0)
            cam_distance = clamp(cam_distance + 6.0, 120.0, 1200.0)

def mouseListener(button, state, x, y):
    global mouse_toggle_debounce, camera_mode_first_person
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        attempt_fire()
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN and not mouse_toggle_debounce:
        camera_mode_first_person = not camera_mode_first_person
        mouse_toggle_debounce = True
    if state == GLUT_UP:
        mouse_toggle_debounce = False

# ---------- Game actions ----------
last_fire_time_ms = -99999
fire_cooldown_ms = 600

def attempt_fire():
    global last_fire_time_ms
    if game_over_freeze or game_win_freeze:
        return
    now = glutGet(GLUT_ELAPSED_TIME)
    
    current_cooldown = 800 if level_index == 2 else fire_cooldown_ms
    cd = 0 if cheat_no_cooldown else current_cooldown
    
    if now - last_fire_time_ms < cd:
        return
    last_fire_time_ms = now
    spawn_projectile()

def spawn_projectile():
    px = tank_pos[0] + math.cos(rad(tank_yaw)) * 12.0
    py = tank_pos[1] + math.sin(rad(tank_yaw)) * 12.0
    pz = tank_pos[2] + 20.0
    speed = 12.0
    base_angle = tank_yaw + barrel_rel
    bullet_size = 6.0 if level_index == 2 else 4.0

    if level_index == 3:
        player_spread_deg = 10.0
        spreads = [0.0, player_spread_deg, -player_spread_deg]
        for angle_offset in spreads:
            world_angle = base_angle + angle_offset
            vx = math.cos(rad(world_angle)) * speed
            vy = math.sin(rad(world_angle)) * speed
            projectiles.append(dict(
                x=px + vx * 0.08, y=py + vy * 0.08, z=pz, vx=vx, vy=vy, ttl=3500, size=bullet_size
            ))
    else:
        vx = math.cos(rad(base_angle)) * speed
        vy = math.sin(rad(base_angle)) * speed
        projectiles.append(dict(
            x=px + vx * 0.08, y=py + vy * 0.08, z=pz, vx=vx, vy=vy, ttl=3500, size=bullet_size
        ))


# ---------- Level control ----------
def set_level(idx):
    global level_index, mode_name
    level_index = clamp(idx, 1, 4)
    mode_name = f"Level {level_index}"

# ---------- Camera setup ----------
def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(90.0, WINDOW_W / float(WINDOW_H), 0.1, 4000.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    if camera_mode_first_person:
        world_angle_rad = rad(tank_yaw + barrel_rel)
        hull_angle_rad = rad(tank_yaw)
        camera_backward_offset = -15.0
        eye_x = tank_pos[0] + math.cos(hull_angle_rad) * camera_backward_offset
        eye_y = tank_pos[1] + math.sin(hull_angle_rad) * camera_backward_offset
        eye_z = tank_pos[2] + fp_eye_height
        look_distance = 200.0
        target_x = eye_x + math.cos(world_angle_rad) * look_distance
        target_y = eye_y + math.sin(world_angle_rad) * look_distance
        target_z = eye_z - 10.0
        gluLookAt(eye_x, eye_y, eye_z, target_x, target_y, target_z, 0, 0, 1)
    else:
        ex = tank_pos[0] + math.cos(rad(cam_orbit_deg)) * cam_distance
        ey = tank_pos[1] + math.sin(rad(cam_orbit_deg)) * cam_distance
        ez = tank_pos[2] + cam_height
        gluLookAt(ex, ey, ez, tank_pos[0], tank_pos[1], tank_pos[2] + 8.0, 0, 0, 1)

# ===================== BASIC ENEMIES (Level 1,2,3) =====================
enemies_basic = []
enemy_bullets_basic = []
_enemies_basic_spawned = False
basic_kills = 0
EN_HULL_W, EN_HULL_H, EN_HULL_D = 52.0, 20.0, 34.0
EN_TURRET_W, EN_TURRET_H, EN_TURRET_D = 19.0, 8.0, 19.0
EN_BARREL_L, EN_BARREL_H, EN_BARREL_D = 30.0, 4.0, 4.0
EN_TURRET_Z  = 11.0
EN_TREAD_Z   = -10.0
ENEMY_SPEED_SLOW = 1.0
ENEMY_SPEED_VERY_SLOW = 0.45
MIN_SEP = 46.0
EN_STANDOFF_R = 140.0
STANDOFF_DEADBAND = 8.0
CROWD_RADIUS = 150.0
EN_BULLET_SPEED = 7.0
EN_BULLET_TTL   = 4200
EN_FIRE_CD_MS   = 1800
EN_FIRE_CD_L3   = 1000
_en_fire_t_acc  = 0

def spawn_five_enemies():
    global _enemies_basic_spawned, basic_kills
    if _enemies_basic_spawned:
        return
    _enemies_basic_spawned = True
    basic_kills = 0
    s = GRID_LENGTH - 120
    spots = [(-s, 0.0), ( s, 0.0), (0.0, -s), (0.0,  s), (-0.7*s, 0.7*s)]
    for (ex, ey) in spots:
        enemies_basic.append(dict(x=ex, y=ey, z=20.0, yaw=0.0, speed=ENEMY_SPEED_SLOW, alive=True))

def spawn_seven_enemies_level2():
    global basic_kills
    enemies_basic.clear()
    enemy_bullets_basic.clear()
    basic_kills = 0
    ring_r = GRID_LENGTH - 140.0
    for i in range(7):
        ang = (2.0 * math.pi) * (i / 7.0)
        ex = math.cos(ang) * ring_r
        ey = math.sin(ang) * ring_r
        enemies_basic.append(dict(x=ex, y=ey, z=20.0, yaw=0.0, speed=ENEMY_SPEED_SLOW, alive=True))

def spawn_ten_enemies_level3():
    global basic_kills
    enemies_basic.clear()
    enemy_bullets_basic.clear()
    basic_kills = 0
    ring_r = GRID_LENGTH - 150.0
    for i in range(10):
        ang = (2.0 * math.pi) * (i / 10.0)
        ex = math.cos(ang) * ring_r
        ey = math.sin(ang) * ring_r
        enemies_basic.append(dict(x=ex, y=ey, z=20.0, yaw=0.0, speed=ENEMY_SPEED_VERY_SLOW, alive=True))

def _separate_enemies():
    n = len(enemies_basic)
    for i in range(n):
        ei = enemies_basic[i]
        if not ei["alive"]:
            continue
        for j in range(i+1, n):
            ej = enemies_basic[j]
            if not ej["alive"]:
                continue
            dx = ej["x"] - ei["x"]
            dy = ej["y"] - ei["y"]
            d2 = dx*dx + dy*dy
            if d2 <= 1e-6:
                push = MIN_SEP * 0.5
                ang = random.random() * 2.0 * math.pi
                ei["x"] -= math.cos(ang) * push
                ei["y"] -= math.sin(ang) * push
                ej["x"] += math.cos(ang) * push
                ej["y"] += math.sin(ang) * push
                continue
            d = math.sqrt(d2)
            if d < MIN_SEP:
                need = (MIN_SEP - d) * 0.5
                nx, ny = dx / d, dy / d
                ej["x"] += nx * need
                ej["y"] += ny * need
                ei["x"] -= nx * need
                ei["y"] -= ny * need

def _check_player_surrounded():
    global player_blocked
    if game_over_freeze or game_win_freeze:
        player_blocked = False
        return
    bins = [False, False, False, False]
    for e in enemies_basic:
        if not e["alive"]:
            continue
        if dist2(e["x"], e["y"], tank_pos[0], tank_pos[1]) <= CROWD_RADIUS * CROWD_RADIUS:
            ang = math.degrees(math.atan2(e["y"] - tank_pos[1], e["x"] - tank_pos[0]))
            if -45.0 <= ang < 45.0:
                bins[0] = True
            elif 45.0 <= ang < 135.0:
                bins[1] = True
            elif -135.0 < ang < -45.0:
                bins[2] = True
            else:
                bins[3] = True
    player_blocked = all(bins)

def update_enemies_basic(dt_ms):
    global _en_fire_t_acc, player_hits_taken, game_over_freeze, basic_kills
    for e in enemies_basic:
        if not e["alive"]:
            continue
        dx, dy = tank_pos[0] - e["x"], tank_pos[1] - e["y"]
        e["yaw"] = math.degrees(math.atan2(dy, dx))
        d = math.hypot(dx, dy)
        step = e["speed"] * (dt_ms / 16.0)
        if d > EN_STANDOFF_R + STANDOFF_DEADBAND:
            e["x"] += math.cos(rad(e["yaw"])) * step
            e["y"] += math.sin(rad(e["yaw"])) * step
        elif d < EN_STANDOFF_R - STANDOFF_DEADBAND:
            back = 0.45 * step
            e["x"] -= math.cos(rad(e["yaw"])) * back
            e["y"] -= math.sin(rad(e["yaw"])) * back
        br = GRID_LENGTH - 50
        e["x"] = clamp(e["x"], -br, br)
        e["y"] = clamp(e["y"], -br, br)
    _separate_enemies()
    cd_ms = EN_FIRE_CD_L3 if level_index == 3 else EN_FIRE_CD_MS
    _en_fire_t_acc += dt_ms
    if _en_fire_t_acc >= cd_ms and len(enemy_bullets_basic) == 0:
        _en_fire_t_acc = 0
        shooters = [e for e in enemies_basic if e["alive"]]
        if shooters:
            e = random.choice(shooters)
            yaw_r = rad(e["yaw"])
            muzzle_forward = EN_BARREL_L + 10.0
            bx = e["x"] + math.cos(yaw_r) * muzzle_forward
            by = e["y"] + math.sin(yaw_r) * muzzle_forward
            bz = e["z"] + EN_TURRET_Z
            enemy_bullets_basic.append(dict(x=bx, y=by, z=bz, vx=math.cos(yaw_r) * EN_BULLET_SPEED, vy=math.sin(rad(yaw_r)) * EN_BULLET_SPEED, ttl=EN_BULLET_TTL))
    rm = []
    for i, b in enumerate(enemy_bullets_basic):
        b["x"] += b["vx"] * (dt_ms / 16.0)
        b["y"] += b["vy"] * (dt_ms / 16.0)
        b["ttl"] -= dt_ms
        out = (abs(b["x"]) >= BULLET_WALL_LIMIT or abs(b["y"]) >= BULLET_WALL_LIMIT or b["ttl"] <= 0)
        if not out and not cheat_invincible:
            if dist2(b["x"], b["y"], tank_pos[0], tank_pos[1]) <= (10.0 + 4.0)**2:
                player_hits_taken += 1
                out = True
                if player_hits_taken >= PLAYER_MAX_HITS:
                    game_over_freeze = True
        if out:
            rm.append(i)
    for idx in reversed(rm):
        enemy_bullets_basic.pop(idx)
    rm_p = []
    for pi, p in enumerate(projectiles):
        hit = False
        for e in enemies_basic:
            if not e["alive"]:
                continue
            if dist2(p["x"], p["y"], e["x"], e["y"]) <= (EN_HULL_W*0.35 + 4.0)**2:
                e["alive"] = False
                basic_kills += 1
                hit = True
                break
        if hit:
            rm_p.append(pi)
    for idx in reversed(rm_p):
        projectiles.pop(idx)
    _check_player_surrounded()

def draw_enemies_basic():
    for e in enemies_basic:
        if not e["alive"]:
            continue
        glPushMatrix()
        glTranslatef(e["x"], e["y"], e["z"])
        glRotatef(e["yaw"], 0, 0, 1)
        glPushMatrix()
        glColor3f(0.80, 0.20, 0.20)
        draw_box(EN_HULL_W, EN_HULL_D, EN_HULL_H)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(0.0, 0.0, EN_TREAD_Z)
        glColor3f(0.12, 0.12, 0.12)
        draw_box(EN_HULL_W * 1.10, EN_HULL_D * 1.16, 5.0)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(0.0, 0.0, EN_TURRET_Z)
        glPushMatrix()
        glColor3f(0.65, 0.15, 0.15)
        draw_box(EN_TURRET_W, EN_TURRET_D, EN_TURRET_H)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(EN_BARREL_L * 0.5 + 6.0, 0.0, 0.0)
        glColor3f(0.0, 0.0, 0.0)
        draw_box(EN_BARREL_L, EN_BARREL_D, EN_BARREL_H)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(EN_BARREL_L + 6.0 + 3.0, 0.0, 0.0)
        glColor3f(0.05, 0.05, 0.05)
        glutSolidSphere(2.8, 10, 8)
        glPopMatrix()
        glPopMatrix()
        glPopMatrix()

def draw_enemy_bullets_basic():
    glColor3f(0.95, 0.35, 0.15)
    for b in enemy_bullets_basic:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], 18.0)
        glutSolidSphere(4.5, 10, 10)
        glPopMatrix()

# ---------- MiniBoss1 (10 HP) ----------
miniboss1 = None
mb1_bullets = []
MB1_HULL_W, MB1_HULL_H, MB1_HULL_D = 64.0, 24.0, 42.0
MB1_TURRET_W, MB1_TURRET_H, MB1_TURRET_D = 24.0, 10.0, 24.0
MB1_BARREL_L, MB1_BARREL_H, MB1_BARREL_D = 38.0, 5.0, 5.0
MB1_TURRET_Z = 14.0
MB1_TREAD_Z  = -12.0
MB1_SPEED_BASE = 0.6
MB1_TURN_BASE  = 28.0
MB1_BULLET_SPEED_BASE = 10.0
MB1_FIRE_CD_MS_BASE   = 900
MB1_BULLET_TTL   = 5200
MB1_HP_SEGMENTS = 10

def _spawn_miniboss1():
    global miniboss1
    for _ in range(20):
        r = random.choice([300.0, 360.0, 420.0])
        ang = random.random() * 2.0 * math.pi
        ex = tank_pos[0] + math.cos(ang) * r
        ey = tank_pos[1] + math.sin(ang) * r
        br = GRID_LENGTH - 80
        if -br <= ex <= br and -br <= ey <= br:
            break
    dx, dy = tank_pos[0] - ex, tank_pos[1] - ey
    yaw = deg(math.atan2(dy, dx))
    miniboss1 = dict(x=ex, y=ey, z=22.0, yaw=yaw, turret_rel=0.0, hp=MB1_HP_SEGMENTS, fire_t=0, fire_cd=MB1_FIRE_CD_MS_BASE, bullet_speed=MB1_BULLET_SPEED_BASE, speed=MB1_SPEED_BASE, turn_speed=MB1_TURN_BASE)

def _update_miniboss1(dt_ms):
    global player_hits_taken, game_over_freeze
    if miniboss1 is None:
        return
    dx, dy = tank_pos[0] - miniboss1["x"], tank_pos[1] - miniboss1["y"]
    miniboss1["yaw"] = deg(math.atan2(dy, dx))
    step = miniboss1["speed"] * (dt_ms / 16.0)
    miniboss1["x"] += math.cos(rad(miniboss1["yaw"])) * step
    miniboss1["y"] += math.sin(rad(miniboss1["yaw"])) * step
    br = GRID_LENGTH - 60
    miniboss1["x"] = clamp(miniboss1["x"], -br, br)
    miniboss1["y"] = clamp(miniboss1["y"], -br, br)
    max_step = miniboss1["turn_speed"] * (dt_ms / 1000.0)
    cur = miniboss1["turret_rel"]
    delta = clamp(0.0 - cur, -max_step, max_step)
    miniboss1["turret_rel"] = (cur + delta)
    miniboss1["fire_t"] += dt_ms
    if miniboss1["fire_t"] >= miniboss1["fire_cd"]:
        miniboss1["fire_t"] = 0
        aim = miniboss1["yaw"] + miniboss1["turret_rel"]
        aim_r = rad(aim)
        mx = miniboss1["x"] + math.cos(aim_r) * (MB1_BARREL_L + 12.0)
        my = miniboss1["y"] + math.sin(aim_r) * (MB1_BARREL_L + 12.0)
        mz = miniboss1["z"] + MB1_TURRET_Z
        mb1_bullets.append(dict(x=mx, y=my, z=mz, vx=math.cos(aim_r)*miniboss1["bullet_speed"], vy=math.sin(aim_r)*miniboss1["bullet_speed"], ttl=MB1_BULLET_TTL))
    rm = []
    for i, b in enumerate(mb1_bullets):
        b["x"] += b["vx"] * (dt_ms / 16.0)
        b["y"] += b["vy"] * (dt_ms / 16.0)
        b["ttl"] -= dt_ms
        out = (abs(b["x"]) >= BULLET_WALL_LIMIT or abs(b["y"]) >= BULLET_WALL_LIMIT or b["ttl"] <= 0)
        if not out and not cheat_invincible:
            if dist2(b["x"], b["y"], tank_pos[0], tank_pos[1]) <= (10.0 + 4.5)**2:
                player_hits_taken += 1
                out = True
                if player_hits_taken >= PLAYER_MAX_HITS:
                    game_over_freeze = True
        if out:
            rm.append(i)
    for idx in reversed(rm):
        mb1_bullets.pop(idx)

def _draw_miniboss1():
    if miniboss1 is None:
        return
    glPushMatrix()
    glTranslatef(miniboss1["x"], miniboss1["y"], miniboss1["z"])
    glRotatef(miniboss1["yaw"], 0, 0, 1)
    glPushMatrix()
    glColor3f(0.85, 0.45, 0.15)
    draw_box(MB1_HULL_W, MB1_HULL_D, MB1_HULL_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, 0.0, MB1_TREAD_Z)
    glColor3f(0.12, 0.12, 0.12)
    draw_box(MB1_HULL_W*1.10, MB1_HULL_D*1.16, 5.5)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, 0.0, MB1_TURRET_Z)
    glRotatef(miniboss1["turret_rel"], 0, 0, 1)
    glPushMatrix()
    glColor3f(0.55, 0.25, 0.12)
    draw_box(MB1_TURRET_W, MB1_TURRET_D, MB1_TURRET_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(MB1_BARREL_L * 0.5 + 7.0, 0.0, 0.0)
    glColor3f(0.0, 0.0, 0.0)
    draw_box(MB1_BARREL_L, MB1_BARREL_D, MB1_BARREL_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(MB1_BARREL_L + 7.0 + 3.0, 0.0, 0.0)
    glColor3f(0.05, 0.05, 0.05)
    glutSolidSphere(3.0, 12, 10)
    glPopMatrix()
    glPopMatrix()
    glPopMatrix()
    _draw_mb1_healthbar()

def _draw_mb1_healthbar():
    if miniboss1 is None:
        return
    segments = MB1_HP_SEGMENTS
    remain = max(0, miniboss1["hp"])
    total_w = 100.0
    seg_gap = 2.0
    seg_w = (total_w - (segments - 1) * seg_gap) / segments
    z = miniboss1["z"] + MB1_HULL_D * 0.6 + 22.0
    cx, cy = miniboss1["x"], miniboss1["y"]
    start_x = cx - total_w * 0.5
    y = cy
    for i in range(segments):
        x0 = start_x + i * (seg_w + seg_gap)
        x1 = x0 + seg_w
        if i < remain:
            glColor3f(0.15, 0.95, 0.15)
        else:
            glColor3f(0.25, 0.25, 0.25)
        glBegin(GL_QUADS)
        glVertex3f(x0, y-1.5, z)
        glVertex3f(x1, y-1.5, z)
        glVertex3f(x1, y+1.5, z)
        glVertex3f(x0, y+1.5, z)
        glEnd()

def _draw_mb1_bullets():
    glColor3f(0.95, 0.85, 0.25)
    for b in mb1_bullets:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], 20.0)
        glutSolidSphere(5.0, 12, 12)
        glPopMatrix()

def _player_bullets_vs_mb1():
    if miniboss1 is None:
        return False
    rm = []
    died = False
    for i, p in enumerate(projectiles):
        if dist2(p["x"], p["y"], miniboss1["x"], miniboss1["y"]) <= (MB1_HULL_W*0.40 + 4.0)**2:
            miniboss1["hp"] -= 1
            rm.append(i)
            if miniboss1["hp"] <= 0:
                died = True
                break
    for idx in reversed(rm):
        projectiles.pop(idx)
    return died

# ---------- Banners ----------
level1_complete_banner_ms = 0
level2_complete_banner_ms = 0
final_boss_banner_ms = 0
def _tick_banners(dt_ms):
    global level1_complete_banner_ms, level2_complete_banner_ms, final_boss_banner_ms
    if level1_complete_banner_ms > 0:
        level1_complete_banner_ms = max(0, level1_complete_banner_ms - dt_ms)
    if level2_complete_banner_ms > 0:
        level2_complete_banner_ms = max(0, level2_complete_banner_ms - dt_ms)
    if final_boss_banner_ms > 0:
        final_boss_banner_ms = max(0, final_boss_banner_ms - dt_ms)

# ===================== MiniBoss2 (Level 2) =====================
miniboss2 = None
mb2_bullets = []
mb2_spawned = False
MB2_HULL_W, MB2_HULL_H, MB2_HULL_D = 64.0, 24.0, 42.0
MB2_TURRET_W, MB2_TURRET_H, MB2_TURRET_D = 24.0, 10.0, 24.0
MB2_BARREL_L, MB2_BARREL_H, MB2_BARREL_D = 38.0, 5.0, 5.0
MB2_TURRET_Z = 14.0
MB2_TREAD_Z = -12.0
MB2_HP_SEGMENTS = 5
MB2_FIRE_CD_MS = 1200
MB2_BULLET_SPEED = 18.0
MB2_BULLET_TTL = 6000
MB2_AURA_RADIUS = 120.0
MB2_AURA_TICK_MS = 1000
MB2_AURA_DAMAGE = 2
MB2_TURRET_TURN = 24.0

def _spawn_miniboss2():
    global miniboss2, tank_pos, tank_yaw, barrel_rel, player_blocked
    miniboss2 = dict(x=0.0, y=0.0, z=22.0, yaw=0.0, turret_rel=0.0, hp=MB2_HP_SEGMENTS, fire_t=0, aura_t=0)
    corners = [(-GRID_LENGTH+80, -GRID_LENGTH+80), (GRID_LENGTH-80, -GRID_LENGTH+80), (-GRID_LENGTH+80,  GRID_LENGTH-80), (GRID_LENGTH-80,  GRID_LENGTH-80)]
    cx, cy = random.choice(corners)
    tank_pos[0], tank_pos[1] = cx, cy
    dx, dy = 0.0 - tank_pos[0], 0.0 - tank_pos[1]
    tank_yaw = deg(math.atan2(dy, dx)) % 360.0
    barrel_rel = 0.0
    player_blocked = False

def _update_miniboss2(dt_ms):
    global player_hits_taken, game_over_freeze
    if miniboss2 is None:
        return
    dx, dy = tank_pos[0] - miniboss2["x"], tank_pos[1] - miniboss2["y"]
    desired_world = deg(math.atan2(dy, dx))
    desired_rel = ang_norm(desired_world - miniboss2["yaw"])
    cur_rel = miniboss2["turret_rel"]
    max_step = MB2_TURRET_TURN * (dt_ms / 1000.0)
    step = clamp(ang_norm(desired_rel - cur_rel), -max_step, max_step)
    miniboss2["turret_rel"] = cur_rel + step
    miniboss2["fire_t"] += dt_ms
    if miniboss2["fire_t"] >= MB2_FIRE_CD_MS:
        miniboss2["fire_t"] = 0
        aim = miniboss2["yaw"] + miniboss2["turret_rel"]
        aim_r = rad(aim)
        mx = miniboss2["x"] + math.cos(aim_r) * (MB2_BARREL_L + 14.0)
        my = miniboss2["y"] + math.sin(aim_r) * (MB2_BARREL_L + 14.0)
        mz = miniboss2["z"] + MB2_TURRET_Z
        mb2_bullets.append(dict(x=mx, y=my, z=mz, vx=math.cos(aim_r) * MB2_BULLET_SPEED, vy=math.sin(aim_r) * MB2_BULLET_SPEED, ttl=MB2_BULLET_TTL))
    if not cheat_invincible:
        miniboss2["aura_t"] += dt_ms
        if dist2(tank_pos[0], tank_pos[1], miniboss2["x"], miniboss2["y"]) <= MB2_AURA_RADIUS * MB2_AURA_RADIUS:
            if miniboss2["aura_t"] >= MB2_AURA_TICK_MS:
                miniboss2["aura_t"] = 0
                player_hits_taken += MB2_AURA_DAMAGE
                if player_hits_taken >= PLAYER_MAX_HITS:
                    game_over_freeze = True
        else:
            miniboss2["aura_t"] = 0
    rm = []
    for i, b in enumerate(mb2_bullets):
        b["x"] += b["vx"] * (dt_ms / 16.0)
        b["y"] += b["vy"] * (dt_ms / 16.0)
        b["ttl"] -= dt_ms
        out = (abs(b["x"]) >= BULLET_WALL_LIMIT or abs(b["y"]) >= BULLET_WALL_LIMIT or b["ttl"] <= 0)
        if not out and not cheat_invincible:
            if dist2(b["x"], b["y"], tank_pos[0], tank_pos[1]) <= (10.0 + 5.0)**2:
                player_hits_taken += 1
                out = True
                if player_hits_taken >= PLAYER_MAX_HITS:
                    game_over_freeze = True
        if out:
            rm.append(i)
    for idx in reversed(rm):
        mb2_bullets.pop(idx)

def _player_bullets_vs_mb2():
    if miniboss2 is None:
        return False
    rm = []
    died = False
    for i, p in enumerate(projectiles):
        if dist2(p["x"], p["y"], miniboss2["x"], miniboss2["y"]) <= (MB2_HULL_W*0.40 + 5.0)**2:
            miniboss2["hp"] -= 2
            rm.append(i)
            if miniboss2["hp"] <= 0:
                died = True
                break
    for idx in reversed(rm):
        projectiles.pop(idx)
    return died

def _draw_miniboss2():
    if miniboss2 is None:
        return
    glPushMatrix()
    glTranslatef(miniboss2["x"], miniboss2["y"], miniboss2["z"])
    glRotatef(miniboss2["yaw"], 0, 0, 1)
    glPushMatrix()
    glColor3f(0.10, 0.65, 0.70)
    draw_box(MB2_HULL_W, MB2_HULL_D, MB2_HULL_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, 0.0, MB2_TREAD_Z)
    glColor3f(0.12, 0.12, 0.12)
    draw_box(MB2_HULL_W*1.10, MB2_HULL_D*1.16, 5.5)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, 0.0, MB2_TURRET_Z)
    glRotatef(miniboss2["turret_rel"], 0, 0, 1)
    glPushMatrix()
    glColor3f(0.06, 0.45, 0.50)
    draw_box(MB2_TURRET_W, MB2_TURRET_D, MB2_TURRET_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(MB2_BARREL_L * 0.5 + 7.0, 0.0, 0.0)
    glColor3f(0.0, 0.0, 0.0)
    draw_box(MB2_BARREL_L, MB2_BARREL_D, MB2_BARREL_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(MB2_BARREL_L + 7.0 + 3.0, 0.0, 0.0)
    glColor3f(0.05, 0.05, 0.05)
    glutSolidSphere(3.0, 12, 10)
    glPopMatrix()
    glPopMatrix()
    glPopMatrix()
    _draw_mb2_healthbar()
    glColor3f(0.1, 0.8, 0.8)
    glBegin(GL_LINE_LOOP)
    for i in range(48):
        a = 2.0*math.pi*i/48
        glVertex3f(miniboss2["x"] + math.cos(a)*MB2_AURA_RADIUS, miniboss2["y"] + math.sin(a)*MB2_AURA_RADIUS, 1.0)
    glEnd()

def _draw_mb2_healthbar():
    if miniboss2 is None:
        return
    segments = MB2_HP_SEGMENTS
    remain = max(0, miniboss2["hp"])
    total_w = 80.0
    seg_gap = 2.0
    seg_w = (total_w - (segments - 1) * seg_gap) / segments
    z = miniboss2["z"] + MB2_HULL_D * 0.6 + 22.0
    cx, cy = miniboss2["x"], miniboss2["y"]
    start_x = cx - total_w * 0.5
    y = cy
    for i in range(segments):
        x0 = start_x + i * (seg_w + seg_gap)
        x1 = x0 + seg_w
        if i < remain:
            glColor3f(0.15, 0.95, 0.15)
        else:
            glColor3f(0.25, 0.25, 0.25)
        glBegin(GL_QUADS)
        glVertex3f(x0, y-1.5, z)
        glVertex3f(x1, y-1.5, z)
        glVertex3f(x1, y+1.5, z)
        glVertex3f(x0, y+1.5, z)
        glEnd()

def _draw_mb2_bullets():
    glColor3f(0.25, 0.85, 0.95)
    for b in mb2_bullets:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], 22.0)
        glutSolidSphere(6.0, 14, 14)
        glPopMatrix()

# ===================== MiniBoss3 (Level 3, Twins) =====================
miniboss3 = None
mb3_bullets = []
mb3_spawned = False
MB3_HULL_W, MB3_HULL_H, MB3_HULL_D = 62.0, 24.0, 40.0
MB3_TURRET_W, MB3_TURRET_H, MB3_TURRET_D = 22.0, 10.0, 22.0
MB3_BARREL_L, MB3_BARREL_H, MB3_BARREL_D = 36.0, 5.0, 5.0
MB3_TURRET_Z = 14.0
MB3_TREAD_Z  = -12.0
MB3_SPEED = 0.55
MB3_BULLET_SPEED = 14.0
MB3_BULLET_TTL = 5200
MB3_FIRE_CD_MS = 3000
MB3_SPREAD_DEG = 12.0
MB3_CLONE_HP = 3
MB3_TOTAL_HP = 6

def _spawn_miniboss3():
    global miniboss3
    clones = []
    base_r = 320.0
    base_ang = random.random() * 2.0 * math.pi
    pos1 = (tank_pos[0] + math.cos(base_ang) * base_r, tank_pos[1] + math.sin(base_ang) * base_r)
    pos2 = (tank_pos[0] + math.cos(base_ang + math.pi) * base_r, tank_pos[1] + math.sin(base_ang + math.pi) * base_r)
    for (ex, ey) in (pos1, pos2):
        br = GRID_LENGTH - 80
        ex = clamp(ex, -br, br)
        ey = clamp(ey, -br, br)
        yaw = deg(math.atan2(tank_pos[1] - ey, tank_pos[0] - ex))
        clones.append(dict(x=ex, y=ey, z=22.0, yaw=yaw, hp=MB3_CLONE_HP, fire_t=0.0, alive=True))
    miniboss3 = dict(clones=clones)

def _update_miniboss3(dt_ms):
    global player_hits_taken, game_over_freeze
    if miniboss3 is None:
        return
    clones = miniboss3["clones"]
    for c in clones:
        if not c["alive"]:
            continue
        dx, dy = tank_pos[0] - c["x"], tank_pos[1] - c["y"]
        c["yaw"] = deg(math.atan2(dy, dx))
        step = MB3_SPEED * (dt_ms / 16.0)
        c["x"] += math.cos(rad(c["yaw"])) * step
        c["y"] += math.sin(rad(c["yaw"])) * step
        br = GRID_LENGTH - 60
        c["x"] = clamp(c["x"], -br, br)
        c["y"] = clamp(c["y"], -br, br)
    if all(cl["alive"] for cl in clones):
        c0, c1 = clones[0], clones[1]
        dx = c1["x"] - c0["x"]
        dy = c1["y"] - c0["y"]
        d2 = dx*dx + dy*dy
        if d2 < (EN_HULL_W*1.2)**2:
            d = max(1e-3, math.sqrt(d2))
            push = (EN_HULL_W*1.2 - d) * 0.5
            nx, ny = dx/d, dy/d
            c0["x"] -= nx * push
            c0["y"] -= ny * push
            c1["x"] += nx * push
            c1["y"] += ny * push
    for c in clones:
        if not c["alive"]:
            continue
        c["fire_t"] += dt_ms
        if c["fire_t"] >= MB3_FIRE_CD_MS:
            c["fire_t"] = 0
            aim = c["yaw"]
            for off in (0.0, MB3_SPREAD_DEG, -MB3_SPREAD_DEG):
                a = rad(aim + off)
                mx = c["x"] + math.cos(a) * (MB3_BARREL_L + 12.0)
                my = c["y"] + math.sin(a) * (MB3_BARREL_L + 12.0)
                mz = c["z"] + MB3_TURRET_Z
                mb3_bullets.append(dict(x=mx, y=my, z=mz, vx=math.cos(a) * MB3_BULLET_SPEED, vy=math.sin(a) * MB3_BULLET_SPEED, ttl=MB3_BULLET_TTL))
    rm = []
    for i, b in enumerate(mb3_bullets):
        b["x"] += b["vx"] * (dt_ms / 16.0)
        b["y"] += b["vy"] * (dt_ms / 16.0)
        b["ttl"] -= dt_ms
        out = (abs(b["x"]) >= BULLET_WALL_LIMIT or abs(b["y"]) >= BULLET_WALL_LIMIT or b["ttl"] <= 0)
        if not out and not cheat_invincible:
            if dist2(b["x"], b["y"], tank_pos[0], tank_pos[1]) <= (10.0 + 5.0)**2:
                player_hits_taken += 1
                out = True
                if player_hits_taken >= PLAYER_MAX_HITS:
                    game_over_freeze = True
        if out:
            rm.append(i)
    for idx in reversed(rm):
        mb3_bullets.pop(idx)

def _player_bullets_vs_mb3():
    if miniboss3 is None:
        return False
    clones = miniboss3["clones"]
    rm = []
    for i, p in enumerate(projectiles):
        hit_any = False
        for c in clones:
            if not c["alive"]:
                continue
            if dist2(p["x"], p["y"], c["x"], c["y"]) <= (MB3_HULL_W*0.40 + 5.0)**2:
                c["hp"] -= 1
                if c["hp"] <= 0:
                    c["alive"] = False
                hit_any = True
                break
        if hit_any:
            rm.append(i)
    for idx in reversed(rm):
        projectiles.pop(idx)
    return all(not c["alive"] for c in clones)

def _draw_miniboss3():
    if miniboss3 is None:
        return
    for c in miniboss3["clones"]:
        if not c["alive"]:
            continue
        glPushMatrix()
        glTranslatef(c["x"], c["y"], c["z"])
        glRotatef(c["yaw"], 0, 0, 1)
        glPushMatrix()
        glColor3f(0.70, 0.20, 0.70)
        draw_box(MB3_HULL_W, MB3_HULL_D, MB3_HULL_H)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(0.0, 0.0, MB3_TREAD_Z)
        glColor3f(0.12, 0.12, 0.12)
        draw_box(MB3_HULL_W*1.10, MB3_HULL_D*1.16, 5.5)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(0.0, 0.0, MB3_TURRET_Z)
        glPushMatrix()
        glColor3f(0.45, 0.12, 0.45)
        draw_box(MB3_TURRET_W, MB3_TURRET_D, MB3_TURRET_H)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(MB3_BARREL_L * 0.5 + 7.0, 0.0, 0.0)
        glColor3f(0.0, 0.0, 0.0)
        draw_box(MB3_BARREL_L, MB3_BARREL_D, MB3_BARREL_H)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(MB3_BARREL_L + 7.0 + 3.0, 0.0, 0.0)
        glColor3f(0.05, 0.05, 0.05)
        glutSolidSphere(3.0, 12, 10)
        glPopMatrix()
        glPopMatrix()
        glPopMatrix()
        _draw_mb3_clone_healthbar(c)

def _draw_mb3_clone_healthbar(c):
    segments = MB3_CLONE_HP
    remain = max(0, c["hp"])
    total_w = 60.0
    seg_gap = 2.0
    seg_w = (total_w - (segments - 1) * seg_gap) / segments
    z = c["z"] + MB3_HULL_D * 0.6 + 20.0
    cx, cy = c["x"], c["y"]
    start_x = cx - total_w * 0.5
    y = cy
    for i in range(segments):
        x0 = start_x + i * (seg_w + seg_gap)
        x1 = x0 + seg_w
        if i < remain:
            glColor3f(0.15, 0.95, 0.15)
        else:
            glColor3f(0.25, 0.25, 0.25)
        glBegin(GL_QUADS)
        glVertex3f(x0, y-1.2, z)
        glVertex3f(x1, y-1.2, z)
        glVertex3f(x1, y+1.2, z)
        glVertex3f(x0, y+1.2, z)
        glEnd()

def _draw_mb3_bullets():
    glColor3f(0.95, 0.55, 0.95)
    for b in mb3_bullets:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], 22.0)
        glutSolidSphere(5.5, 12, 12)
        glPopMatrix()

# ===================== FINAL BOSS (Level 4) =====================
final_boss = None
fb_bullets = []
fb_spawned = False
FB_HULL_W, FB_HULL_H, FB_HULL_D = 110.0, 36.0, 80.0
FB_TURRET_W, FB_TURRET_H, FB_TURRET_D = 42.0, 16.0, 42.0
FB_BARREL_L, FB_BARREL_H, FB_BARREL_D = 56.0, 7.0, 7.0
FB_TURRET_Z = 22.0
FB_TREAD_Z  = -18.0
FB_HP = 20
FB_SPEED = 0.48
FB_STANDOFF_R = 220.0
FB_STANDOFF_DB = 12.0
FB_BULLET_SPEED = 18.0
FB_BULLET_TTL = 6500
FB_VOLLEY_SPREADS = (-18.0, -6.0, 6.0, 18.0)
FB_PAUSE_MS = 1000
FB_LASER_MS = 1000
FB_BURST_MS = 2500
FB_LASER_LEN = 1400.0
FB_LASER_HIT_RADIUS = 14.0
FB_PHASE_BURST = 0
FB_PHASE_PAUSE = 1
FB_PHASE_LASER = 2
fb_laser_active = False

def _spawn_final_boss():
    global final_boss
    r = GRID_LENGTH - 180.0
    a = random.random() * 2.0 * math.pi
    ex = clamp(math.cos(a) * r, -GRID_LENGTH+80, GRID_LENGTH-80)
    ey = clamp(math.sin(a) * r, -GRID_LENGTH+80, GRID_LENGTH-80)
    yaw = deg(math.atan2(tank_pos[1] - ey, tank_pos[0] - ex))
    final_boss = dict(x=ex, y=ey, z=26.0, yaw=yaw, hp=FB_HP, phase=FB_PHASE_BURST, phase_t=0, laser_ax=0.0, laser_ay=0.0, laser_bx=0.0, laser_by=0.0)

def _fb_move_toward_standoff(dt_ms):
    dtx = tank_pos[0] - final_boss["x"]
    dty = tank_pos[1] - final_boss["y"]
    final_boss["yaw"] = deg(math.atan2(dty, dtx))
    d = math.hypot(dtx, dty)
    step = FB_SPEED * (dt_ms / 16.0)
    if d > FB_STANDOFF_R + FB_STANDOFF_DB:
        final_boss["x"] += math.cos(rad(final_boss["yaw"])) * step
        final_boss["y"] += math.sin(rad(final_boss["yaw"])) * step
    elif d < FB_STANDOFF_R - FB_STANDOFF_DB:
        back = step * 0.6
        final_boss["x"] -= math.cos(rad(final_boss["yaw"])) * back
        final_boss["y"] -= math.sin(rad(final_boss["yaw"])) * back
    br = GRID_LENGTH - 70
    final_boss["x"] = clamp(final_boss["x"], -br, br)
    final_boss["y"] = clamp(final_boss["y"], -br, br)

def _fb_fire_volley():
    aim = final_boss["yaw"]
    for off in FB_VOLLEY_SPREADS:
        a = rad(aim + off)
        mx = final_boss["x"] + math.cos(a) * (FB_BARREL_L + 18.0)
        my = final_boss["y"] + math.sin(a) * (FB_BARREL_L + 18.0)
        mz = final_boss["z"] + FB_TURRET_Z
        fb_bullets.append(dict(x=mx, y=my, z=mz, vx=math.cos(a) * FB_BULLET_SPEED, vy=math.sin(a) * FB_BULLET_SPEED, ttl=FB_BULLET_TTL))

def _calculate_laser_endpoint(ox, oy, angle_deg):
    angle_rad = rad(angle_deg)
    dx, dy = math.cos(angle_rad), math.sin(angle_rad)
    t_values = []
    if abs(dx) > 1e-6:
        t_x1 = (GRID_LENGTH - ox) / dx
        t_x2 = (-GRID_LENGTH - ox) / dx
        if t_x1 > 0: t_values.append(t_x1)
        if t_x2 > 0: t_values.append(t_x2)
    if abs(dy) > 1e-6:
        t_y1 = (GRID_LENGTH - oy) / dy
        t_y2 = (-GRID_LENGTH - oy) / dy
        if t_y1 > 0: t_values.append(t_y1)
        if t_y2 > 0: t_values.append(t_y2)
    if not t_values:
        return (ox + dx * FB_LASER_LEN, oy + dy * FB_LASER_LEN)
    min_t = min(t_values)
    return (ox + min_t * dx, oy + min_t * dy)

def _fb_begin_laser():
    global fb_laser_active
    fb_laser_active = True
    aim = final_boss["yaw"]
    ax, ay = final_boss["x"], final_boss["y"]
    bx, by = _calculate_laser_endpoint(ax, ay, aim)
    final_boss["laser_ax"] = ax
    final_boss["laser_ay"] = ay
    final_boss["laser_bx"] = bx
    final_boss["laser_by"] = by

def _update_final_boss(dt_ms):
    global player_hits_taken, game_over_freeze, killed_by_laser, fb_laser_active
    if final_boss is None:
        return
    phase = final_boss["phase"]
    final_boss["phase_t"] += dt_ms
    if phase == FB_PHASE_BURST:
        if final_boss["phase_t"] <= dt_ms + 1:
            _fb_fire_volley()
        _fb_move_toward_standoff(dt_ms)
        if final_boss["phase_t"] >= FB_BURST_MS:
            final_boss["phase"] = FB_PHASE_PAUSE
            final_boss["phase_t"] = 0
    elif phase == FB_PHASE_PAUSE:
        if final_boss["phase_t"] >= FB_PAUSE_MS:
            final_boss["phase"] = FB_PHASE_LASER
            final_boss["phase_t"] = 0
            _fb_begin_laser()
    elif phase == FB_PHASE_LASER:
        ax, ay, bx, by = final_boss["laser_ax"], final_boss["laser_ay"], final_boss["laser_bx"], final_boss["laser_by"]
        if not cheat_invincible and not game_over_freeze:
            d2 = point_segment_dist2(tank_pos[0], tank_pos[1], ax, ay, bx, by)
            if d2 <= FB_LASER_HIT_RADIUS * FB_LASER_HIT_RADIUS:
                killed_by_laser = True
                player_hits_taken = PLAYER_MAX_HITS
                game_over_freeze = True
        if final_boss["phase_t"] >= FB_LASER_MS:
            final_boss["phase"] = FB_PHASE_BURST
            final_boss["phase_t"] = 0
            fb_laser_active = False
    rm = []
    for i, b in enumerate(fb_bullets):
        b["x"] += b["vx"] * (dt_ms / 16.0)
        b["y"] += b["vy"] * (dt_ms / 16.0)
        b["ttl"] -= dt_ms
        out = (abs(b["x"]) >= BULLET_WALL_LIMIT or abs(b["y"]) >= BULLET_WALL_LIMIT or b["ttl"] <= 0)
        if not out and not cheat_invincible:
            if dist2(b["x"], b["y"], tank_pos[0], tank_pos[1]) <= (10.0 + 6.0)**2:
                player_hits_taken += 1
                out = True
                if player_hits_taken >= PLAYER_MAX_HITS:
                    game_over_freeze = True
        if out:
            rm.append(i)
    for idx in reversed(rm):
        fb_bullets.pop(idx)

def _player_bullets_vs_final_boss():
    if final_boss is None:
        return False
    rm = []
    died = False
    for i, p in enumerate(projectiles):
        if dist2(p["x"], p["y"], final_boss["x"], final_boss["y"]) <= (FB_HULL_W*0.45 + 6.0)**2:
            final_boss["hp"] -= 1
            rm.append(i)
            if final_boss["hp"] <= 0:
                died = True
                break
    for idx in reversed(rm):
        projectiles.pop(idx)
    return died

def _draw_final_boss():
    if final_boss is None:
        return
    glPushMatrix()
    glTranslatef(final_boss["x"], final_boss["y"], final_boss["z"])
    glRotatef(final_boss["yaw"], 0, 0, 1)
    glPushMatrix()
    glColor3f(0.95, 0.75, 0.15)
    draw_box(FB_HULL_W, FB_HULL_D, FB_HULL_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, 0.0, FB_TREAD_Z)
    glColor3f(0.12, 0.12, 0.12)
    draw_box(FB_HULL_W*1.12, FB_HULL_D*1.18, 7.0)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.0, 0.0, FB_TURRET_Z)
    glPushMatrix()
    glColor3f(0.90, 0.45, 0.10)
    draw_box(FB_TURRET_W, FB_TURRET_D, FB_TURRET_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(FB_BARREL_L * 0.5 + 10.0, 0.0, 0.0)
    glColor3f(0.05, 0.05, 0.05)
    draw_box(FB_BARREL_L, FB_BARREL_D, FB_BARREL_H)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(FB_BARREL_L + 10.0 + 4.0, 0.0, 0.0)
    glColor3f(0.1, 0.1, 0.1)
    glutSolidSphere(4.2, 14, 12)
    glPopMatrix()
    glPopMatrix()
    glPopMatrix()
    segments = FB_HP
    remain = max(0, final_boss["hp"])
    total_w = 140.0
    seg_gap = 2.0
    seg_w = (total_w - (segments - 1) * seg_gap) / segments
    z = final_boss["z"] + FB_HULL_D * 0.6 + 26.0
    cx, cy = final_boss["x"], final_boss["y"]
    start_x = cx - total_w * 0.5
    y = cy
    for i in range(segments):
        x0 = start_x + i * (seg_w + seg_gap)
        x1 = x0 + seg_w
        if i < remain:
            glColor3f(0.15, 0.95, 0.15)
        else:
            glColor3f(0.25, 0.25, 0.25)
        glBegin(GL_QUADS)
        glVertex3f(x0, y-2.0, z)
        glVertex3f(x1, y-2.0, z)
        glVertex3f(x1, y+2.0, z)
        glVertex3f(x0, y+2.0, z)
        glEnd()

def _draw_fb_bullets():
    glColor3f(0.95, 0.45, 0.15)
    for b in fb_bullets:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], 26.0)
        glutSolidSphere(6.2, 14, 14)
        glPopMatrix()

def _draw_fb_laser():
    if not fb_laser_active:
        return
    ax, ay = final_boss["laser_ax"], final_boss["laser_ay"]
    bx, by = final_boss["laser_bx"], final_boss["laser_by"]
    glLineWidth(4.0)
    glColor3f(1.0, 0.1, 0.1)
    glBegin(GL_LINES)
    glVertex3f(ax, ay, 24.0)
    glVertex3f(bx, by, 24.0)
    glEnd()
    glLineWidth(1.0)

# ---------- Simulation updates ----------
last_time_ms = 0

def update_player(dt_ms):
    global tank_velocity, strafe_velocity, tank_yaw, barrel_rel
    forward = 0.0
    turn = 0.0
    strafe = 0.0
    if game_over_freeze or game_win_freeze:
        if 'j' in keys_down:
            barrel_rel = (barrel_rel - 1.4) % 360.0
        if 'l' in keys_down:
            barrel_rel = (barrel_rel + 1.4) % 360.0
        return
    if 'w' in keys_down: forward += 0.3
    if 's' in keys_down: forward -= 0.3
    if 'd' in keys_down: turn -= 0.3
    if 'a' in keys_down: turn += 0.3
    if 'e' in keys_down: strafe -= 0.5
    if 'q' in keys_down: strafe += 0.5
    if 'j' in keys_down: barrel_rel = (barrel_rel - 1.4) % 360.0
    if 'l' in keys_down: barrel_rel = (barrel_rel + 1.4) % 360.0
    if player_blocked:
        forward = 0.0
        strafe = 0.0
        tank_velocity *= (1.0 - friction)
        strafe_velocity *= (1.0 - friction)
    target_speed = max_speed * forward
    if abs(target_speed) > abs(tank_velocity):
        tank_velocity += accel * math.copysign(1.0, target_speed - tank_velocity)
    else:
        if tank_velocity > target_speed:
            tank_velocity = max(target_speed, tank_velocity - decel)
        else:
            tank_velocity = min(target_speed, tank_velocity + decel)
    if forward == 0.0:
        tank_velocity *= (1.0 - friction)
    target_strafe = strafe * strafe_speed
    if abs(target_strafe) > abs(strafe_velocity):
        strafe_velocity += 0.18 * math.copysign(1.0, target_strafe - strafe_velocity)
    else:
        if strafe_velocity > target_strafe:
            strafe_velocity = max(target_strafe, strafe_velocity - 0.22)
        else:
            strafe_velocity = min(target_strafe, strafe_velocity + 0.22)
    if strafe == 0.0:
        strafe_velocity *= (1.0 - friction)
    fwd_dx = math.cos(rad(tank_yaw)) * tank_velocity
    fwd_dy = math.sin(rad(tank_yaw)) * tank_velocity
    strafe_ang = tank_yaw + 90.0
    str_dx = math.cos(rad(strafe_ang)) * strafe_velocity
    str_dy = math.sin(rad(strafe_ang)) * strafe_velocity
    tank_pos[0] += fwd_dx + str_dx
    tank_pos[1] += fwd_dy + str_dy
    tank_yaw = (tank_yaw + turn * turn_speed) % 360.0
    border = GRID_LENGTH - 50
    tank_pos[0] = clamp(tank_pos[0], -border, border)
    tank_pos[1] = clamp(tank_pos[1], -border, border)

def update_projectiles(dt_ms):
    remove_idx = []
    for i, p in enumerate(projectiles):
        p["x"] += p["vx"] * (dt_ms / 16.0)
        p["y"] += p["vy"] * (dt_ms / 16.0)
        p["ttl"] -= dt_ms
        if p["ttl"] <= 0 or abs(p["x"]) >= BULLET_WALL_LIMIT or abs(p["y"]) >= BULLET_WALL_LIMIT:
            remove_idx.append(i)
    for idx in reversed(remove_idx):
        projectiles.pop(idx)

def idle():
    global last_time_ms, miniboss1, mb2_spawned, miniboss2, mb3_spawned, miniboss3, fb_spawned, final_boss, game_win_freeze
    now = glutGet(GLUT_ELAPSED_TIME)
    if last_time_ms == 0:
        last_time_ms = now
    dt = now - last_time_ms
    last_time_ms = now
    if not (game_over_freeze or game_win_freeze):
        update_player(dt)
        update_projectiles(dt)
        update_enemies_basic(dt)
        if basic_kills >= 5 and miniboss1 is None and level_index == 1:
            _spawn_miniboss1()
        _update_miniboss1(dt)
        if _player_bullets_vs_mb1():
            mb1_bullets.clear()
            miniboss1 = None
            level1_complete_banner_ms = 2200
            set_level(2)
            mb2_spawned = False
            spawn_seven_enemies_level2()
        if level_index == 2:
            alive_left = sum(1 for e in enemies_basic if e["alive"])
            if not mb2_spawned and miniboss2 is None and basic_kills >= 7 and alive_left == 0:
                enemy_bullets_basic.clear()
                _spawn_miniboss2()
                mb2_spawned = True
        _update_miniboss2(dt)
        if _player_bullets_vs_mb2():
            mb2_bullets.clear()
            miniboss2 = None
            level2_complete_banner_ms = 2000
            set_level(3)
            mb3_spawned = False
            spawn_ten_enemies_level3()
        if level_index == 3:
            alive_left3 = sum(1 for e in enemies_basic if e["alive"])
            if not mb3_spawned and miniboss3 is None and basic_kills >= 10 and alive_left3 == 0:
                enemy_bullets_basic.clear()
                _spawn_miniboss3()
                mb3_spawned = True
        _update_miniboss3(dt)
        if _player_bullets_vs_mb3():
            mb3_bullets.clear()
            miniboss3 = None
            final_boss_banner_ms = 3000
            set_level(4)
            fb_spawned = False
        if level_index == 4:
            if not fb_spawned and final_boss is None:
                _spawn_final_boss()
                fb_spawned = True
            _update_final_boss(dt)
            if _player_bullets_vs_final_boss():
                final_boss = None
                fb_bullets.clear()
                game_win_freeze = True
        _tick_banners(dt)
    glutPostRedisplay()

def draw_arena_walls():
    wall_h = 48.0
    wall_t = 12.0
    # North Wall
    glPushMatrix()
    glTranslatef(0.0, GRID_LENGTH + wall_t/2, wall_h/2)
    glColor3f(0.9, 0.9, 1.0)
    draw_box(GRID_LENGTH*2 + wall_t*2, wall_t, wall_h)
    glPopMatrix()
    # South Wall
    glPushMatrix()
    glTranslatef(0.0, -GRID_LENGTH - wall_t/2, wall_h/2)
    glColor3f(1.0, 0.92, 0.9)
    draw_box(GRID_LENGTH*2 + wall_t*2, wall_t, wall_h)
    glPopMatrix()
    # West Wall
    glPushMatrix()
    glTranslatef(-GRID_LENGTH - wall_t/2, 0.0, wall_h/2)
    glColor3f(0.92, 1.0, 0.92)
    draw_box(wall_t, GRID_LENGTH*2, wall_h)
    glPopMatrix()
    # East Wall
    glPushMatrix()
    glTranslatef(GRID_LENGTH + wall_t/2, 0.0, wall_h/2)
    glColor3f(1.0, 0.98, 0.9)
    draw_box(wall_t, GRID_LENGTH*2, wall_h)
    glPopMatrix()

# ---------- Display ----------
def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_W, WINDOW_H)
    setupCamera()
    draw_ground()
    draw_arena_walls()
    draw_tank()
    draw_projectiles()
    _draw_miniboss1()
    _draw_mb1_bullets()
    _draw_miniboss2()
    _draw_mb2_bullets()
    _draw_miniboss3()
    _draw_mb3_bullets()
    _draw_final_boss()
    _draw_fb_bullets()
    _draw_fb_laser()
    draw_enemies_basic()
    draw_enemy_bullets_basic()
    status = "BLOCKED" if player_blocked else "FREE"
    boss_txt = ""
    if level_index == 1 and miniboss1:
        boss_txt = f" | MB1 HP: {miniboss1['hp']}/{MB1_HP_SEGMENTS}"
    elif level_index == 2 and miniboss2:
        boss_txt = f" | MB2 HP: {miniboss2['hp']}/{MB2_HP_SEGMENTS}"
    elif level_index == 3 and miniboss3:
        total_hp = sum(c['hp'] for c in miniboss3['clones'] if c['alive'])
        boss_txt = f" | MB3 HP: {total_hp}/{MB3_TOTAL_HP}"
    elif level_index == 4 and final_boss:
        boss_txt = f" | FINAL BOSS HP: {final_boss['hp']}/{FB_HP}"
    draw_text(10, WINDOW_H - 30, f"{mode_name}{boss_txt}")
    draw_text(10, WINDOW_H - 60, f"Cam: {'FIRST' if camera_mode_first_person else 'THIRD'}  |  Cheat: {'ON' if cheat_invincible else 'OFF'}  |  Hits: {player_hits_taken}/{PLAYER_MAX_HITS}  |  {status}")
    draw_text(10, WINDOW_H - 90, "W/S accel/brake | A/D turn | Q/E strafe | J/L turret | LMB fire | RMB/T cam | 1..4 level (jump) | C cheat | R reset")
    if level1_complete_banner_ms > 0:
        draw_center_banner("Level 1 completed", 0.0, 0.95, 0.0)
    if level2_complete_banner_ms > 0:
        draw_center_banner("Level 2 completed!", 0.0, 0.95, 0.0)
    if final_boss_banner_ms > 0:
        draw_center_banner("FINAL BOSS", 0.95, 0.05, 0.05)
    if game_win_freeze:
        draw_center_banner("YOU WON!!", 0.1, 1.0, 0.1)
    elif game_over_freeze:
        if killed_by_laser:
            draw_center_banner("GAME OVER - INCINERATED", 0.95, 0.05, 0.05)
        else:
            draw_center_banner("GAME OVER", 0.95, 0.05, 0.05)
    glutSwapBuffers()

# ---------- GL init / main ----------
def init_gl():
    glClearColor(0.04, 0.06, 0.09, 1.0)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_NORMALIZE)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Battle Tanks - Full Game (Final Boss)")
    init_gl()
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    spawn_five_enemies()
    glutMainLoop()

if __name__ == "__main__":
    main()

