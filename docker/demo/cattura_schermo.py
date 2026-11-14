#!/usr/bin/env python3
"""
docker/demo/cattura_schermo.py — salva in PNG lo schermo virtuale della demo.

Uso (dentro il container della postazione):
    python /opt/foliarium-demo/cattura_schermo.py /tmp/schermo.png

Serve a due cose: permettere a chi installa la demo di vedere che cosa
troverebbe il cliente senza aprire un browser, e dare alla prova automatica
(docker/demo/prova.sh, CI) un'immagine da allegare.

Esce con 1 se lo schermo e' di un solo colore: e' il sintomo di uno schermo
virtuale partito senza che nessuna finestra vi sia comparsa.
"""

from __future__ import annotations

import sys

from PyQt6.QtGui import QGuiApplication

# Punti campionati per lato: 24 x 24 bastano a distinguere una finestra
# vera da uno sfondo uniforme senza leggere ogni pixel.
CAMPIONI = 24


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: cattura_schermo.py <file.png>", file=sys.stderr)
        return 2
    destinazione = sys.argv[1]

    app = QGuiApplication(sys.argv[:1])
    schermo = app.primaryScreen()
    if schermo is None:
        print("nessuno schermo disponibile", file=sys.stderr)
        return 1

    # Con finestra 0 Qt cattura la finestra radice, cioe' l'intero schermo.
    immagine = schermo.grabWindow(0).toImage()
    if immagine.isNull() or immagine.width() == 0 or immagine.height() == 0:
        print("cattura dello schermo fallita", file=sys.stderr)
        return 1

    if not immagine.save(destinazione, "PNG"):
        print(f"impossibile scrivere {destinazione}", file=sys.stderr)
        return 1

    colori = {
        immagine.pixel(
            (colonna * (immagine.width() - 1)) // (CAMPIONI - 1),
            (riga * (immagine.height() - 1)) // (CAMPIONI - 1),
        )
        for colonna in range(CAMPIONI)
        for riga in range(CAMPIONI)
    }
    print(f"{destinazione}: {immagine.width()}x{immagine.height()}, "
          f"{len(colori)} colori nei punti campionati")
    if len(colori) < 2:
        print("lo schermo e' di un solo colore: nessuna finestra visibile",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
