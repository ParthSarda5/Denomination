import math
import os
import time
import pygame

pygame.init()
pygame.font.init()

# ─────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────

BG = (10, 12, 20)
PANEL = (18, 22, 36)
PANEL2 = (25, 31, 50)
SEP = (42, 50, 80)

CELL = (28, 34, 54)
CELL_HOVER = (42, 50, 78)
CELL_BORDER = (54, 66, 102)

NULL_FILL = (25, 75, 45)
NULL_BORDER = (70, 220, 120)

SUM_FILL = (20, 48, 95)
SUM_BORDER = (90, 165, 255)

TEXT = (220, 228, 248)
TEXT_DIM = (120, 132, 160)
TEXT_FAINT = (70, 82, 110)

GREEN = (70, 210, 120)
RED = (235, 90, 90)
BLUE = (80, 150, 255)
GOLD = (240, 200, 70)

STONE = [
    None,
    (100, 110, 140),
    (220, 180, 60),
    (200, 85, 70),
    (70, 180, 100),
    (60, 145, 235),
    (150, 90, 235),
    (220, 70, 140),
    (55, 200, 190),
    (240, 130, 55),
]

HEADER_H = 64
FOOTER_H = 74
MARGIN = 28
CELL_GAP = 4
MIN_CELL = 52
MAX_CELL = 110

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def clamp(v):
    return max(0, min(255, int(v)))

def lighten(c, t):
    return tuple(clamp(c[i] + (255-c[i])*t) for i in range(3))

def darken(c, t):
    return tuple(clamp(c[i]*(1-t)) for i in range(3))

def mix(a, b, t):
    return tuple(clamp(a[i] + (b[i]-a[i])*t) for i in range(3))

def frect(s, c, r, rad=0):
    pygame.draw.rect(s, c, r, border_radius=rad)

def orect(s, c, r, w=1, rad=0):
    pygame.draw.rect(s, c, r, w, border_radius=rad)

# ─────────────────────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────────────────────

FONT = "dejavusans"
MONO = "dejavusansmono"

fonts = {
    "title": pygame.font.SysFont(FONT, 46, bold=True),
    "sub": pygame.font.SysFont(FONT, 16),
    "menu": pygame.font.SysFont(FONT, 17, bold=True),
    "play": pygame.font.SysFont(FONT, 19, bold=True),
    "status": pygame.font.SysFont(FONT, 14, bold=True),
    "ctrl": pygame.font.SysFont(FONT, 11),
    "cell_big": pygame.font.SysFont(FONT, 30, bold=True),
    "cell_mid": pygame.font.SysFont(FONT, 22, bold=True),
    "coord": pygame.font.SysFont(MONO, 10),
    "header": pygame.font.SysFont(FONT, 15, bold=True),
    "kmax": pygame.font.SysFont(FONT, 28, bold=True),
}

# ─────────────────────────────────────────────────────────────
# GAME LOGIC
# ─────────────────────────────────────────────────────────────

class Game:

    def __init__(self, rows, cols):

        self.rows = rows
        self.cols = cols

        self.board = {}
        self.history = []
        self.flash = {}

    def reset(self):

        self.board.clear()
        self.history.clear()
        self.flash.clear()

    def nbrs(self, r, c):

        out = []

        for dr in (-1,0,1):
            for dc in (-1,0,1):

                if dr == dc == 0:
                    continue

                nr, nc = r+dr, c+dc

                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    out.append((nr,nc))

        return out

    def nbr_sum(self, r, c):
        return sum(self.board[n] for n in self.nbrs(r,c) if n in self.board)

    def can_null(self, r, c):

        if (r,c) in self.board:
            return False

        return all(n not in self.board for n in self.nbrs(r,c))

    def can_non_null(self, r, c):

        if (r,c) in self.board:
            return False

        s = self.nbr_sum(r,c)

        if s < 2:
            return False

        vals = set(self.board.values())

        return all(k in vals for k in range(1,s))

    def place(self, r, c):

        if self.can_null(r,c):
            self._place(r,c,1)
            return True, 1

        if self.can_non_null(r,c):
            s = self.nbr_sum(r,c)
            self._place(r,c,s)
            return True, s

        if (r,c) in self.board:
            return False, "already occupied"

        s = self.nbr_sum(r,c)

        if s == 0:
            return False, "no neighbours"

        if s == 1:
            return False, "sum = 1 → use green cell"

        return False, "invalid move"

    def _place(self, r, c, d):

        self.board[(r,c)] = d
        self.history.append((r,c))
        self.flash[(r,c)] = time.perf_counter()

    def undo(self):

        if not self.history:
            return False

        cell = self.history.pop()

        self.board.pop(cell, None)
        self.flash.pop(cell, None)

        return True

    @property
    def kmax(self):
        return max(self.board.values(), default=0)

