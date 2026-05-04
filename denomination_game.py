"""
denomination_game.py
====================
Interactive implementation of the Denomination puzzle using pygame.

Rules
-----
Null stone   (denomination 1): placed on cell v only if ALL king-graph
             neighbours of v are currently empty. Denomination 1 can
             ONLY appear as a null stone — it is never produced by the
             neighbourhood-sum rule.
Non-null stone (denomination k > 1): placed on empty cell v when
             (a) the sum of denominations of v's already-placed
                 neighbours equals exactly k, and
             (b) denominations 1, 2, …, k-1 all exist on the grid.
Objective: maximise k_max, the highest denomination placed.

Controls (in-game)
------------------
  Left-click          Select / deselect a cell
  N                   Place a null stone on the selected cell
  Space / Enter       Place a non-null stone on the selected cell
  H                   Toggle hint overlay
  U                   Undo last move
  R                   Reset board
  M                   Return to main menu
  Q / Escape          Quit

Usage
-----
  pip install pygame
  python denomination_game.py
"""

import sys
import math
import time
import pygame

# ---------------------------------------------------------------------------
# Colour palette  (dark studio theme)
# ---------------------------------------------------------------------------
C_BG        = ( 15,  17,  23)   # page background
C_SURFACE   = ( 24,  28,  38)   # card / panel background
C_BORDER    = ( 44,  52,  70)   # subtle border
C_CELL      = ( 32,  37,  50)   # empty cell fill
C_HOVER     = ( 45,  54,  76)   # hovered cell
C_SELECT    = ( 38,  70, 118)   # selected cell
C_H_NULL    = ( 28,  68,  50)   # hint: valid null
C_H_SUM     = ( 68,  58,  22)   # hint: valid non-null
C_ACCENT    = ( 99, 179, 237)   # blue accent
C_GOLD      = (236, 201,  75)   # gold / kmax display
C_MINT      = ( 72, 199, 142)   # mint / success
C_ERROR     = (248, 114, 114)   # error red
C_WHITE     = (238, 243, 250)   # primary text
C_GREY      = (108, 118, 140)   # secondary text
C_DARK      = ( 52,  60,  78)   # muted text / disabled

# Stone colours indexed by denomination  (index 0 unused)
STONE_C = [
    None,
    ( 85,  93, 112),   # 1  slate  (null)
    (228, 172,  48),   # 2  gold
    (208,  92,  68),   # 3  terracotta
    ( 66, 176, 108),   # 4  emerald
    ( 56, 152, 208),   # 5  azure
    (142,  88, 218),   # 6  violet
    (222,  78, 128),   # 7  rose
    ( 68, 202, 182),   # 8  teal
    (232, 132,  52),   # 9  amber
]


def stone_color(d):
    if not d:
        return C_CELL
    return STONE_C[min(d, len(STONE_C) - 1)]


def text_color_for(bg):
    """Return white or dark text depending on background luminance."""
    L = bg[0] * 0.299 + bg[1] * 0.587 + bg[2] * 0.114
    return C_WHITE if L < 140 else C_BG


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------------------
# King-graph helper
# ---------------------------------------------------------------------------

def king_neighbours(r, c, m, n):
    """All king-graph neighbours of (r, c) on an m×n grid (0-indexed)."""
    return [(r + dr, c + dc)
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr, dc) != (0, 0) and 0 <= r + dr < m and 0 <= c + dc < n]


# ---------------------------------------------------------------------------
# Game logic
# ---------------------------------------------------------------------------

