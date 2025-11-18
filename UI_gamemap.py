import json
import pygame
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from mapa import geo_to_screen


class Map:
    """Z GeoJSON udělá vizuální posuvnou a zoomovatelnou mapu v maximálních možných rozměrech."""
    def __init__(self, window, data, x, y, max_width, max_height):
        self.window = window
        self.geojson = data
        self.scale = 1
        self.bounds_rect = self.geojson.union_all().bounds # Najde co nejmenší obdélník, do kterého se vejde mapa
        self.min_offset_x = -int(self.bounds_rect[0])
        self.min_offset_y = -int(self.bounds_rect[1])
        self.offset_x = self.min_offset_x
        self.offset_y = self.min_offset_y
        self.set_window_size(x, y, max_width, max_height)
        self.set_default_view()
        self.drawn = MultiPolygon([]) # MultiPolygon nakreslený hráčem
        self.drawn_points = [] # Nedokončený polygon, který kreslí hráč

    def click_inside_map(self, x, y):
        if self.screen_x <= x <= self.screen_x + self.width and self.screen_y <= y <= self.screen_y + self.height:
            return True
        return False

    def set_window_size(self, x, y, max_width, max_height):
        self.map_width = abs(self.bounds_rect[0] - self.bounds_rect[2])
        self.map_height = abs(self.bounds_rect[1] - self.bounds_rect[3])
        ratio = self.map_width / self.map_height
        if max_height * ratio <= max_width:
            self.height = int(max_height)
            self.width = int(max_height * ratio)
            self.screen_x = int(x + (max_width - self.width) / 2)  # Chci aby to bylo vycentrováno v daném prostoru
            self.screen_y = int(y)
        else:
            self.width = int(max_width)
            self.height = int(max_width / ratio)
            self.screen_x = int(x)
            self.screen_y = int(y + (max_height - self.height) / 2)
        self.default_scale = self.width / self.map_width
        self.zoom(1) # Aby nezůstala mapa více oddálená než je možné
    
    def set_default_view(self):
        """Nastaví výchozí hodnoty pro zobrazení mapy"""
        self.scale = self.default_scale
        self.offset_x = self.min_offset_x
        self.offset_y = self.min_offset_y
    
    def zoom(self, rate):
        """Zazoomuje tak, aby zachoval stejný střed"""
        self.offset_x = self.offset_x*self.scale
        self.offset_y = self.offset_y*self.scale
        self.scale *= rate
        if self.scale < self.default_scale: # Nechci odzoomovat více, než je velikost mapy
            self.scale = self.default_scale
        self.offset_x = self.offset_x/self.scale
        self.offset_y = self.offset_y/self.scale
        self.move(0,0) # Zkontrolovat, zda jsme neodzoomovali mimo plochu
    
    def move(self, x, y):
        """Posune mapu o x, y a pohlídá, že nevyjedu z mapy ven"""
        x = x / self.scale
        y = y / self.scale
        max_offset_x = (self.map_width*self.scale - self.width) / self.scale
        max_offset_y = (self.map_height*self.scale - self.height) / self.scale
        self.offset_x = max(self.offset_x + x, self.min_offset_x - max_offset_x)
        self.offset_y = max(self.offset_y + y, self.min_offset_y - max_offset_y)
        self.offset_x = min(self.offset_x, self.min_offset_x)
        self.offset_y = min(self.offset_y, self.min_offset_y)
    
    def geo_to_screen(self, lon, lat):
        """Převede geografické souřadnice na obrazovkové souřadnice."""
        x = self.screen_x + (lon + self.offset_x) * self.scale
        y = self.screen_y + (-lat + self.offset_y) * self.scale  # obrácená osa Y
        return int(x), int(y)
    
    def screen_to_geo(self, x, y):
        """Převede obrazovkové souřadnice na geografické souřadnice."""
        lon = (x - self.screen_x) / self.scale - self.offset_x
        lat = self.offset_y - (y - self.screen_y) / self.scale
        return lon, lat
    
    def draw_country(self, polygon):
        """Vykreslí jeden stát (Polygon nebo MultiPolygon)."""
        if isinstance(polygon, Polygon):
            polygons = [polygon]
        elif isinstance(polygon, MultiPolygon):
            polygons = polygon.geoms
        else:
            return

        for poly in polygons:
            points = [self.geo_to_screen(x, y) for x, y in poly.exterior.coords]
            if len(points) > 2:
                pygame.draw.polygon(self.window, styles.color["continent"], points)

    def draw_borders(self, polygon):
        if isinstance(polygon, Polygon):
            polygons = [polygon]
        elif isinstance(polygon, MultiPolygon):
            polygons = polygon.geoms
        else:
            return

        for poly in polygons:
            points = [self.geo_to_screen(x, y) for x, y in poly.exterior.coords]
            if len(points) > 2:
                pygame.draw.lines(self.window, styles.color["border"], True, points, 2)
    
    def draw_map(self):
        """Vykreslí mapu"""
        pygame.draw.rect(self.window, styles.color["ocean"], (self.screen_x-10, self.screen_y-10, self.width+20, self.height+20))
        for _, row in self.geojson.iterrows():
            self.draw_country(row.geometry)
        self.draw_borders(self.drawn)
        if len(self.drawn_points) >= 2:
            pygame.draw.lines(self.window, styles.color["border"], False, [(self.geo_to_screen(i[0],i[1])) for i in self.drawn_points], 2)

    def add_drawn_point(self, x, y):
        """Přidá souřadnice převedené na geografické souřadnice"""
        self.drawn_points.append((self.screen_to_geo(x,y)))

    def close_drawn_structure(self):
        """Uzavře doposud namalované body a převede je na Polygon"""
        if len(self.drawn_points) < 2:
            return
        if self.drawn_points[-1] != self.drawn_points[0]:
            self.drawn_points.append(self.drawn_points[0])
        poly = Polygon(self.drawn_points)
        self.drawn_points = []
        if not poly.is_valid:
            poly = poly.buffer(0)  # automatická oprava
        self.drawn = unary_union([self.drawn, poly])


