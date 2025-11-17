import pygame
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

# ======== NASTAVENÍ =========
WIDTH, HEIGHT = 1000, 500
TOOLBAR_HEIGHT = 100
BACKGROUND = (100, 100, 255)
COUNTRY_COLOR = (255, 255, 255)
BORDER_COLOR = (255, 255, 255)
TOOLBAR_COLOR = (100, 100, 100)
TEXT_COLOR = (20, 20, 40)

GEOJSON_PATH = "worldmap.geojson"  # ← sem dej cestu ke svému souboru

# ======== FUNKCE NA PŘEVOD SOUŘADNIC =========
def geo_to_screen(lon, lat, scale, offset_x, offset_y):
    """Převede geografické souřadnice (lon, lat) na obrazovkové souřadnice."""
    x = lon * scale + offset_x
    y = -lat * scale + offset_y + TOOLBAR_HEIGHT  # obrácená osa Y
    return (int(x), int(y))

def draw_country(surface, shape, color, border, scale, offset_x, offset_y):
    """Vykreslí jeden stát (Polygon nebo MultiPolygon)."""
    if isinstance(shape, Polygon):
        polygons = [shape]
    elif isinstance(shape, MultiPolygon):
        polygons = shape.geoms
    else:
        return

    for poly in polygons:
        points = [geo_to_screen(x, y, scale, offset_x, offset_y)
                  for x, y in poly.exterior.coords]
        if len(points) > 2:
            pygame.draw.polygon(surface, color, points)
            pygame.draw.lines(surface, border, True, points, 1)

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

# ======== HLAVNÍ PROGRAM =========
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + TOOLBAR_HEIGHT))
    pygame.display.set_caption("GeoDraw – mapa světa (Pygame + GeoPandas)")

    # --- Načtení dat ---
    print("Načítám GeoJSON...")
    gdf = gpd.read_file(GEOJSON_PATH)
    print(f"Načteno {len(gdf)} zemí")
    
    font = pygame.font.SysFont("segoeui", 22)

    # --- Inicializace pohledu ---
    scale = WIDTH/360   # počáteční měřítko
    offset_x, offset_y = WIDTH // 2, HEIGHT // 2 + TOOLBAR_HEIGHT
    dragging = False
    prev_mouse = (0, 0)
    
    # --- Tlačítka ---
    buttons = [
        Button((20, 10, 140, 40), "Reset pozice", (180, 200, 240), (160, 180, 220), "reset"),
        Button((180, 10, 100, 40), "Konec", (240, 180, 180), (220, 160, 160), "quit")
    ]

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                # zoom
                if event.y > 0:
                    offset_x = (offset_x-WIDTH/2)/scale
                    offset_y = (offset_y-HEIGHT/2)/scale
                    scale *= 1.1
                    offset_x = offset_x*scale+WIDTH/2
                    offset_y = offset_y*scale+HEIGHT/2
                elif event.y < 0:
                    offset_x = (offset_x-WIDTH/2)/scale
                    offset_y = (offset_y-HEIGHT/2)/scale
                    scale /= 1.1
                    if scale < WIDTH/360:
                        scale = WIDTH/360
                    offset_x = offset_x*scale+WIDTH/2
                    offset_y = offset_y*scale+HEIGHT/2

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for btn in buttons:
                        if btn.check_click(event.pos):
                            if btn.action == "reset":
                                scale = WIDTH/360
                                offset_x, offset_y = WIDTH // 2, HEIGHT // 2 + TOOLBAR_HEIGHT
                            elif btn.action == "quit":
                                running = False
                            break
                    else:
                        # klik mimo toolbar – začátek posunu mapy
                        if event.pos[1] > TOOLBAR_HEIGHT:
                            dragging = True
                            prev_mouse = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False

            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                dx, dy = mx - prev_mouse[0], my - prev_mouse[1]
                offset_x += dx
                offset_y += dy
                prev_mouse = (mx, my)
            max_offset_x = ((WIDTH//2)*scale)/(WIDTH/360)
            max_offset_y = ((HEIGHT//2)*scale)/(HEIGHT/180)
            offset_x = min(offset_x,max_offset_x)
            offset_y = min(offset_y,max_offset_y)
            offset_x = max(offset_x,WIDTH-max_offset_x)
            offset_y = max(offset_y,HEIGHT-max_offset_y)

        # --- Kreslení ---
        screen.fill(BACKGROUND)
        for _, row in gdf.iterrows():
            draw_country(screen, row.geometry, COUNTRY_COLOR, BORDER_COLOR, scale, offset_x, offset_y)
            
        
        # Toolbar
        pygame.draw.rect(screen, TOOLBAR_COLOR, (0, 0, WIDTH, TOOLBAR_HEIGHT))
        title_surface = font.render("GeoDraw – Mapa světa", True, TEXT_COLOR)
        screen.blit(title_surface, (WIDTH//2 - title_surface.get_width()//2, 15))
        for btn in buttons:
            btn.draw(screen, font, mouse_pos)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