class DenominationGame:
    def __init__(self, m, n):
        self.m = m
        self.n = n
        self.reset()

    def reset(self):
        self.board   = {}     # (r, c) → denomination (int ≥ 1)
        self.history = []     # list of (r, c) for undo
        self._set_msg("Select a cell, then press N for a null stone.", C_GREY)

    def _set_msg(self, text, color):
        self.msg_text  = text
        self.msg_color = color

    # -- neighbour helpers ---------------------------------------------------

    def neighbours(self, r, c):
        return king_neighbours(r, c, self.m, self.n)

    def placed_neighbour_sum(self, r, c):
        return sum(self.board[nb] for nb in self.neighbours(r, c)
                   if nb in self.board)

    # -- validity ------------------------------------------------------------

    def can_place_null(self, r, c):
        """Null stone: cell empty and ALL neighbours empty."""
        if (r, c) in self.board:
            return False
        return all(nb not in self.board for nb in self.neighbours(r, c))

    def can_place_non_null(self, r, c):
        """Non-null stone: sum ≥ 2 and all 1..sum-1 present on board."""
        if (r, c) in self.board:
            return False
        s = self.placed_neighbour_sum(r, c)
        if s < 2:
            return False
        present = set(self.board.values())
        return all(k in present for k in range(1, s))

    def valid_null_cells(self):
        return {(r, c) for r in range(self.m) for c in range(self.n)
                if self.can_place_null(r, c)}

    def valid_non_null_cells(self):
        return {(r, c) for r in range(self.m) for c in range(self.n)
                if self.can_place_non_null(r, c)}

    # -- actions -------------------------------------------------------------

    def place_null(self, r, c):
        if not self.can_place_null(r, c):
            self._set_msg(
                "Invalid: all neighbours of the cell must be empty for a null stone.",
                C_ERROR)
            return False
        self.board[(r, c)] = 1
        self.history.append((r, c))
        self._set_msg(f"Null stone (1★) placed at ({r+1}, {c+1}).", C_MINT)
        return True

    def place_non_null(self, r, c):
        if (r, c) in self.board:
            self._set_msg("That cell is already occupied.", C_ERROR)
            return False
        s = self.placed_neighbour_sum(r, c)
        if s == 0:
            self._set_msg("No placed neighbours — neighbourhood sum is 0.", C_ERROR)
            return False
        if s == 1:
            self._set_msg(
                "Sum = 1: denomination 1 may only be placed as a null stone (press N).",
                C_ERROR)
            return False
        present = set(self.board.values())
        missing = [k for k in range(1, s) if k not in present]
        if missing:
            self._set_msg(
                f"Cannot place {s}: denomination {missing[0]} must appear first.",
                C_ERROR)
            return False
        self.board[(r, c)] = s
        self.history.append((r, c))
        self._set_msg(
            f"Placed denomination {s} at ({r+1}, {c+1}).  k_max = {self.kmax}",
            C_ACCENT)
        return True

    def undo(self):
        if not self.history:
            self._set_msg("Nothing to undo.", C_ERROR)
            return
        cell = self.history.pop()
        d    = self.board.pop(cell)
        self._set_msg(
            f"Undone: removed denomination {d} from ({cell[0]+1}, {cell[1]+1}).",
            C_GREY)

    @property
    def kmax(self):
        return max(self.board.values(), default=0)

    def is_stuck(self):
        return (bool(self.board)
                and not self.valid_null_cells()
                and not self.valid_non_null_cells())


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def rrect(surf, color, rect, radius=10):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def rrect_border(surf, color, rect, width=1, radius=10):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)


def blit_text(surf, font, text, color, pos, anchor="center"):
    s = font.render(text, True, color)
    r = s.get_rect()
    setattr(r, anchor, pos)
    surf.blit(s, r)
    return r


# ---------------------------------------------------------------------------
# Menu / start screen
# ---------------------------------------------------------------------------

