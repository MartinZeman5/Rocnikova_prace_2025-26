import sys, os, json, pygame, pyproj, threading, ctypes, random
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union, transform

""" Hlavní okno ---------------------------------------------------------------------------------------------------- """
class MainWindow:
    """Hlavní okno"""
    def __init__(self, width, height, outermap, country, countrymap, icon):
        pygame.display.set_icon(icon)
        pygame.init()
        set_icon(icon)
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.mapfile = outermap
        self.country = country
        self.countryfile = countrymap
        self.buttons = []
        self.map = Map(self.screen, self.mapfile, self.countryfile, 10, 115, width-20, height-130)
        self.set_buttons()
        self.set_title()
        self.alert = None # Vyskakovací okno
        self.running = True
        self.dragging = False
        self.drawing = False

    def mainloop(self):
        while(self.running):
            self.event_handler()
            self.draw_window()
        pygame.quit()

    def event_handler(self):
        for event in pygame.event.get():
            mouse_pos = pygame.mouse.get_pos()
            self.set_title()
            self.set_buttons()

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.draw_window()
                self.map.set_default_view()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                for button in self.buttons:
                    button.check_click(mouse_pos)
                if self.alert:
                    for button in self.alert.buttons:
                        if button.check_click(mouse_pos):
                            self.alert = None

            """ Ovládání mapy """
            if self.alert or self.map.state == "calculating": # Pokud je vyskakovací okno, nechci ovládat mapu
                continue

            elif event.type == pygame.MOUSEWHEEL:
                # zoom
                if event.y > 0:
                    self.map.zoom(1.1, mouse_pos[0], mouse_pos[1])
                elif event.y < 0:
                    self.map.zoom(1/1.1, mouse_pos[0], mouse_pos[1])

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    if self.map.click_inside_map(mouse_pos[0], mouse_pos[1]):
                        self.dragging = True
                        self.prev_mouse = event.pos
                elif event.button == 1:
                    button_clicked = False
                    for button in self.map.buttons:
                        if button.check_click(mouse_pos):
                            button_clicked = True
                    if self.map.click_inside_map(mouse_pos[0], mouse_pos[1]) and not button_clicked:
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
                elif event.key == pygame.K_BACKSPACE:
                    self.map.remove_drawn_point()
                elif event.key == pygame.K_DELETE:
                    text = "Are you sure you want to delete all drawn structures?"
                    self.alert = Alert(self,text,["Yes","Cancel"], [lambda: self.map.delete_all_drawn_structures(), None])
                elif event.key == pygame.K_KP_ENTER or event.key == pygame.K_RETURN and self.map.state == "drawing":
                    # Je to delší výpočet, dávám na pozadí
                    self.map.state = "calculating"
                    thread = threading.Thread(target=self.map.calculate_result)
                    thread.start()

    def set_title(self):
        if self.map.state == "drawing":
            self.title = "Draw " + self.country
        elif self.map.state == "calculating":
            self.title = "Calculating..."
        elif self.map.state == "result":
            self.title = f"Result: {self.map.result:.1f} %"
        else:
            self.title = "GeoDraw"

    def set_buttons(self):
        width, height = pygame.display.get_surface().get_size()
        self.buttons = []
        if self.map.state == "result":
            self.buttons.append(Button(pygame.Rect(width - 265, 15, 250, 50), "Next random country", styles.color["button_next_country"], styles.color["button_next_country_hover"], lambda: self.new_country(pick_random_country())))

    def new_country(self, country_path):
        width, height = pygame.display.get_surface().get_size()
        self.countryfile = gpd.read_file(country_path)
        country_name = country_path.split("/")[-1].split(".")[0]  # Chci název souboru
        self.country = " ".join(country_name.split("_"))  # Z podtržítek mezery
        self.buttons = []
        self.map = Map(self.screen, self.mapfile, self.countryfile, 10, 115, width - 20, height - 130)

    def draw_window(self):
        width, height = pygame.display.get_surface().get_size()
        # Minimální velikost je 500x500
        if width < 500 or height < 500:
            width = max(500, width)
            height = max(500, height)
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.map.set_window_size(10, 115, width-20, height-130)
        pygame.display.set_caption("GeoDraw")

        self.screen.fill((0, 0, 0))
        self.map.draw_map()
        fill_except_rect(self.screen, styles.color["background"], (self.map.screen_x, self.map.screen_y, self.map.width, self.map.height))

        # Toolbar
        pygame.draw.rect(self.screen, styles.color["toolbar_background"], (0, 0, width, 100))
        draw_text_in_rect(self.screen, self.title, pygame.Rect(100,10,width-200,80), styles.color["text"])

        # Tlačítka
        for button in self.buttons:
            button.draw(self.screen,pygame.mouse.get_pos())

        # Alert
        if self.alert:
            self.alert.draw_alert()

        pygame.display.flip()

