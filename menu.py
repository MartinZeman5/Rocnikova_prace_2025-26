from gamemap import * # Zde už importujeme hodně knihoven potřebných i k tomuto scriptu
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class Menu(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.show()

    def init_ui(self):
        self.setWindowTitle('GeoDraw - Menu')
        self.set_icon()
        self.resize(1000, 700)
        h_layout = QHBoxLayout()
        middle_v_layout = QVBoxLayout()
        title = QLabel('<h1>MENU</h1>')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_random = QPushButton('Random country')
        btn_random.setObjectName("random_country")
        btn_random.clicked.connect(self.spustit_hru)

        middle_v_layout.addWidget(title,1)
        middle_v_layout.addStretch(1)
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

    def spustit_hru(self):
        scale_factor = self.devicePixelRatioF()
        sirka = self.frameGeometry().width()*scale_factor
        vyska = self.frameGeometry().height()*scale_factor
        gamemap = run_pygame(width=sirka, height=vyska)
        self.hide()
        gamemap.mainloop()

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    with open(resource_path("styles/menu.qss"), "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)
    window = Menu()
    sys.exit(app.exec())