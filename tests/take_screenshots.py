#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per acquisire screenshot dell'applicazione Meridiana in modalità headless.
Viene eseguito nel CI di GitHub Actions dopo i test, produce immagini PNG
caricate come artifact e consultabili direttamente su GitHub.
"""
import os
import sys

# Forza la modalità offscreen (nessun display fisico necessario)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QScreen

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")


def save(widget, filename: str) -> None:
    widget.show()
    widget.repaint()
    QApplication.processEvents()
    pixmap = widget.grab()
    path = os.path.join(OUTPUT_DIR, filename)
    pixmap.save(path, "PNG")
    print(f"  Screenshot salvato: {path}")


def main() -> int:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    screenshots_taken = 0

    # ------------------------------------------------------------------ #
    # 1. Dialogo di configurazione DB (non richiede connessione attiva)    #
    # ------------------------------------------------------------------ #
    try:
        from gui_widgets import DBConfigDialog
        dlg = DBConfigDialog()
        save(dlg, "01_configurazione_database.png")
        screenshots_taken += 1
    except Exception as exc:
        print(f"  [WARN] DBConfigDialog non disponibile: {exc}")

    # ------------------------------------------------------------------ #
    # 2. Finestra principale (richiede il DB di test)                     #
    # ------------------------------------------------------------------ #
    db_host = os.environ.get("DB_HOST", "localhost")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "testpassword")
    db_name = os.environ.get("DB_NAME", "catasto_storico")
    db_port = int(os.environ.get("DB_PORT", "5432"))

    try:
        from catasto_db_manager import CatastoDBManager
        manager = CatastoDBManager(
            host=db_host, dbname=db_name,
            user=db_user, password=db_pass, port=db_port
        )
        manager.initialize_main_pool()

        # Importa la finestra principale senza passare per il flusso di login
        from gui_main import MainWindow
        window = MainWindow(db_manager=manager)
        window.resize(1280, 800)
        save(window, "02_finestra_principale.png")
        screenshots_taken += 1

        # Naviga sulle tab principali e cattura ognuna
        tab_widget = window.findChild(__import__("PyQt6.QtWidgets", fromlist=["QTabWidget"]).QTabWidget)
        if tab_widget:
            for i in range(min(tab_widget.count(), 6)):
                tab_widget.setCurrentIndex(i)
                QApplication.processEvents()
                name = tab_widget.tabText(i).replace(" ", "_").replace("/", "-")
                save(window, f"03_tab_{i:02d}_{name}.png")
                screenshots_taken += 1

        manager.close_pool()
    except Exception as exc:
        print(f"  [WARN] Finestra principale non acquisita: {exc}")

    print(f"\nScreenshot acquisiti: {screenshots_taken}")
    return 0 if screenshots_taken > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
