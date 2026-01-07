from gamemap import * # Zde už importujeme hodně knihoven potřebných i k tomuto scriptu
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class Menu(QWidget):
    """ Hlavní menu """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.show()

    def init_ui(self):
        self.setWindowTitle('GeoDraw - Menu')
        self.set_icon()
        self.resize(1000, 700)
        if settings.mode == "dark-mode":
            apply_dark_title_bar(self)
        h_layout = QHBoxLayout()
        middle_v_layout = QVBoxLayout()
        title = QLabel()
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_path = resource_path('styles/GeoDraw_menu_logo_dark.png') if settings.mode == "dark-mode" else resource_path('styles/GeoDraw_menu_logo.png')
        pixmap = QPixmap(logo_path)

        if not pixmap.isNull():
            pixmap = pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
            title.setPixmap(pixmap)
        else:
            # Záloha pro případ, že se obrázek nepodaří načíst
            title.setText('<h1>MENU</h1>')

        btn_tutorial = QPushButton('Tutorial')
        btn_tutorial.setObjectName("play_button")
        btn_tutorial.clicked.connect(self.spustit_tutorial)

        btn_random = QPushButton('Random country')
        btn_random.setObjectName("play_button")
        btn_random.clicked.connect(self.spustit_hru_random_country)

        middle_v_layout.addWidget(title,1)
        middle_v_layout.addStretch(1)
        middle_v_layout.addWidget(btn_tutorial, 1)
        middle_v_layout.addWidget(btn_random,1)
        middle_v_layout.addStretch(5)

        h_layout.addStretch(1)
        h_layout.addLayout(middle_v_layout, 2)
        h_layout.addStretch(1)

        self.setLayout(h_layout)

    def set_icon(self):
        """ Nastaví ikonu okna na obrázek 'icon.png' """
        # Musíme nastavit unikátní ID aplikace, aby ji Windows nebral jako "Python" (jinak by vzal ikonu pro python)
        myappid = 'GeoDraw.v.1'
        try:
            # Tato funkce řekne Windows, že jde o samostatnou aplikaci
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except AttributeError:
            # Pokud spouštíš kód na jiném systému než Windows (Linux/Mac),
            # tato funkce nemusí existovat, proto chybu ignorujeme.
            pass
        self.setWindowIcon(QIcon(resource_path('styles/icon.png')))

    def spustit_hru_random_country(self):
        selector = ContinentSelector()
        # Zobrazíme modální okno
        if selector.exec():
            selected_continents = selector.get_selected_continents()

            if not selected_continents:
                # Pokud nic nevybral, zobrazíme jen rychlou hlášku a neukončujeme menu
                QMessageBox.warning(self, "Warning", "You need to choose at least one continent!")
                return

            # Nahrát do JSON vybrané kontinenty
            json_dict = json.loads(open(resource_path("country_data/continents.json"), 'r', encoding="utf-8").read())
            json_dict["allowed_continents"] = selected_continents
            json.dump(json_dict, open(resource_path("country_data/continents.json"), "w", encoding="utf-8"), indent=2)

            # Spustit hru
            scale_factor = self.devicePixelRatioF()
            sirka = self.frameGeometry().width() * scale_factor
            vyska = self.frameGeometry().height() * scale_factor
            gamemap = run_pygame(width=sirka, height=vyska)
            self.hide()
            gamemap.mainloop()
            self.show()

    def spustit_tutorial(self):
        scale_factor = self.devicePixelRatioF()
        sirka = self.frameGeometry().width()*scale_factor
        vyska = self.frameGeometry().height()*scale_factor
        gamemap = run_tutorial(width=sirka, height=vyska)
        self.hide()
        gamemap.mainloop()
        self.show()


class ContinentSelector(QDialog):
    """ Před tím, než se spustí hra, chceme vědět, ze kterých kontinentů hráč chce státy """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Choose continents")
        self.resize(350, 450)
        self.setObjectName("ContinentSelector")
        if settings.mode == "dark-mode":
            apply_dark_title_bar(self)

        # Layout
        layout = QVBoxLayout()

        # Nadpis
        label = QLabel("Choose continents you want to have countries from")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("ContinentTitle")  # ID pro QSS
        layout.addWidget(label)

        # Seznam kontinentů
        json_dict = json.loads(open(resource_path("country_data/continents.json"), 'r', encoding="utf-8").read())
        self.continents_list = json_dict["all_continents"]

        # Vytvoření checkboxů
        self.checkboxes = []
        for cont in self.continents_list:
            chk = QCheckBox(cont)
            chk.setChecked(True)
            self.checkboxes.append(chk)
            layout.addWidget(chk)

        layout.addStretch(1)

        # Tlačítka
        btn_layout = QHBoxLayout()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("BtnBack")
        btn_cancel.clicked.connect(self.reject)

        btn_start = QPushButton("Start Game")
        btn_start.setObjectName("BtnStart")
        btn_start.clicked.connect(self.accept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_start)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_selected_continents(self):
        """ Vrátí seznam názvů vybraných kontinentů """
        selected = []
        for chk in self.checkboxes:
            if chk.isChecked():
                selected.append(chk.text())
        return selected

def apply_dark_title_bar(window):
    """
    Zapne tmavou horní lištu (Title Bar) pro dané okno ve Windows 10/11.
    """
    try:
        # Získáme handle (ID) okna
        hwnd = window.winId()

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            int(hwnd),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception as e:
        print(f"Nepodařilo se nastavit tmavou lištu: {e}")

def load_styles(mode):
    """ Načtení souborů se styly podle palety """
    with open(resource_path("styles/layout.qss"), "r", encoding="utf-8") as f:
        layout_style = f.read()

    # Načteme barvy
    with open(resource_path("styles/"+mode+".qss"), "r", encoding="utf-8") as f:
        color_style = f.read()

    # Vrátíme spojený řetězec
    return layout_style + color_style


if __name__ == '__main__':
    settings = Settings()
    app = QApplication(sys.argv)
    app.setStyleSheet(load_styles(settings.mode))
    window = Menu()
    sys.exit(app.exec())