class Button:
    """Jednoduché tlačítko."""
    def __init__(self, rect, text, color, hover, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover
        self.action = action

    def draw(self, screen, font, mouse_pos):
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        text_surface = font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def check_click(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

class MainWindow:
    """Hlavní okno"""
    def __init__(self, width, height, outermap, country, countrymap=0):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.mapfile = outermap
        self.countryfile = countrymap
        self.title = "Draw " + country
        self.map = Map(self.screen, self.mapfile, 10, 100, width-20, height-120)
        self.running = True
        self.dragging = False
        self.drawing = False
        self.mainloop()

    def mainloop(self):
        while(self.running):
            self.event_handler()
            self.draw_window()
        pygame.quit()

    def event_handler(self):
        for event in pygame.event.get():
            mouse_pos = pygame.mouse.get_pos()

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.MOUSEWHEEL:
                # zoom
                if event.y > 0:
                    self.map.zoom(1.1)
                elif event.y < 0:
                    self.map.zoom(1/1.1)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    if self.map.click_inside_map(mouse_pos[0], mouse_pos[1]):
                        self.dragging = True
                        self.prev_mouse = event.pos
                elif event.button == 1:
                    if self.map.click_inside_map(mouse_pos[0], mouse_pos[1]):
                        self.drawing = True
                        self.map.add_drawn_point(mouse_pos[0], mouse_pos[1])
                        self.prev_mouse = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    self.dragging = False
                elif event.button == 1:
                    self.drawing = False

            elif event.type == pygame.MOUSEMOTION and self.dragging:
                mx, my = event.pos
                dx, dy = mx - self.prev_mouse[0], my - self.prev_mouse[1]
                self.map.move(dx, dy)
                self.prev_mouse = (mx, my)

            elif event.type == pygame.MOUSEMOTION and self.drawing:
                mx, my = event.pos
                self.map.add_drawn_point(mx, my)
                self.prev_mouse = (mx, my)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.map.close_drawn_structure()

            elif event.type == pygame.VIDEORESIZE:
                self.draw_window()
                self.map.set_default_view()

    def draw_window(self):
        width, height = pygame.display.get_surface().get_size()
        # Minimální velikost je 500x500
        if width < 500 or height < 500:
            width = max(500, width)
            height = max(500, height)
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.map.set_window_size(10, 100, width-20, height-120)
        pygame.display.set_caption("GeoDraw")

        self.screen.fill((0, 0, 0))
        self.map.draw_map()
        fill_except_rect(self.screen, styles.color["background"], (self.map.screen_x, self.map.screen_y, self.map.width, self.map.height))

        # Toolbar
        font = pygame.font.SysFont(styles.font, styles.fontsizes["nadpis"])
        title_surface = font.render(self.title, True, styles.color["text"])
        self.screen.blit(title_surface, (width//2 - title_surface.get_width() // 2, 15))

        pygame.display.flip()

def fill_except_rect(surface, color, exclude_rect):
    """Vyplní celé okno barvou, ale vynechá zadaný obdélník."""
    w, h = surface.get_size()
    x, y, rw, rh = exclude_rect

    # horní pruh
    pygame.draw.rect(surface, color, (0, 0, w, y))
    # dolní pruh
    pygame.draw.rect(surface, color, (0, y + rh, w, h - (y + rh)))
    # levý pruh
    pygame.draw.rect(surface, color, (0, y, x, rh))
    # pravý pruh
    pygame.draw.rect(surface, color, (x + rw, y, w - (x + rw), rh))

class Styles:
    def __init__(self, file_path):
        styles = json.loads(open(file_path, 'r', encoding="utf-8").read())
        self.font = styles["font"]
        self.fontsizes = styles["fontsizes"]
        self.color = styles["colors"]

if __name__ == "__main__":
    styles = Styles("styles/normal.json")
    run = MainWindow(1000, 700, gpd.read_file("worldmap.geojson"), "France")