""" Mapa ----------------------------------------------------------------------------------------------------------- """
class Map:
    """Z GeoJSON udělá vizuální posuvnou a zoomovatelnou mapu v maximálních možných rozměrech."""
    def __init__(self, window, data, country_data, x, y, max_width, max_height):
        self.window = window # Odkaz na okno ve kterém se mapa nachází
        self.surface = None # Plocha kam vygeneruji polygon mapy, abych to mohl generovat, jen když se tam něco změní
        self.worldmap = unary_union([row.geometry for _, row in data.iterrows()]).buffer(0) # Data vnější mapy
        self.country = country_data # Data mapy země
        self.country = unary_union([row.geometry.buffer(0) for _, row in self.country.iterrows()])
        self.state = "drawing" # Aktuální stav mapy (drawing/result)
        self.scale = 1 # Poměr šířky v px ku šířce mapy v zeměpisných souřadnicích
        self.bounds_rect = data.union_all().bounds # Najde co nejmenší obdélník, do kterého se vejde mapa
        self.min_offset_x = -self.bounds_rect[0]
        self.min_offset_y = self.bounds_rect[3]
        self.offset_x = self.min_offset_x # Rozdíl x od bodu (0,0) v zeměpisných souřadnicích
        self.offset_y = self.min_offset_y # Rozdíl y od bodu (0,0) v zeměpisných souřadnicích
        self.buttons = [Button((0,0,0,0), "+", styles.color["zoom_button"], styles.color["zoom_button_hover"],action=lambda: self.zoom(1.1)),
                        Button((0,0,0,0), "-", styles.color["zoom_button"], styles.color["zoom_button_hover"],action=lambda: self.zoom(1 / 1.1))]
        self.drawn = MultiPolygon([]) # MultiPolygon nakreslený hráčem
        self.drawn_points = [] # Nedokončený polygon, který kreslí hráč
        self.set_window_size(x, y, max_width, max_height)
        self.set_default_view()
        # Nástroje pro přepočet z geografických souřadnic na metrické souřadnice (aby se dal počítat obsah)
        wgs84 = pyproj.CRS('EPSG:4326')
        target_crs = pyproj.CRS('EPSG:8857')
        self.transformer = pyproj.Transformer.from_crs(wgs84, target_crs, always_xy=True).transform
        self.back_transformer = pyproj.Transformer.from_crs(target_crs, wgs84, always_xy=True).transform
        self.country_metric = transform(self.transformer, self.country)
        self.country_area = self.country_metric.area
        self.update_map_surface()

    """Vykreslování -----------------------"""
    def draw_map(self):
        """Vykreslí mapu"""
        if self.state == "calculating":
            font = pygame.font.SysFont(styles.font, styles.fontsizes["loading"])
            text_surface = font.render("Calculating...", True, styles.color["text"])
            self.window.blit(text_surface, pygame.Rect(self.screen_x,self.screen_y,self.width,self.height))
            return
        self.window.blit(self.surface, (self.screen_x, self.screen_y))
        self.draw_buttons()

    def draw_country(self, surface, polygon, color):
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
                pygame.draw.polygon(surface, color, points)

    def draw_borders(self, surface, polygon):
        """Nakreslí hranice polygonu"""
        if isinstance(polygon, Polygon):
            polygons = [polygon]
        elif isinstance(polygon, MultiPolygon):
            polygons = polygon.geoms
        else:
            return

        for poly in polygons:
            points = [self.geo_to_screen(x, y) for x, y in poly.exterior.coords]
            if len(points) > 2:
                pygame.draw.lines(surface, styles.color["border"], True, points, 2)

    def draw_buttons(self):
        for button in self.buttons:
            button.draw(self.window,pygame.mouse.get_pos())

    def update_map_surface(self):
        self.surface = pygame.Surface((self.width, self.height))
        pygame.draw.rect(self.surface, styles.color["ocean"], (0, 0, self.width, self.height))
        self.draw_country(self.surface, self.worldmap, styles.color["continent"])
        if self.state == "drawing":
            self.draw_borders(self.surface, self.drawn)
            if len(self.drawn_points) >= 2:
                pygame.draw.lines(self.surface, styles.color["border"], False,
                                  [(self.geo_to_screen(i[0], i[1])) for i in self.drawn_points], 2)
        elif self.state == "result":
            self.draw_country(self.surface, self.drawn_rest_geom, styles.color["wrong_area"])
            self.draw_country(self.surface, self.country_rest_geom, styles.color["rest_area"])
            self.draw_country(self.surface, self.intersection_geom, styles.color["correct_area"])

    """Logika --------------------------"""
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
        buttons_x = self.screen_x + self.width - 35
        self.buttons[0].rect = pygame.Rect(buttons_x, self.screen_y + 10, 25, 25)
        self.buttons[1].rect = pygame.Rect(buttons_x, self.screen_y + 35, 25, 25)
        self.zoom(1) # Aby nezůstala mapa více oddálená než je možné
    
    def set_default_view(self):
        """Nastaví výchozí hodnoty pro zobrazení mapy"""
        self.scale = self.default_scale
        self.offset_x = self.min_offset_x
        self.offset_y = self.min_offset_y
    
    def zoom(self, rate, mouse_x=None, mouse_y=None):
        """Zazoomuje tak, aby zachoval místo kurzoru myši na stejném místě"""
        if mouse_x is None: # Používáme například při zoomu tlačítkem
            mouse_x = self.screen_x + (self.width / 2)
        if mouse_y is None:
            mouse_y = self.screen_y + (self.height / 2)
        rel_x = mouse_x - self.screen_x
        rel_y = mouse_y - self.screen_y
        cursor_lon = (rel_x / self.scale) - self.offset_x
        cursor_lat = self.offset_y - rel_y / self.scale
        self.scale *= rate
        if self.scale < self.default_scale: # Nechci odzoomovat více, než je velikost mapy
            self.scale = self.default_scale
        self.offset_x = (rel_x / self.scale) - cursor_lon
        self.offset_y = (rel_y / self.scale) + cursor_lat
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
        self.update_map_surface()
    
    def geo_to_screen(self, lon, lat):
        """Převede geografické souřadnice na obrazovkové souřadnice. (avšak lokálně, nepřipočítává se screen_x, screen_y)"""
        x = (lon + self.offset_x) * self.scale
        y = (-lat + self.offset_y) * self.scale  # obrácená osa Y
        return int(x), int(y)
    
    def screen_to_geo(self, x, y):
        """Převede obrazovkové souřadnice na geografické souřadnice."""
        lon = (x - self.screen_x) / self.scale - self.offset_x
        lat = self.offset_y - (y - self.screen_y) / self.scale
        return lon, lat

    def add_drawn_point(self, x, y):
        """Přidá souřadnice převedené na geografické souřadnice"""
        self.drawn_points.append((self.screen_to_geo(x,y)))

    def remove_drawn_point(self):
        """Odstraní poslední nakreslený bod"""
        if self.drawn_points:
            self.drawn_points.pop()
        if len(self.drawn_points) == 1:
            self.drawn_points.pop()

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

    def delete_all_drawn_structures(self):
        """ Smaže všechny hranice namalované hráčem """
        self.drawn_points = []
        self.drawn = MultiPolygon([])

    def calculate_result(self):
        """ Vypočítá úspěšnost namalovaného objektu a uloží Polygony překryvů """
        country_multipolygon = self.country_metric
        drawn_multipolygon = self.drawn
        # Je potřeba přepočítat geografické souřadnice, tak aby polygon seděl metricky
        drawn_multipolygon = transform(self.transformer, drawn_multipolygon)
        # Spočítat průnik a zbytky
        intersection_metric = country_multipolygon.intersection(drawn_multipolygon)
        drawn_rest_metric = drawn_multipolygon.difference(country_multipolygon)
        country_rest_metric = country_multipolygon.difference(drawn_multipolygon)
        # Spočítat procentuální výsledky
        self.percent_correct_area = (intersection_metric.area / self.country_area) * 100
        self.percent_wrong_area = (drawn_rest_metric.area / self.country_area) * 100
        self.result = self.percent_correct_area - self.percent_wrong_area
        # Zpětná transformace
        self.intersection_geom = transform(self.back_transformer, intersection_metric)
        self.drawn_rest_geom = transform(self.back_transformer, drawn_rest_metric)
        self.country_rest_geom = transform(self.back_transformer, country_rest_metric)
        self.state = "result"
        self.update_map_surface()

