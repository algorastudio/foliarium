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
from app_utils import get_local_ip_address


def main():
    """Avvia l'applicazione Foliarium."""
    # Configura i metadati dell'applicazione (usati da QSettings)
    QCoreApplication.setOrganizationName("ALGORASTUDIO")
    QCoreApplication.setApplicationName("Foliarium")

    app = QApplication(sys.argv)

    # Configura il logging globale
    setup_global_logging()

    # Recupera l'indirizzo IP locale del client (usato per il log delle sessioni)
    client_ip = get_local_ip_address()

    # Crea e mostra la finestra principale
    window = CatastoMainWindow(client_ip_address_gui=client_ip)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
