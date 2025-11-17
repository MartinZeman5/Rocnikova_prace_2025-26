import pygame
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

class Map:
    """Z GeoJSON udělá vizuální posuvnou a zoomovatelnou mapu v maximálních možných rozměrech."""
    def __init__(self, window, data, x, y, max_width, max_height):
        self.window = window
        self.geojson = data
        bounds_rect = self.geojson.union_all().bounds # Najde co nejmenší obdélník, do kterého se vejde mapa
        self.map_width = abs(bounds_rect[0]-bounds_rect[2])
        self.map_height = abs(bounds_rect[1]-bounds_rect[3])
        ratio = self.map_width/self.map_height
        if max_height*ratio <= max_width:
            self.height = int(max_height)
            self.width = int(max_height*ratio)
            self.screen_x = int(x + (max_width-self.width)/2) # Chci aby to bylo vycentrováno v daném prostoru
            self.screen_y = int(y)
        else:
            self.width = int(max_width)
            self.height = int(max_width/ratio)
            self.screen_x = int(x)
            self.screen_y = int(y + (max_height-self.height)/2)
        self.default_scale = self.width / self.map_width
        self.min_offset_x = -int(bounds_rect[0])
        self.min_offset_y = -int(bounds_rect[1])
        self.set_default_view()
    
    def set_default_view(self):
        """Nastaví výchozí hodnoty pro zobrazení mapy"""
        self.scale = self.default_scale
        self.offset_x = self.min_offset_x
        self.offset_y = self.min_offset_y
    
    def zoom(self, rate):
        """Zazoomuje tak, aby zachoval stejný střed"""
        self.offset_x = (self.offset_x)*self.scale
        self.offset_y = (self.offset_y)*self.scale
        self.scale *= rate
        if self.scale < self.default_scale: # Nechci odzoomovat více, než je velikost mapy
            self.scale = self.default_scale
        self.offset_x = (self.offset_x)/self.scale
        self.offset_y = (self.offset_y)/self.scale
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
        return (int(x), int(y))
    
    def screen_to_geo(self, x, y):
        """Převede obrazovkové souřadnice na geografické souřadnice."""
        lon = (x - self.screen_x) / self.scale - self.offset_x
        lat = -(y - self.screen_y) / self.scale - self.offset_y
        return (int(lon), int(lat))
    
    def draw_country(self, polygon, color, border):
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
                pygame.draw.polygon(self.window, color, points)
                pygame.draw.lines(self.window, border, True, points, 1)
    
    def draw_map(self):
        pygame.draw.rect(self.window, (100, 100, 255), (self.screen_x-10, self.screen_y-10, self.width+20, self.height+20))
        for _, row in self.geojson.iterrows():
            self.draw_country(row.geometry, (255, 255, 255), (255, 255, 255))

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

def main():
    pygame.init()
    screen = pygame.display.set_mode((1000, 700), pygame.RESIZABLE)
    pygame.display.set_caption("GeoDraw – mapa světa (Pygame + GeoPandas)")

    # --- Načtení dat ---
    print("Načítám GeoJSON...")
    gdf = gpd.read_file("worldmap.geojson")
    mapa = Map(screen, gdf, 10, 100, 980, 600)
    
    font = pygame.font.SysFont("segoeui", 22)

    # --- Tlačítka ---
    buttons = [
        Button((20, 10, 140, 40), "Reset pozice", (180, 200, 240), (160, 180, 220), "reset"),
        Button((180, 10, 100, 40), "Konec", (240, 180, 180), (220, 160, 160), "quit")
    ]

    running = True
    dragging = False
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                # zoom
                if event.y > 0:
                    mapa.zoom(1.1)
                elif event.y < 0:
                    mapa.zoom(1/1.1)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for btn in buttons:
                        if btn.check_click(event.pos):
                            if btn.action == "reset":
                                mapa.set_default_view()
                            elif btn.action == "quit":
                                running = False
                            break
                    else:
                        # klik mimo toolbar – začátek posunu mapy
                        if event.pos[1] > 100:
                            dragging = True
                            prev_mouse = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False

            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                dx, dy = mx - prev_mouse[0], my - prev_mouse[1]
                mapa.move(dx, dy)
                prev_mouse = (mx, my)
        
        screen.fill((0,0,0))
        mapa.draw_map()
        fill_except_rect(screen, (100, 100, 100), (mapa.screen_x, mapa.screen_y, mapa.width, mapa.height))
        
        # Toolbar
        pygame.draw.rect(screen, (100, 100, 100), (0, 0, 1000, 100))
        title_surface = font.render("GeoDraw – Mapa světa", True, (220, 220, 240))
        screen.blit(title_surface, (500 - title_surface.get_width()//2, 15))
        for btn in buttons:
            btn.draw(screen, font, mouse_pos)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()









