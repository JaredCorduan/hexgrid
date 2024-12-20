import argparse
import os
import re

import pygame

COLOR_SQUARE_SIZE = 20
COLOR_SQUARE_SPACE = 3

BUTTON_WIDTH = 80
BUTTON_HEIGHT = 30

COLOR_BUTTONS_X_OFFSET = 150
COLOR_Y = 50

PALLET_BUTTONS_X_OFFSET = 15
PALLET_Y = 200

CLEAR_BUTTON_Y = 700
CLEAR_BUTTON_OFFSET_X = 100
SAVE_BUTTON_SPACING_X = 20


GRAY = (150, 150, 150)
BLACK = (0, 0, 0)
BLUE = (6 * 16, 8 * 16, 14 * 16)

FONT_SIZE = 24
ROOT_THREE = 0.866


class HexMapper:
    #       S
    #      _____
    #     /    |\
    #    /     |_\
    #    \     | /
    #     \____|/
    #
    #
    #    This is a 30-60-90 triangle
    #
    #     |\
    #  dy | \ S
    #     |  \
    #     ----
    #      dx = S / 2
    #
    # dy = (√3)h / 2
    #
    #
    #    A _____ B
    #     /     \
    #  F /       \ C
    #    \       /
    #     \_____/
    #     E     D

    def __init__(self, x0, y0, side_len, radius, default_color):
        self.x0 = x0
        self.y0 = y0
        self.side_len = side_len
        self.radius = radius
        self.default_color = default_color
        self.dx = side_len // 2
        self.dy = int(side_len * ROOT_THREE)  # (√3)h / 2

        self.colors = {}

    def clear(self):
        self.colors = {}

    def to_polygon(self, hx, hy):
        x = self.x0 + (hx * (self.side_len + self.dx))
        y = self.y0 + (hy * 2 * self.dy) + (hx * self.dy)

        s = self.side_len
        dx = self.dx
        dy = self.dy

        # The labels below (in comments) refer to the diagram above,
        # ie the points of the hexagon.
        return [
            (x, y),  # A
            (x + s, y),  # B
            (x + s + dx, y + dy),  # C
            (x + s, y + 2 * dy),  # D
            (x, y + 2 * dy),  # E
            (x - dx, y + dy),  # F
        ]

    def get_polygon(self, x, y):
        r"""
        This isn't perfect.
        It grabs as though the hex
        where the following square
            _____
           /|    \ |
          / | X   \|
          \ |     /|
           \|___ / |

        """
        x1 = x - self.x0
        y1 = y - self.y0
        hx = x1 // (self.side_len + self.dx)
        hy = (y1 - (hx * self.dy)) // (2 * self.dy)
        return hx, hy

    def draw_hex(self, x, y, surf, col):
        pts = self.to_polygon(x, y)
        pygame.draw.polygon(surf, col, pts)

    def draw_hex_outline(self, x, y, surf, col):
        pts = self.to_polygon(x, y)
        pygame.draw.lines(surf, col, closed=True, points=pts, width=3)

    def draw(self, surf):
        for x in range(-self.radius, self.radius + 1):
            for y in range(-self.radius, self.radius + 1):
                if abs(x + y) > self.radius:
                    continue
                c = self.colors.get((x, y))
                if c is None:
                    c = self.default_color
                self.draw_hex(x, y, surf, c)
                self.draw_hex_outline(x, y, surf, BLACK)

    def poke(self, pt, color):
        x, y = self.get_polygon(pt[0], pt[1])
        if abs(x) <= self.radius and abs(y) <= self.radius and abs(x + y) <= self.radius:
            self.colors[(x, y)] = color


