#!/usr/bin/env python3
"""
docker/demo/file_server.py — pagina di download della demo.

Nella demo Foliarium gira su un server e il cliente lo vede dal browser.
Un file salvato con «Salva con nome» finisce quindi sul disco del server:
questa pagina pubblica la cartella Documenti della postazione, cosi' il
cliente puo' scaricare cio' che ha esportato.

Usa solo la libreria standard. Sta dietro il proxy della demo, che chiede
le credenziali e toglie il prefisso `/<postazione>/file`: per questo ogni
collegamento generato qui e' RELATIVO.

Regola di sicurezza, una sola: non esce nulla che, risolti i collegamenti
simbolici, non stia dentro la cartella pubblicata. Sta tutta in `risolvi`.
"""

from __future__ import annotations

import html
import mimetypes
import os
import shutil
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, Optional, Type
from urllib.parse import quote, unquote

FORMATO_DATA = "%d/%m/%Y %H:%M"
TESTO_VUOTO = "Nessun file esportato."
METODI_AMMESSI = "GET, HEAD"


# ---------------------------------------------------------------------------
# Dal percorso della richiesta al file su disco
# ---------------------------------------------------------------------------

def risolvi(radice: Path, percorso_url: str) -> Optional[Path]:
    """
    Traduce il percorso di una richiesta in un percorso reale dentro `radice`.

    Restituisce None, cioe' 404, se il percorso non esiste, se un suo
    componente e' nascosto (comincia con un punto) o se, risolti i
    collegamenti simbolici, cade fuori da `radice`.
    """
    radice = radice.resolve()
    solo_percorso = percorso_url.split("?", 1)[0].split("#", 1)[0]

    parti: List[str] = []
    for grezza in solo_percorso.split("/"):
        if not grezza:
            continue
        try:
            parte = unquote(grezza, errors="strict")
        except UnicodeDecodeError:
            return None
        # Il controllo va fatto DOPO la decodifica: `%2e%2e` e `..%2f` sono
        # i modi classici per far passare un `..` oltre un filtro ingenuo.
        if parte.startswith(".") or "/" in parte or "\\" in parte or "\x00" in parte:
            return None
        parti.append(parte)

    try:
        reale = radice.joinpath(*parti).resolve(strict=True)
    except (OSError, ValueError):
        return None
    if not _dentro(radice, reale):
        return None
    return reale


def _dentro(radice: Path, percorso: Path) -> bool:
    return percorso == radice or radice in percorso.parents


# ---------------------------------------------------------------------------
# Pagina con l'elenco
# ---------------------------------------------------------------------------

def _dimensione(byte: int) -> str:
    """Dimensione leggibile, con la virgola decimale italiana."""
    if byte < 1024:
        return f"{byte} byte"
    valore = float(byte)
    for unita in ("kB", "MB", "GB"):
        valore /= 1024
        if valore < 1024 or unita == "GB":
            return f"{valore:.1f}".replace(".", ",") + f" {unita}"
    raise AssertionError("irraggiungibile")


def _voci_visibili(radice: Path, cartella: Path):
    """Cartelle (in ordine alfabetico) e file (dal piu' recente) da mostrare."""
    cartelle, file = [], []
    for voce in cartella.iterdir():
        if voce.name.startswith("."):
            continue
        try:
            reale = voce.resolve(strict=True)
            stato = reale.stat()
        except OSError:
            continue  # collegamento interrotto o voce sparita nel frattempo
        if not _dentro(radice, reale):
            continue  # collegamento simbolico che porta fuori: non si mostra
        if reale.is_dir():
            cartelle.append((voce.name, stato))
        elif reale.is_file():
            file.append((voce.name, stato))
    cartelle.sort(key=lambda v: v[0].lower())
    file.sort(key=lambda v: v[1].st_mtime, reverse=True)
    return cartelle, file


_STILE = """
body{font-family:"Open Sans","Segoe UI",Arial,sans-serif;margin:0;background:#f4f5f7;color:#1f2933}
main{max-width:860px;margin:0 auto;padding:24px 16px}
h1{font-size:1.25rem;margin:0 0 4px}
p.nota{margin:0 0 20px;color:#52606d;font-size:.9rem}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9dee4}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #e4e7eb;font-size:.95rem}
th{background:#eef0f3;font-weight:600}
td.num,th.num{text-align:right;white-space:nowrap}
a{color:#1d4f91;text-decoration:none}a:hover{text-decoration:underline}
p.vuoto{background:#fff;border:1px solid #d9dee4;padding:24px;text-align:center;color:#52606d}
"""


