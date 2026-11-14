#!/bin/bash
# controllo-salute.sh — la postazione e' sana solo se il cliente, aprendo il
# browser, troverebbe davvero il programma: schermo virtuale attivo, ponte
# verso il browser che risponde, Foliarium in esecuzione.
#
# Mentre il programma aspetta il database il controllo fallisce: e' voluto.

[ -S /tmp/.X11-unix/X1 ] || { echo "schermo virtuale assente"; exit 1; }

curl -fsS -o /dev/null --max-time 3 http://127.0.0.1:6080/ \
    || { echo "il ponte verso il browser non risponde"; exit 1; }

# Le parentesi quadre evitano che pgrep trovi la riga di comando di chi lo
# ha lanciato (per esempio `sh -c 'pgrep -f gui_main.py'`).
pgrep -f '/opt/foliarium/[g]ui_main.py' > /dev/null \
    || { echo "Foliarium non e' in esecuzione"; exit 1; }

# In modalita' demo un errore di connessione al database produce una finestra
# modale («Demo — DB non raggiungibile», «Demo — Errore DB», «Demo — Avvio
# database fallito») che aspetta un clic: il processo esiste, ma il cliente
# vedrebbe un errore. Va segnalato come postazione non sana.
if xwininfo -root -tree 2>/dev/null | grep -q '"Demo — '; then
    echo "il programma mostra un errore di database"
    exit 1
fi

exit 0