class Button:
    def __init__(self, rect, text, font, color=GRAY, clicked=BLUE, text_spacing=4):
        self.rect = rect
        self.text = text
        self.font = font
        self.color = color
        self.color_clicked = clicked
        self.text_spacing = text_spacing

        self.is_clicked = False

    def was_clicked(self, pt):
        wc = self.rect.collidepoint(pt)
        if wc:
            self.is_clicked = True
        return wc

    def unclick(self):
        self.is_clicked = False

    def draw(self, surf):
        c = self.color_clicked if self.is_clicked else self.color
        pygame.draw.rect(surf, c, self.rect)
        text = self.font.render(self.text, True, BLACK)
        surf.blit(text, (self.rect.x + self.text_spacing, self.rect.y + self.text_spacing))


class Pallet:
    def __init__(self, x0, y0, font):
        self.idx = 0
        self.set_color = "green"
        self.selected_color = None
        self.selected_box = None

        self.rects = {}
        w = COLOR_SQUARE_SIZE + COLOR_SQUARE_SPACE

        button_spacing = 5
        bws = BUTTON_WIDTH + button_spacing
        below_rects = y0 + w * 16 + COLOR_SQUARE_SPACE

        bx = x0 + PALLET_BUTTONS_X_OFFSET

        self.less_button = Button(pygame.Rect(bx + 0 * bws, below_rects, BUTTON_WIDTH, BUTTON_HEIGHT), "less g", font)
        self.more_button = Button(pygame.Rect(bx + 1 * bws, below_rects, BUTTON_WIDTH, BUTTON_HEIGHT), "more g", font)
        self.axis_button = Button(pygame.Rect(bx + 2 * bws, below_rects, BUTTON_WIDTH, BUTTON_HEIGHT), "axis g", font)
        self.reset_button = Button(pygame.Rect(bx + 3 * bws, below_rects, BUTTON_WIDTH, BUTTON_HEIGHT), "reset", font)

        self.rect_to_coord = {}

        for i in range(16):
            for j in range(16):
                r = pygame.Rect(x0 + i * w, y0 + j * w, COLOR_SQUARE_SIZE, COLOR_SQUARE_SIZE)
                self.rects[(i, j)] = r
                self.rect_to_coord[(r.x, r.y)] = (i, j)

    def get_color(self, i, j, k):
        if self.set_color == "green":
            return (i * 16, k, j * 16)
        if self.set_color == "red":
            return (k, i * 16, j * 16)
        if self.set_color == "blue":
            return (i * 16, j * 16, k)
        msg = "error in get_color"
        raise RuntimeError(msg)

    def set_button_text(self, letter):
        self.less_button.text = f"less {letter}"
        self.more_button.text = f"more {letter}"
        self.axis_button.text = f"axis {letter}"

    def change_set_color(self):
        if self.set_color == "green":
            self.set_color = "red"
            self.set_button_text("r")
        elif self.set_color == "red":
            self.set_color = "blue"
            self.set_button_text("b")
        elif self.set_color == "blue":
            self.set_color = "green"
            self.set_button_text("g")
        else:
            msg = "error in change_set_color"
            raise RuntimeError(msg)

    @property
    def k(self):
        return self.idx * 16

    def poke(self, pt):
        last_idx_x = 15

        if self.less_button.was_clicked(pt) and self.idx > 0:
            self.idx -= 1
        elif self.more_button.was_clicked(pt) and self.idx < last_idx_x:
            self.idx += 1
        elif self.axis_button.was_clicked(pt):
            self.change_set_color()
        elif self.reset_button.was_clicked(pt):
            self.idx = 1
        else:
            for r in self.rects.values():
                if r.collidepoint(pt):
                    i, j = self.rect_to_coord[(r.x, r.y)]
                    self.selected_color = self.get_color(i, j, self.k)
                    self.selected_box = (i, j)
                    break

    def unclick(self):
        self.less_button.unclick()
        self.more_button.unclick()
        self.axis_button.unclick()
        self.reset_button.unclick()

    def draw(self, surf):
        for (i, j), r in self.rects.items():
            c = self.get_color(i, j, self.k)
            pygame.draw.rect(surf, c, r)
            if self.selected_box == (i, j):
                pygame.draw.rect(surf, GRAY, r, width=2)

        self.less_button.draw(surf)
        self.axis_button.draw(surf)
        self.more_button.draw(surf)
        self.reset_button.draw(surf)