# ─────────────────────────────────────────────────────────────
# GRID LAYOUT
# ─────────────────────────────────────────────────────────────

class GridLayout:

    def __init__(self, sw, sh, rows, cols):

        aw = sw - 2*MARGIN
        ah = sh - HEADER_H - FOOTER_H - 2*MARGIN

        cs = min(
            (aw - (cols-1)*CELL_GAP)//cols,
            (ah - (rows-1)*CELL_GAP)//rows
        )

        self.cs = max(MIN_CELL, min(MAX_CELL, cs))

        gw = cols*self.cs + (cols-1)*CELL_GAP
        gh = rows*self.cs + (rows-1)*CELL_GAP

        self.ox = (sw-gw)//2
        self.oy = HEADER_H + MARGIN + (ah-gh)//2

    def rect(self, r, c):

        return pygame.Rect(
            self.ox + c*(self.cs + CELL_GAP),
            self.oy + r*(self.cs + CELL_GAP),
            self.cs,
            self.cs
        )

# ─────────────────────────────────────────────────────────────
# GAME SCREEN
# ─────────────────────────────────────────────────────────────

class GameScreen:

    def __init__(self, surf, rows, cols):

        self.surf = surf
        self.game = Game(rows, cols)
        self.layout = GridLayout(*surf.get_size(), rows, cols)

        self.msg = "Click a highlighted cell"
        self.msg_color = TEXT_DIM

        self.hover = None
        self.hints = True

    def draw(self):

        s = self.surf
        g = self.game
        L = self.layout

        s.fill(BG)

        frect(s, PANEL, pygame.Rect(0,0,s.get_width(),HEADER_H))

        title = fonts["header"].render("DENOMINATION", True, TEXT)
        s.blit(title, (24,16))

        k = fonts["kmax"].render(f"k = {g.kmax}", True, GOLD)
        s.blit(k, (s.get_width()-k.get_width()-24, 12))

        gw = g.cols*L.cs + (g.cols-1)*CELL_GAP
        gh = g.rows*L.cs + (g.rows-1)*CELL_GAP

        bg_rect = pygame.Rect(L.ox-16, L.oy-16, gw+32, gh+32)

        frect(s, PANEL2, bg_rect, 12)

        valid_null = {
            (r,c)
            for r in range(g.rows)
            for c in range(g.cols)
            if g.can_null(r,c)
        }

        valid_sum = {
            (r,c)
            for r in range(g.rows)
            for c in range(g.cols)
            if g.can_non_null(r,c)
        }

        for r in range(g.rows):
            for c in range(g.cols):

                rect = L.rect(r,c)

                cell = (r,c)
                d = g.board.get(cell)

                if d is not None:
                    fill = STONE[min(d, len(STONE)-1)]

                elif cell in valid_null:
                    fill = NULL_FILL

                elif cell in valid_sum:
                    fill = SUM_FILL

                elif cell == self.hover:
                    fill = CELL_HOVER

                else:
                    fill = CELL

                frect(s, fill, rect, 6)
                orect(s, CELL_BORDER, rect, 1, 6)

                if d is not None:

                    txt = "1★" if d == 1 else str(d)

                    label = fonts["cell_mid"].render(txt, True, TEXT)

                    s.blit(
                        label,
                        label.get_rect(center=rect.center)
                    )

                elif cell in valid_sum:

                    val = g.nbr_sum(r,c)

                    if val >= 2:
                        label = fonts["cell_mid"].render(
                            str(val),
                            True,
                            lighten(SUM_BORDER,0.2)
                        )

                        s.blit(
                            label,
                            label.get_rect(center=rect.center)
                        )

                elif cell in valid_null:

                    label = fonts["cell_mid"].render(
                        "★",
                        True,
                        lighten(NULL_BORDER,0.2)
                    )

                    s.blit(
                        label,
                        label.get_rect(center=rect.center)
                    )

        fy = s.get_height() - FOOTER_H

        frect(s, PANEL, pygame.Rect(0,fy,s.get_width(),FOOTER_H))

        status = fonts["status"].render(
            self.msg,
            True,
            self.msg_color
        )

        s.blit(status, status.get_rect(center=(s.get_width()//2, fy+22)))

        ctrl = fonts["ctrl"].render(
            "H hints   U undo   R restart   M menu   Q quit",
            True,
            TEXT_FAINT
        )

        s.blit(ctrl, ctrl.get_rect(center=(s.get_width()//2, fy+50)))

        pygame.display.flip()

    def handle(self, e):

        g = self.game
        L = self.layout

        if e.type == pygame.QUIT:
            return "quit"

        if e.type == pygame.KEYDOWN:

            if e.key in (pygame.K_q, pygame.K_ESCAPE):
                return "quit"

            if e.key == pygame.K_m:
                return "menu"

            if e.key == pygame.K_r:
                g.reset()

            if e.key == pygame.K_u:
                g.undo()

        if e.type == pygame.MOUSEMOTION:

            mx, my = e.pos

            self.hover = None

            for r in range(g.rows):
                for c in range(g.cols):

                    if L.rect(r,c).collidepoint(mx,my):
                        self.hover = (r,c)

        if e.type == pygame.MOUSEBUTTONDOWN:

            if e.button == 1 and self.hover:

                r,c = self.hover

                ok, val = g.place(r,c)

                if ok:
                    self.msg = f"Placed {val}"
                    self.msg_color = BLUE
                else:
                    self.msg = val
                    self.msg_color = RED

        return None

# ─────────────────────────────────────────────────────────────
# MENU SCREEN
# ─────────────────────────────────────────────────────────────

class MenuScreen:

    def __init__(self, surf):

        self.surf = surf

        self.presets = [
            (3,3), (4,4), (5,5),
            (6,6), (7,7), (8,8),
            (9,9), (10,10)
        ]

        self.buttons = []

        self.manual_rows = ""
        self.manual_cols = ""

        self.active_input = None

        # NEW
        self.error_msg = ""

    def draw(self):

        s = self.surf
        sw, sh = s.get_size()

        s.fill(BG)

        title = fonts["title"].render(
            "DENOMINATION",
            True,
            TEXT
        )

        s.blit(
            title,
            title.get_rect(center=(sw//2, 100))
        )

        sub = fonts["sub"].render(
            "a grid placement puzzle",
            True,
            TEXT_DIM
        )

        s.blit(
            sub,
            sub.get_rect(center=(sw//2, 145))
        )

        self.buttons.clear()

        start_y = 240

        for i, (r,c) in enumerate(self.presets):

            rect = pygame.Rect(
                sw//2 - 260 + (i%3)*190,
                start_y + (i//3)*90,
                150,
                60
            )

            self.buttons.append((rect, r, c))

            frect(s, PANEL2, rect, 10)
            orect(s, BLUE, rect, 2, 10)

            label = fonts["menu"].render(
                f"{r} × {c}",
                True,
                TEXT
            )

            s.blit(
                label,
                label.get_rect(center=rect.center)
            )

        # ─────────────────────────────────────────────────────
        # MANUAL ENTRY
        # ─────────────────────────────────────────────────────

        manual_y = 560

        label = fonts["menu"].render(
            "Manual grid size (max 10 × 10)",
            True,
            TEXT
        )

        s.blit(label, (sw//2 - 190, manual_y))

        row_box = pygame.Rect(
            sw//2 - 170,
            manual_y+40,
            90,
            44
        )

        col_box = pygame.Rect(
            sw//2 - 50,
            manual_y+40,
            90,
            44
        )

        play_box = pygame.Rect(
            sw//2 + 80,
            manual_y+40,
            120,
            44
        )

        for rect, txt, key in [
            (row_box, self.manual_rows, "rows"),
            (col_box, self.manual_cols, "cols")
        ]:

            active = self.active_input == key

            frect(
                s,
                PANEL2 if active else PANEL,
                rect,
                8
            )

            orect(
                s,
                BLUE if active else SEP,
                rect,
                2,
                8
            )

            text = fonts["menu"].render(
                txt or "0",
                True,
                TEXT
            )

            s.blit(
                text,
                text.get_rect(center=rect.center)
            )

        # PLAY BUTTON

        frect(s, BLUE, play_box, 8)

        play = fonts["play"].render(
            "PLAY",
            True,
            BG
        )

        s.blit(
            play,
            play.get_rect(center=play_box.center)
        )

        self.row_box = row_box
        self.col_box = col_box
        self.play_box = play_box

        # ─────────────────────────────────────────────────────
        # ERROR MESSAGE
        # ─────────────────────────────────────────────────────

        if self.error_msg:

            err = fonts["status"].render(
                self.error_msg,
                True,
                RED
            )

            s.blit(
                err,
                err.get_rect(center=(sw//2, sh-90))
            )

        ctrl = fonts["ctrl"].render(
            "Click preset or enter custom rows/cols",
            True,
            TEXT_FAINT
        )

        s.blit(
            ctrl,
            ctrl.get_rect(center=(sw//2, sh-40))
        )

        pygame.display.flip()

    def handle(self, e):

        if e.type == pygame.QUIT:
            return "quit"

        # ─────────────────────────────────────────────────────
        # MOUSE
        # ─────────────────────────────────────────────────────

        if e.type == pygame.MOUSEBUTTONDOWN:

            mx, my = e.pos

            # PRESET BUTTONS

            for rect, r, c in self.buttons:

                if rect.collidepoint(mx,my):

                    self.error_msg = ""
                    return r, c

            # INPUT BOXES

            if self.row_box.collidepoint(mx,my):
                self.active_input = "rows"

            elif self.col_box.collidepoint(mx,my):
                self.active_input = "cols"

            # PLAY BUTTON

            elif self.play_box.collidepoint(mx,my):

                try:

                    r = int(self.manual_rows)
                    c = int(self.manual_cols)

                    # VALID RANGE

                    if 2 <= r <= 10 and 2 <= c <= 10:

                        self.error_msg = ""
                        return r, c

                    else:

                        self.error_msg = (
                            "Grid size must be between 2 and 10"
                        )

                except:

                    self.error_msg = (
                        "Please enter valid integers"
                    )

        # ─────────────────────────────────────────────────────
        # KEYBOARD
        # ─────────────────────────────────────────────────────

        if e.type == pygame.KEYDOWN:

            if e.key in (pygame.K_ESCAPE, pygame.K_q):
                return "quit"

            if self.active_input:

                target = (
                    self.manual_rows
                    if self.active_input == "rows"
                    else self.manual_cols
                )

                if e.key == pygame.K_BACKSPACE:

                    target = target[:-1]

                elif e.unicode.isdigit() and len(target) < 2:

                    target += e.unicode

                if self.active_input == "rows":
                    self.manual_rows = target
                else:
                    self.manual_cols = target

        return None
# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():

    surf = pygame.display.set_mode((1100, 820), pygame.RESIZABLE)

    pygame.display.set_caption("Denomination")

    clock = pygame.time.Clock()

    state = "menu"

    menu = MenuScreen(surf)
    game = None

    running = True

    while running:

        for e in pygame.event.get():

            if state == "menu":

                result = menu.handle(e)

                if result == "quit":
                    running = False

                elif isinstance(result, tuple):

                    rows, cols = result

                    game = GameScreen(surf, rows, cols)

                    state = "game"

            elif state == "game":

                result = game.handle(e)

                if result == "quit":
                    running = False

                elif result == "menu":
                    menu = MenuScreen(surf)
                    state = "menu"

        if running:

            if state == "menu":
                menu.draw()
            else:
                game.draw()

        clock.tick(60)

    pygame.quit()
    os._exit(0)

if __name__ == "__main__":
    main()