""" Tlačítko ------------------------------------------------------------------------------------------------------- """
class Button:
    """Jednoduché tlačítko."""
    def __init__(self, rect, text, color, hover, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = pygame.font.SysFont(styles.font, styles.fontsizes["button"])
        self.color = color
        self.hover_color = hover
        self.action = action

    def draw(self, screen, mouse_pos):
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def check_click(self, mouse_pos):
        """Pokud je kliknuto, provede akci."""
        if self.rect.collidepoint(mouse_pos):
            if self.action:  # Zkontrolujeme, zda je nějaká akce přiřazena
                self.action()  # Spustíme funkci
            return True
        return False

""" Vyskakovací okno ----------------------------------------------------------------------------------------------- """
class Alert:
    def __init__(self, window, text, button_texts, button_actions):
        self.window = window
        self.text = text
        self.x = pygame.display.get_surface().get_width()//2 - 150
        self.button_texts = button_texts
        self.button_actions = button_actions
        self.buttons = self.create_buttons()

    def create_buttons(self):
        buttons = []
        count = len(self.button_texts)
        for i in range(count):
            if i == 0:
                color = styles.color["alert_succes"]
                hover_color = styles.color["alert_succes_hover"]
            elif i == 1:
                color = styles.color["alert_cancel"]
                hover_color = styles.color["alert_cancel_hover"]
            else:
                color = styles.color["alert_other"]
                hover_color = styles.color["alert_other_hover"]
            buttons.append(Button((self.x+210-i*100,300,80,30),self.button_texts[i], color, hover_color, lambda index=i: self.action(index)))
        return buttons

    def reload_alert(self):
        self.x = pygame.display.get_surface().get_width() // 2 - 150
        self.buttons = self.create_buttons()

    def draw_alert(self):
        pygame.draw.rect(self.window.screen, styles.color["alert"], (self.x,150,300,200))
        draw_text_in_rect(self.window.screen, self.text, pygame.Rect(self.x + 25,170,250,100), styles.color["text"])
        for button in self.buttons:
            button.draw(self.window.screen,pygame.mouse.get_pos())

    def action(self, i):
        if self.button_actions[i]:
            self.button_actions[i]()


""" Pomocné funkce pro vykreslování -------------------------------------------------------------------------------- """
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

def draw_text_in_rect(surface, text, rect, color):
    """ Vepíše text v co největším možném fontu do obdélníku """
    # Jeden řádek
    lines_1 = [text]
    size_1 = get_max_font_size(lines_1, rect)
    # Dva řádky
    lines_2 = smart_split(text)
    # Pokud text nejde rozdělit (jedno slovo), velikost pro 2 řádky je 0 (nepoužitelné)
    if len(lines_2) < 2:
        size_2 = 0
    else:
        size_2 = get_max_font_size(lines_2, rect)

    # Vybereme variantu, která umožní větší písmo
    if size_1 >= size_2:
        final_size = size_1
        final_lines = lines_1
    else:
        final_size = size_2
        final_lines = lines_2

    # --- VYKRESLENÍ ---
    if final_size > 0:
        font = pygame.font.SysFont(styles.font, final_size)
        # Spočítat celkovou výšku bloku pro vycentrování
        total_block_height = sum(font.size(line)[1] for line in final_lines)
        start_y = rect.centery - total_block_height // 2
        current_y = start_y
        for line in final_lines:
            w, h = font.size(line)
            text_surf = font.render(line, True, color)
            text_rect = text_surf.get_rect()
            text_rect.centerx = rect.centerx
            text_rect.top = current_y

            surface.blit(text_surf, text_rect)
            current_y += h + 5

def smart_split(text):
    """ Rozdělí text v půlce (nikoliv ale uprostřed slova) """
    words = text.split(' ')
    if len(words) <= 1: return [text]
    middle_index = len(text) // 2
    best_split_index = 0
    min_distance = len(text)
    current_length = 0
    for i, word in enumerate(words):
        current_length += len(word) + 1
        distance = abs(current_length - middle_index)
        if distance < min_distance:
            min_distance = distance
            best_split_index = i + 1

    part1 = " ".join(words[:best_split_index])
    part2 = " ".join(words[best_split_index:])
    if not part1: return [part2]
    if not part2: return [part1]
    return [part1, part2]

def get_max_font_size(text_lines, rect):
    """
    Zjistí maximální možnou velikost písma pro daný seznam řádků (1 nebo 2), aby se vešly do rect.
    Vrací velikost písma (int). Pokud se nevejde ani min, vrací 0.
    """
    for size in range(50, 10, -1):
        font = pygame.font.SysFont(styles.font, size)
        total_height = -5
        max_width = 0

        # Spočítáme rozměry celého bloku textu
        for line in text_lines:
            w, h = font.size(line)
            max_width = max(max_width, w)
            total_height += h + 5
        # Kontrola, zda se vejdeme
        if max_width <= rect.width and total_height <= rect.height:
            return size
    return 0

def set_icon(icon):
    """ Nastaví ikonu okna na obrázek 'icon' """
    # Musíme nastavit unikátní ID aplikace, aby ji Windows nebral jako "Python" (jinak by vzal ikonu pro python)
    myappid = 'GeoDraw.v.1'
    try:
        # Tato funkce řekne Windows, že jde o samostatnou aplikaci
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except AttributeError:
        # Pokud spouštíš kód na jiném systému než Windows (Linux/Mac),
        # tato funkce nemusí existovat, proto chybu ignorujeme.
        pass
    pygame.display.set_icon(icon)

""" Další pomocné funkce ------------------------------------------------------------------------------------------- """
def resource_path(relative_path):
    """ Získá správnou cestu k přibaleným datům (pro exe) """
    try:
        # Pokud běží jako exe, PyInstaller vytvoří tuto složku
        base_path = sys._MEIPASS
    except Exception:
        # Pokud běží normálně v Pythonu
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def pick_random_country(path=resource_path("country_data")):
    countries = json.loads(open(os.path.join(path,"countries_find.json"), 'r', encoding="utf-8").read())
    list_countries = list(countries.keys())
    choice = random.choice(list_countries)
    folder = path + "/" + countries[choice] + "/ADM0/"
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    return os.path.join(folder,files[0]) # Měl by být pouze jeden

class Styles:
    def __init__(self, file_path):
        styles = json.loads(open(file_path, 'r', encoding="utf-8").read())
        self.font = styles["font"]
        self.fontsizes = styles["fontsizes"]
        self.color = styles["colors"]

def run_pygame(width=1000,height=700, background_map_file=None, country_file=None):
    """ Spustí hru se zadanými parametry (Pak je ještě potřeba zvenku zavolat .mainloop())"""
    global styles
    styles = Styles(resource_path("styles/normal.json"))
    if background_map_file is None:
        background_map_file = resource_path("data/worldmap.geojson")
    if country_file is None:
        country_file = pick_random_country(resource_path("country_data"))
    country_name = country_file.split("/")[-1].split(".")[0] # Chci název souboru
    country_name = " ".join(country_name.split("_")) # Z podtržítek mezery
    return MainWindow(width, height, gpd.read_file(background_map_file), country_name, gpd.read_file(country_file), pygame.image.load(resource_path("styles/icon.png")))

if __name__ == "__main__":
    styles = Styles(resource_path("styles/normal.json"))
    run = MainWindow(1000, 700, gpd.read_file(resource_path("data/worldmap.geojson")), "France", gpd.read_file(resource_path("geoBoundaries-FRA-ADM0_simplified.topojson")), pygame.image.load(resource_path("styles/icon.png")))
    run.mainloop()