def starting_colors():
    colors = {}
    for i in range(16):
        for j in range(4):
            colors[(i, j)] = (160, 160, 160)
    colors[(0, 0)] = (26, 19, 52)
    colors[(1, 0)] = (38, 41, 74)
    colors[(2, 0)] = (1, 84, 90)
    colors[(3, 0)] = (1, 115, 81)
    colors[(4, 0)] = (3, 195, 131)
    colors[(5, 0)] = (170, 217, 98)
    colors[(6, 0)] = (251, 191, 69)
    colors[(7, 0)] = (239, 106, 50)
    colors[(8, 0)] = (237, 3, 69)
    colors[(9, 0)] = (161, 42, 94)
    colors[(10, 0)] = (113, 1, 98)
    colors[(11, 0)] = (2, 44, 125)

    colors[(15, 0)] = BLUE

    colors[(0, 1)] = (84, 48, 5)
    colors[(1, 1)] = (140, 81, 10)
    colors[(2, 1)] = (191, 129, 45)
    colors[(3, 1)] = (223, 194, 125)
    colors[(4, 1)] = (246, 232, 195)
    colors[(5, 1)] = (245, 245, 245)
    colors[(6, 1)] = (199, 234, 229)
    colors[(7, 1)] = (128, 205, 193)
    colors[(8, 1)] = (53, 151, 143)
    colors[(9, 1)] = (1, 102, 94)
    colors[(10, 1)] = (0, 60, 48)

    colors[(0, 2)] = (158, 1, 66)
    colors[(1, 2)] = (213, 62, 79)
    colors[(2, 2)] = (244, 109, 67)
    colors[(3, 2)] = (253, 174, 97)
    colors[(4, 2)] = (254, 224, 139)
    colors[(5, 2)] = (230, 245, 152)
    colors[(6, 2)] = (171, 221, 164)
    colors[(7, 2)] = (102, 194, 165)
    colors[(8, 2)] = (50, 136, 189)
    colors[(9, 2)] = (94, 79, 162)

    colors[(0, 3)] = (247, 252, 253)
    colors[(1, 3)] = (224, 236, 244)
    colors[(2, 3)] = (191, 211, 230)
    colors[(3, 3)] = (158, 188, 218)
    colors[(4, 3)] = (140, 150, 198)
    colors[(5, 3)] = (140, 107, 177)
    colors[(6, 3)] = (136, 65, 157)
    colors[(7, 3)] = (129, 15, 124)
    colors[(8, 3)] = (77, 0, 75)

    colors[(11, 3)] = (85, 34, 51)
    colors[(12, 3)] = (187, 68, 68)
    colors[(13, 3)] = (187, 170, 68)
    colors[(14, 3)] = (136, 168, 147)
    colors[(15, 3)] = (118, 89, 65)
    return colors


class Colors:
    def __init__(self, x0, y0, font):
        self.colors = starting_colors()

        self.selected_color = self.colors[(0, 0)]
        self.selected_box = (0, 0)

        self.rects = {}
        w = COLOR_SQUARE_SIZE + COLOR_SQUARE_SPACE

        self.rect_to_coord = {}

        cols = 16
        rows = 4
        for i in range(cols):
            for j in range(rows):
                r = pygame.Rect(x0 + i * w, y0 + j * w, COLOR_SQUARE_SIZE, COLOR_SQUARE_SIZE)
                self.rects[(i, j)] = r
                self.rect_to_coord[(r.x, r.y)] = (i, j)

        below_rects = y0 + w * rows + COLOR_SQUARE_SPACE

        self.mutate = False
        self.set_button = Button(
            pygame.Rect(x0 + COLOR_BUTTONS_X_OFFSET, below_rects, BUTTON_WIDTH, BUTTON_HEIGHT), "frozen", font
        )

    def freeze(self):
        self.mutate = False
        self.set_button.text = "frozen"

    def flip(self):
        if self.mutate:
            self.set_button.text = "frozen"
        else:
            self.set_button.text = "unfrozen"
        self.mutate = not self.mutate

    def poke(self, pt, color):
        if self.set_button.was_clicked(pt):
            self.flip()
        else:
            for r in self.rects.values():
                if r.collidepoint(pt):
                    i, j = self.rect_to_coord[(r.x, r.y)]
                    if self.mutate:
                        self.colors[(i, j)] = color
                    self.selected_color = self.colors[(i, j)]
                    self.selected_box = (i, j)
                    self.freeze()
                    break

    def unclick(self):
        self.set_button.unclick()

    def draw(self, surf):
        for (i, j), r in self.rects.items():
            c = self.colors[(i, j)]
            pygame.draw.rect(surf, c, r)
            if self.selected_box == (i, j):
                pygame.draw.rect(surf, GRAY, r, width=2)

        self.set_button.draw(surf)


