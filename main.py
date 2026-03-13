#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Foliarium — Gestionale Catasto Storico per Archivi di Stato
Entry point dell'applicazione.

Autore: Marco Santoro — ALGORASTUDIO
Licenza: AGPL-3.0-or-later
"""

import sys
import os

# Aggiunge la cartella src/ al path di importazione
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

from config import setup_global_logging
from gui_main import CatastoMainWindow


def main():
    """Avvia l'applicazione Foliarium."""
    # Configura i metadati dell'applicazione (usati da QSettings)
    QCoreApplication.setOrganizationName("ALGORASTUDIO")
    QCoreApplication.setApplicationName("Foliarium")

    app = QApplication(sys.argv)

    # Configura il logging globale
    setup_global_logging()

    # Crea e mostra la finestra principale
    window = CatastoMainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