def pagina_elenco(radice: Path, cartella: Path) -> str:
    """Pagina HTML con il contenuto di `cartella`, che deve stare in `radice`."""
    radice = radice.resolve()
    cartella = cartella.resolve()
    cartelle, file = _voci_visibili(radice, cartella)

    righe: List[str] = []
    if cartella != radice:
        righe.append(
            '<tr><td><a href="../">&larr; Cartella superiore</a></td>'
            '<td class="num"></td><td class="num"></td></tr>'
        )
    for nome, stato in cartelle:
        righe.append(
            f'<tr><td><a href="{quote(nome)}/">{html.escape(nome)}/</a></td>'
            f'<td class="num">cartella</td>'
            f'<td class="num">{datetime.fromtimestamp(stato.st_mtime).strftime(FORMATO_DATA)}</td></tr>'
        )
    for nome, stato in file:
        righe.append(
            f'<tr><td><a href="{quote(nome)}">{html.escape(nome)}</a></td>'
            f'<td class="num">{_dimensione(stato.st_size)}</td>'
            f'<td class="num">{datetime.fromtimestamp(stato.st_mtime).strftime(FORMATO_DATA)}</td></tr>'
        )

    if cartelle or file:
        corpo = (
            "<table><thead><tr><th>Nome</th><th class=\"num\">Dimensione</th>"
            "<th class=\"num\">Ultima modifica</th></tr></thead><tbody>"
            + "".join(righe) + "</tbody></table>"
        )
    else:
        ritorno = ('<p><a href="../">&larr; Cartella superiore</a></p>'
                   if cartella != radice else "")
        corpo = f'{ritorno}<p class="vuoto">{TESTO_VUOTO}</p>'

    relativo = cartella.relative_to(radice).as_posix()
    titolo = "File esportati" if relativo == "." else f"File esportati — {relativo}"
    return (
        '<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(titolo)} — Foliarium Demo</title>"
        f"<style>{_STILE}</style></head><body><main>"
        f"<h1>{html.escape(titolo)}</h1>"
        '<p class="nota">I file salvati dal programma nella cartella Documenti '
        "compaiono qui. Ricaricare la pagina dopo una nuova esportazione.</p>"
        f"{corpo}</main></body></html>"
    )


# ---------------------------------------------------------------------------
# Servizio HTTP
# ---------------------------------------------------------------------------

class _Gestore(BaseHTTPRequestHandler):
    radice: Path  # impostata da crea_server
    server_version = "FoliariumDemoFile"
    sys_version = ""

    def do_GET(self):  # noqa: N802 — nome imposto da http.server
        self._servi(con_corpo=True)

    def do_HEAD(self):  # noqa: N802
        self._servi(con_corpo=False)

    def _non_ammesso(self):
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", METODI_AMMESSI)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _non_ammesso  # noqa: N815

    def _servi(self, con_corpo: bool) -> None:
        trovato = risolvi(self.radice, self.path)
        if trovato is None:
            self._testo(HTTPStatus.NOT_FOUND, "File non trovato.", con_corpo)
            return

        if trovato.is_dir():
            solo_percorso = self.path.split("?", 1)[0]
            if not solo_percorso.endswith("/"):
                # Senza la barra finale i collegamenti relativi della pagina
                # punterebbero un livello piu' su. Redirezione relativa: il
                # prefisso tolto dal proxy qui non e' noto.
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", quote(trovato.name) + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._html(HTTPStatus.OK, pagina_elenco(self.radice, trovato), con_corpo)
            return

        try:
            flusso = trovato.open("rb")
        except OSError:
            self._testo(HTTPStatus.NOT_FOUND, "File non trovato.", con_corpo)
            return
        with flusso:
            dimensione = os.fstat(flusso.fileno()).st_size
            tipo = mimetypes.guess_type(trovato.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(dimensione))
            # Sempre come allegato: un file HTML esportato non deve essere
            # eseguito dal browser nell'origine della demo.
            self.send_header("Content-Disposition",
                             f"attachment; filename*=UTF-8''{quote(trovato.name)}")
            self._intestazioni_comuni()
            self.end_headers()
            if con_corpo:
                shutil.copyfileobj(flusso, self.wfile)

    def _intestazioni_comuni(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")

    def _html(self, stato: HTTPStatus, pagina: str, con_corpo: bool) -> None:
        dati = pagina.encode("utf-8")
        self.send_response(stato)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dati)))
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'unsafe-inline'")
        self._intestazioni_comuni()
        self.end_headers()
        if con_corpo:
            self.wfile.write(dati)

    def _testo(self, stato: HTTPStatus, messaggio: str, con_corpo: bool) -> None:
        self._html(
            stato,
            '<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">'
            f"<title>{html.escape(messaggio)}</title></head>"
            f"<body><p>{html.escape(messaggio)}</p>"
            '<p><a href="./">Torna all\'elenco</a></p></body></html>',
            con_corpo,
        )


def crea_server(radice: Path, porta: int, indirizzo: str = "0.0.0.0") -> ThreadingHTTPServer:
    """Server HTTP che pubblica `radice`. Con porta 0 ne sceglie una libera."""
    gestore: Type[_Gestore] = type("GestoreFile", (_Gestore,), {"radice": radice.resolve()})
    return ThreadingHTTPServer((indirizzo, porta), gestore)


def main() -> None:
    radice = Path(os.environ.get("DEMO_FILE_RADICE") or "~/Documenti").expanduser()
    porta = int(os.environ.get("DEMO_FILE_PORTA") or "6081")
    radice.mkdir(parents=True, exist_ok=True)
    server = crea_server(radice, porta)
    print(f"[file-server] pubblico {radice} sulla porta {porta}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