def image_numbers(fs):
    hm = re.compile(r"hexgrid_(\d\d\d)\.png")
    for f in fs:
        match = hm.match(f)
        if match:
            yield int(match[1])


def get_screenshot_filename():
    files = os.listdir()

    nums = list(image_numbers(files))
    next_num = max(nums) + 1 if nums else 0
    return f"hexgrid_{next_num:03}.png"


def draw_all(surf, things):
    [x.draw(surf) for x in things]


def run(hex_side_len, screen_width, screen_height):
    tools_width = 16 * (20 + 3)
    tools_start_x = screen_width - (tools_width + 20)
    non_tools_rect = (0, 0, tools_start_x, screen_height)

    hexgrid_hexes_x = tools_start_x // (2 * hex_side_len)
    hexgrid_hexes_y = screen_height // (hex_side_len * ROOT_THREE)
    hex_space = min(hexgrid_hexes_x, hexgrid_hexes_y)
    hex_radius = (hex_space - 1) // 2

    hexgrid_middle_a_x = (tools_start_x / 2) - hex_side_len
    hexgrid_middle_a_y = (screen_height / 2) - hex_side_len

    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height))
    screen.fill("black")

    font = pygame.font.SysFont(None, FONT_SIZE)

    mapper = HexMapper(
        x0=hexgrid_middle_a_x, y0=hexgrid_middle_a_y, side_len=hex_side_len, radius=hex_radius, default_color=BLUE
    )
    pallet = Pallet(tools_start_x, PALLET_Y, font)
    colors = Colors(tools_start_x, COLOR_Y, font)

    clear_x = tools_start_x + CLEAR_BUTTON_OFFSET_X
    save_x = clear_x + BUTTON_WIDTH + SAVE_BUTTON_SPACING_X

    clear_map = Button(pygame.Rect(clear_x, CLEAR_BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT), "clear", font)
    save_image = Button(pygame.Rect(save_x, CLEAR_BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT), "save", font)

    things = [pallet, colors, mapper, clear_map, save_image]
    draw_all(screen, things)

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                p = event.pos

                if clear_map.was_clicked(p):
                    mapper.clear()
                if save_image.was_clicked(p):
                    fn = get_screenshot_filename()

                    hexgrid = screen.subsurface(non_tools_rect)
                    pygame.image.save(hexgrid, fn)

                pallet.poke(p)
                colors.poke(p, pallet.selected_color)
                mapper.poke(p, colors.selected_color)

                draw_all(screen, things)

            elif event.type == pygame.MOUSEBUTTONUP:
                pallet.unclick()
                colors.unclick()
                clear_map.unclick()
                save_image.unclick()

                draw_all(screen, things)

        pygame.display.flip()

    pygame.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--size", type=int, default=20)
    parser.add_argument("--screen-width", type=int, default=1560)
    parser.add_argument("--screen-height", type=int, default=1000)

    args = parser.parse_args()
    run(args.size, args.screen_width, args.screen_height)