def run_menu(screen):
    """Show grid-size selection screen. Returns (m, n) or raises SystemExit."""
    W, H   = screen.get_size()
    clock  = pygame.time.Clock()
    t0     = time.time()

    F_title = pygame.font.SysFont("Georgia",      48, bold=True)
    F_sub   = pygame.font.SysFont("Trebuchet MS", 18)
    F_label = pygame.font.SysFont("Trebuchet MS", 15, bold=True)
    F_inp   = pygame.font.SysFont("Courier New",  30, bold=True)
    F_small = pygame.font.SysFont("Trebuchet MS", 13)
    F_btn   = pygame.font.SysFont("Trebuchet MS", 19, bold=True)

    fields  = {"m": "3", "n": "3"}
    focus   = "m"
    presets = [(2, 2), (2, 3), (3, 3), (3, 4), (4, 4), (4, 5), (5, 5)]
    err     = ""

    def parse():
        try:
            m, n = int(fields["m"]), int(fields["n"])
            if not (1 <= m <= 9 and 1 <= n <= 9):
                return None, "Dimensions must be between 1 and 9."
            return (m, n), ""
        except ValueError:
            return None, "Please enter a single digit for each dimension."

    while True:
        t  = time.time() - t0
        mx, my = pygame.mouse.get_pos()

        # -- events --
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.VIDEORESIZE:
                W, H   = event.w, event.h
                screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit(0)
                elif event.key == pygame.K_TAB:
                    focus = "n" if focus == "m" else "m"
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    mn, err = parse()
                    if mn:
                        return mn
                elif event.key == pygame.K_BACKSPACE:
                    fields[focus] = fields[focus][:-1]
                elif event.unicode.isdigit() and len(fields[focus]) < 1:
                    fields[focus] += event.unicode
                    err = ""

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Click on input boxes
                for key, (fx, fy) in [("m", (W // 2 - 85, H // 2 - 5)),
                                       ("n", (W // 2 + 85, H // 2 - 5))]:
                    if abs(mx - fx) < 46 and abs(my - fy) < 30:
                        focus = key

                # Click on presets
                for i, (pm, pn) in enumerate(presets):
                    bx = W // 2 - 198 + i * 66
                    by = H // 2 + 100
                    if abs(mx - bx) < 28 and abs(my - by) < 17:
                        fields["m"], fields["n"] = str(pm), str(pn)
                        err = ""

                # Click PLAY button
                play_y = H // 2 + 168
                if abs(mx - W // 2) < 88 and abs(my - play_y) < 24:
                    mn, err = parse()
                    if mn:
                        return mn

        # -- draw --
        screen.fill(C_BG)

        # Soft hexagonal dot pattern (static — no lag)
        for xi in range(0, W + 50, 48):
            for yi in range(0, H + 50, 48):
                alpha = 0.04 + 0.03 * math.sin(t * 0.8 + xi * 0.04 + yi * 0.04)
                c = lerp(C_BG, C_BORDER, alpha)
                pygame.draw.circle(screen, c, (xi, yi), 1)

        # Card
        CW, CH = 500, 460
        cx, cy = (W - CW) // 2, (H - CH) // 2
        card_surf = pygame.Surface((CW, CH), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, (*C_SURFACE, 245), (0, 0, CW, CH), border_radius=18)
        pygame.draw.rect(card_surf, (*C_BORDER, 180), (0, 0, CW, CH), 1, border_radius=18)
        screen.blit(card_surf, (cx, cy))

        # Title
        blit_text(screen, F_title, "Denomination", C_WHITE, (W // 2, cy + 58))

        # Animated underline
        aw = int(160 + 18 * math.sin(t * 1.4))
        pygame.draw.rect(screen, C_GOLD,
                         (W // 2 - aw // 2, cy + 93, aw, 3), border_radius=2)

        blit_text(screen, F_sub, "A Grid Placement Puzzle", C_GREY,
                  (W // 2, cy + 116))

        # Grid size label
        blit_text(screen, F_label, "CHOOSE GRID SIZE", C_ACCENT,
                  (W // 2, cy + 172))

        # Input boxes
        for key, label, bx in [("m", "Rows", W // 2 - 85),
                                 ("n", "Cols", W // 2 + 85)]:
            is_f = (focus == key)
            box  = pygame.Rect(bx - 44, cy + 194, 88, 52)
            rrect(screen, C_CELL, box, radius=10)
            rrect_border(screen, C_ACCENT if is_f else C_BORDER,
                         box, width=2, radius=10)

            val = fields[key] + ("|" if is_f and int(t * 2) % 2 == 0 else "")
            blit_text(screen, F_inp, val, C_WHITE, box.center)
            blit_text(screen, F_small, label, C_GREY,
                      (bx, cy + 254))

        blit_text(screen, F_title, "×", C_DARK, (W // 2, cy + 219))

        # Preset buttons
        blit_text(screen, F_small, "Quick presets:", C_GREY,
                  (cx + 30, cy + 285), anchor="midleft")
        for i, (pm, pn) in enumerate(presets):
            bx = W // 2 - 198 + i * 66
            by = cy + 305
            active = fields["m"] == str(pm) and fields["n"] == str(pn)
            br = pygame.Rect(bx - 26, by - 15, 52, 30)
            rrect(screen, C_BG if not active else C_SELECT, br, radius=7)
            rrect_border(screen, C_ACCENT if active else C_DARK, br,
                         width=1, radius=7)
            blit_text(screen, F_small, f"{pm}×{pn}",
                      C_ACCENT if active else C_GREY, (bx, by))

        # Error
        if err:
            blit_text(screen, F_small, err, C_ERROR, (W // 2, cy + 345))

        # PLAY button
        pulse = 0.93 + 0.07 * math.sin(t * 2.2)
        bw    = int(174 * pulse)
        bh    = int(46 * pulse)
        pb    = pygame.Rect(W // 2 - bw // 2, cy + 380 - bh // 2, bw, bh)
        bc    = lerp(C_ACCENT, (140, 210, 255), 0.25 + 0.25 * math.sin(t * 2))
        rrect(screen, bc, pb, radius=11)
        blit_text(screen, F_btn, "PLAY", C_BG, pb.center)

        # Tab hint
        blit_text(screen, F_small, "Tab  switch fields  ·  Enter  play",
                  C_DARK, (W // 2, cy + 438))

        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# In-game renderer
# ---------------------------------------------------------------------------

PANEL_H  = 110
MARGIN   = 28
MIN_CS   = 58
MAX_CS   = 110


class GameScreen:
    def __init__(self, screen, m, n):
        self.screen = screen
        self.game   = DenominationGame(m, n)
        self.sel    = None
        self.hints  = False
        self._init_fonts()
        self._layout()

    def _init_fonts(self):
        self.F_num   = pygame.font.SysFont("Georgia",       26, bold=True)
        self.F_coord = pygame.font.SysFont("Courier New",   11)
        self.F_panel = pygame.font.SysFont("Trebuchet MS",  17, bold=True)
        self.F_kmax  = pygame.font.SysFont("Georgia",       32, bold=True)
        self.F_ctrl  = pygame.font.SysFont("Trebuchet MS",  12)
        self.F_small = pygame.font.SysFont("Trebuchet MS",  14)

    def _layout(self):
        W, H  = self.screen.get_size()
        g     = self.game
        avail_w = W - 2 * MARGIN
        avail_h = H - PANEL_H - 2 * MARGIN - 32
        cs = max(MIN_CS, min(MAX_CS, avail_w // g.n, avail_h // g.m))
        self.cs = cs
        gw = cs * g.n
        gh = cs * g.m
        self.ox = (W - gw) // 2
        self.oy = MARGIN + 32 + (avail_h - gh) // 2

    def _cell_rect(self, r, c):
        pad = 4
        return pygame.Rect(
            self.ox + c * self.cs + pad,
            self.oy + r * self.cs + pad,
            self.cs - 2 * pad,
            self.cs - 2 * pad)

    def _cell_at(self, px, py):
        c = (px - self.ox) // self.cs
        r = (py - self.oy) // self.cs
        if 0 <= r < self.game.m and 0 <= c < self.game.n:
            return (r, c)
        return None

    # -- draw ----------------------------------------------------------------

    def _draw_cell(self, r, c, hover, hn, hnn):
        rect  = self._cell_rect(r, c)
        cell  = (r, c)
        g     = self.game
        d     = g.board.get(cell)

        # Fill
        if d is not None:
            fill = stone_color(d)
        elif cell == self.sel:
            fill = C_SELECT
        elif cell in hn:
            fill = C_H_NULL
        elif cell in hnn:
            fill = C_H_SUM
        elif cell == hover:
            fill = C_HOVER
        else:
            fill = C_CELL

        # Shadow for placed stones
        if d is not None:
            sr = rect.move(3, 3)
            pygame.draw.rect(self.screen, (0, 0, 0), sr, border_radius=9)

        rrect(self.screen, fill, rect, radius=9)

        # Border
        if cell == self.sel:
            rrect_border(self.screen, C_ACCENT, rect, 2, radius=9)
        elif d is not None:
            hi_col = lerp(fill, C_WHITE, 0.22)
            rrect_border(self.screen, hi_col, rect, 1, radius=9)
        else:
            rrect_border(self.screen, C_BORDER, rect, 1, radius=9)

        # Highlight stripe (top edge glow on placed stones)
        if d is not None:
            glow_r = pygame.Rect(rect.x + 5, rect.y + 5,
                                  rect.w - 10, max(4, rect.h // 4))
            glow_c = lerp(fill, C_WHITE, 0.28)
            rrect(self.screen, glow_c, glow_r, radius=5)

        # Label
        if d is not None:
            label = "1★" if d == 1 else str(d)
            blit_text(self.screen, self.F_num, label,
                      text_color_for(fill), rect.center)
        elif self.hints:
            if cell in hnn:
                s = g.placed_neighbour_sum(r, c)
                blit_text(self.screen, self.F_small, str(s), C_GOLD, rect.center)
            elif cell in hn:
                blit_text(self.screen, self.F_small, "N", C_MINT, rect.center)

        # Coordinate micro-label
        co = self.F_coord.render(f"{r+1},{c+1}", True, C_DARK)
        self.screen.blit(co, (rect.x + 4, rect.y + 4))

    def _draw_panel(self):
        W, H = self.screen.get_size()
        g    = self.game
        py   = H - PANEL_H

        # Panel background
        panel_r = pygame.Rect(0, py, W, PANEL_H)
        pygame.draw.rect(self.screen, C_SURFACE, panel_r)
        pygame.draw.line(self.screen, C_BORDER, (0, py), (W, py))

        # k_max
        km     = g.kmax
        km_col = C_GOLD if km >= 4 else (C_MINT if km >= 2 else C_GREY)
        blit_text(self.screen, self.F_kmax, f"k_max = {km}", km_col,
                  (72, py + 32))

        # Cells used
        blit_text(self.screen, self.F_ctrl,
                  f"{g.m}×{g.n} grid  ·  {len(g.board)}/{g.m*g.n} cells placed",
                  C_GREY, (72, py + 60))

        # Status message
        blit_text(self.screen, self.F_panel, g.msg_text, g.msg_color,
                  (W // 2, py + 28))

        # Stuck notice
        if g.is_stuck():
            blit_text(self.screen, self.F_panel,
                      "● No more valid moves — game over",
                      C_GOLD, (W // 2, py + 58))

        # Controls
        ctrl = ("N  null stone     Space/Enter  place     "
                "H  hints     U  undo     R  reset     M  menu     Q  quit")
        blit_text(self.screen, self.F_ctrl, ctrl, C_DARK, (W // 2, py + 90))

        # Hint indicator
        hc = C_MINT if self.hints else C_DARK
        pygame.draw.circle(self.screen, hc, (W - 36, py + 28), 6)
        blit_text(self.screen, self.F_ctrl, "hints", hc, (W - 66, py + 28))

    def _draw_title(self):
        W, _ = self.screen.get_size()
        blit_text(self.screen, self.F_panel, "DENOMINATION", C_ACCENT,
                  (W // 2, 16))

    def draw(self, hover_pos):
        g      = self.game
        hover  = self._cell_at(*hover_pos)
        hn     = g.valid_null_cells()     if self.hints else set()
        hnn    = g.valid_non_null_cells() if self.hints else set()

        self.screen.fill(C_BG)

        # Grid card background
        pad   = 8
        gr    = pygame.Rect(self.ox - pad, self.oy - pad,
                            g.n * self.cs + 2 * pad,
                            g.m * self.cs + 2 * pad)
        rrect(self.screen, C_SURFACE, gr, radius=14)
        rrect_border(self.screen, C_BORDER, gr, 1, radius=14)

        self._draw_title()
        for r in range(g.m):
            for c in range(g.n):
                self._draw_cell(r, c, hover, hn, hnn)
        self._draw_panel()

        pygame.display.flip()

    # -- event handling ------------------------------------------------------

    def handle(self, event):
        """
        Process one pygame event.
        Returns 'quit', 'menu', or None.
        """
        g = self.game

        if event.type == pygame.QUIT:
            return "quit"

        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode(
                (event.w, event.h), pygame.RESIZABLE)
            self._layout()

        if event.type == pygame.KEYDOWN:
            k = event.key

            if k in (pygame.K_q, pygame.K_ESCAPE):
                return "quit"
            if k == pygame.K_m:
                return "menu"
            if k == pygame.K_r:
                g.reset()
                self.sel = None
            if k == pygame.K_h:
                self.hints = not self.hints
            if k == pygame.K_u:
                g.undo()
                self.sel = None
            if k == pygame.K_n and self.sel:
                g.place_null(*self.sel)
                self.sel = None
            if k in (pygame.K_RETURN, pygame.K_SPACE) and self.sel:
                g.place_non_null(*self.sel)
                self.sel = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._cell_at(*event.pos)
            if cell:
                r, c = cell
                if self.sel == cell:
                    self.sel = None
                    g._set_msg("Cell deselected.", C_GREY)
                else:
                    self.sel = cell
                    d = g.board.get(cell)
                    if d is not None:
                        lbl = "null stone (1★)" if d == 1 else f"denomination {d}"
                        g._set_msg(f"({r+1},{c+1}) holds {lbl}.", C_GREY)
                    elif g.can_place_null(r, c):
                        g._set_msg(
                            f"({r+1},{c+1}) — press N to place a null stone.",
                            C_MINT)
                    elif g.can_place_non_null(r, c):
                        s = g.placed_neighbour_sum(r, c)
                        g._set_msg(
                            f"({r+1},{c+1}) — press Space to place denomination {s}.",
                            C_ACCENT)
                    else:
                        s = g.placed_neighbour_sum(r, c)
                        g._set_msg(
                            f"({r+1},{c+1}) — not a valid placement (sum = {s}).",
                            C_ERROR)

        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pygame.init()
    pygame.font.init()

    W, H = 900, 700
    screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
    pygame.display.set_caption("Denomination Puzzle")

    # Simple programmatic icon
    icon = pygame.Surface((32, 32))
    icon.fill(C_SURFACE)
    pygame.draw.rect(icon, C_GOLD, (8, 8, 16, 16), border_radius=4)
    pygame.display.set_icon(icon)

    clock = pygame.time.Clock()

    while True:
        # --- menu ---
        mn = run_menu(screen)          # returns (m, n)  or raises SystemExit
        m, n = mn

        gs = GameScreen(screen, m, n)

        # --- game loop ---
        while True:
            for event in pygame.event.get():
                action = gs.handle(event)
                if action == "quit":
                    pygame.quit()
                    sys.exit(0)
                if action == "menu":
                    break           # go back to outer while → run_menu
            else:
                gs.draw(pygame.mouse.get_pos())
                clock.tick(60)
                continue
            break                   # inner for-loop was broken → go to menu


if __name__ == "__main__":
    main()
