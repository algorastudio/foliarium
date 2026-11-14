"""
tests/unit/test_demo_file_server.py
===================================
La pagina da cui il cliente della demo scarica i file esportati
(`docker/demo/file_server.py`).

Nella demo il programma gira su un server: un PDF salvato con «Salva con
nome» finisce sul disco del server, non sul PC di chi lo ha esportato.
Questa pagina pubblica la cartella Documenti della postazione.

E' un servizio raggiungibile da internet (dietro le credenziali della
postazione): il grosso dei test riguarda cio' che NON deve servire, cioe'
qualunque cosa fuori dalla cartella pubblicata.
"""

from __future__ import annotations

import http.client
import importlib.util
import os
import threading
from datetime import datetime
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

MODULO = Path(__file__).resolve().parents[2] / "docker" / "demo" / "file_server.py"


@pytest.fixture(scope="module")
def fs():
    """Il modulo non sta in un package: lo si carica dal suo percorso."""
    spec = importlib.util.spec_from_file_location("demo_file_server", MODULO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def radice(tmp_path):
    """Cartella pubblicata, con accanto un file che non deve mai uscire."""
    (tmp_path / "segreto.txt").write_text("riservato", encoding="utf-8")
    cartella = tmp_path / "Documenti"
    cartella.mkdir()
    return cartella


@pytest.fixture
def server(fs, radice):
    srv = fs.crea_server(radice, 0, "127.0.0.1")
    filo = threading.Thread(target=srv.serve_forever, daemon=True)
    filo.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    filo.join(timeout=5)


def _richiesta(server, metodo: str, percorso: str):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    try:
        conn.request(metodo, percorso)
        risposta = conn.getresponse()
        return risposta, risposta.read()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# risolvi(): dal percorso della richiesta al file su disco
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ostile", [
    "/../segreto.txt",
    "/%2e%2e/segreto.txt",
    "/a/../../segreto.txt",
    "//etc/passwd",
    "/..%2fsegreto.txt",
    "/%2e%2e%2fsegreto.txt",
    "/.nascosto",
    "/a/.nascosto/x",
    "/esiste.txt%00.pdf",
])
def test_percorsi_ostili_respinti(fs, radice, ostile):
    (radice / "esiste.txt").write_text("x", encoding="utf-8")
    (radice / ".nascosto").write_text("x", encoding="utf-8")
    assert fs.risolvi(radice, ostile) is None


def test_link_simbolico_verso_esterno_respinto(fs, radice, tmp_path):
    (radice / "fuga").symlink_to(tmp_path / "segreto.txt")
    assert fs.risolvi(radice, "/fuga") is None


def test_cartella_collegata_verso_esterno_respinta(fs, radice, tmp_path):
    (radice / "su").symlink_to(tmp_path, target_is_directory=True)
    assert fs.risolvi(radice, "/su/segreto.txt") is None


def test_file_inesistente(fs, radice):
    assert fs.risolvi(radice, "/non-c-e.pdf") is None


def test_radice(fs, radice):
    assert fs.risolvi(radice, "/") == radice.resolve()


def test_file_in_sottocartella(fs, radice):
    (radice / "Esportazioni Foliarium").mkdir()
    atteso = radice / "Esportazioni Foliarium" / "partita_12.pdf"
    atteso.write_bytes(b"%PDF")
    trovato = fs.risolvi(radice, "/Esportazioni%20Foliarium/partita_12.pdf")
    assert trovato == atteso.resolve()


def test_nome_con_spazi_e_accenti(fs, radice):
    (radice / "partita n° 12 città.pdf").write_bytes(b"%PDF")
    trovato = fs.risolvi(radice, "/partita%20n%C2%B0%2012%20citt%C3%A0.pdf")
    assert trovato.name == "partita n° 12 città.pdf"


def test_la_query_viene_ignorata(fs, radice):
    (radice / "a.csv").write_text("x", encoding="utf-8")
    assert fs.risolvi(radice, "/a.csv?scarica=1").name == "a.csv"


# ---------------------------------------------------------------------------
# pagina_elenco(): cio' che il cliente vede
# ---------------------------------------------------------------------------

def test_elenco_vuoto(fs, radice):
    assert "Nessun file esportato." in fs.pagina_elenco(radice, radice)


def test_elenco_dal_piu_recente(fs, radice):
    vecchio = radice / "vecchio.pdf"
    nuovo = radice / "nuovo.pdf"
    vecchio.write_bytes(b"1")
    nuovo.write_bytes(b"2")
    os.utime(vecchio, (1_700_000_000, 1_700_000_000))
    os.utime(nuovo, (1_800_000_000, 1_800_000_000))
    pagina = fs.pagina_elenco(radice, radice)
    assert pagina.index("nuovo.pdf") < pagina.index("vecchio.pdf")


def test_elenco_mostra_data_italiana_e_dimensione(fs, radice):
    f = radice / "report.pdf"
    f.write_bytes(b"x" * 1536)
    os.utime(f, (1_700_000_000, 1_700_000_000))
    pagina = fs.pagina_elenco(radice, radice)
    assert datetime.fromtimestamp(1_700_000_000).strftime("%d/%m/%Y %H:%M") in pagina
    assert "1,5 kB" in pagina


def test_elenco_usa_collegamenti_relativi(fs, radice):
    # La pagina e' servita sotto /<postazione>/file/ e il proxy toglie il
    # prefisso: un collegamento assoluto porterebbe fuori dalla postazione.
    (radice / "a b.pdf").write_bytes(b"x")
    (radice / "cartella").mkdir()
    pagina = fs.pagina_elenco(radice, radice)
    assert 'href="/' not in pagina
    assert 'href="a%20b.pdf"' in pagina
    assert 'href="cartella/"' in pagina


def test_elenco_non_mostra_nascosti_ne_collegamenti_esterni(fs, radice, tmp_path):
    (radice / ".config").mkdir()
    (radice / "fuga").symlink_to(tmp_path / "segreto.txt")
    (radice / "visibile.txt").write_text("x", encoding="utf-8")
    pagina = fs.pagina_elenco(radice, radice)
    assert "visibile.txt" in pagina
    assert ".config" not in pagina
    assert "fuga" not in pagina


def test_elenco_neutralizza_html_nei_nomi(fs, radice):
    (radice / "a<b>&c.txt").write_text("x", encoding="utf-8")
    pagina = fs.pagina_elenco(radice, radice)
    assert "a&lt;b&gt;&amp;c.txt" in pagina
    assert "<b>&c" not in pagina


def test_sottocartella_ha_il_ritorno_alla_superiore(fs, radice):
    sotto = radice / "Esportazioni Foliarium"
    sotto.mkdir()
    assert 'href="../"' in fs.pagina_elenco(radice, sotto)
    assert 'href="../"' not in fs.pagina_elenco(radice, radice)


# ---------------------------------------------------------------------------
# Via HTTP
# ---------------------------------------------------------------------------

def test_http_elenco(server, radice):
    (radice / "partita.pdf").write_bytes(b"%PDF")
    risposta, corpo = _richiesta(server, "GET", "/")
    assert risposta.status == 200
    assert risposta.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "partita.pdf" in corpo.decode("utf-8")


def test_http_scarica_come_allegato(server, radice):
    (radice / "città.pdf").write_bytes(b"%PDF-1.4 prova")
    risposta, corpo = _richiesta(server, "GET", "/citt%C3%A0.pdf")
    assert risposta.status == 200
    assert corpo == b"%PDF-1.4 prova"
    assert risposta.headers["Content-Disposition"] == "attachment; filename*=UTF-8''citt%C3%A0.pdf"
    assert risposta.headers["X-Content-Type-Options"] == "nosniff"
    assert risposta.headers["Content-Length"] == "14"


def test_http_head_non_ha_corpo(server, radice):
    (radice / "a.csv").write_bytes(b"1;2;3")
    risposta, corpo = _richiesta(server, "HEAD", "/a.csv")
    assert risposta.status == 200
    assert corpo == b""
    assert risposta.headers["Content-Length"] == "5"


@pytest.mark.parametrize("ostile", [
    "/..%2fsegreto.txt",
    "/%2e%2e/segreto.txt",
    "/.nascosto",
    "/inesistente.pdf",
])
def test_http_percorso_ostile_404(server, radice, ostile):
    (radice / ".nascosto").write_text("x", encoding="utf-8")
    risposta, corpo = _richiesta(server, "GET", ostile)
    assert risposta.status == 404
    assert b"riservato" not in corpo


def test_http_cartella_senza_barra_finale_redirige(server, radice):
    # Senza la barra i collegamenti relativi della pagina punterebbero
    # un livello piu' su.
    (radice / "Esportazioni Foliarium").mkdir()
    risposta, _ = _richiesta(server, "GET", "/Esportazioni%20Foliarium")
    assert risposta.status == 301
    assert risposta.headers["Location"] == "Esportazioni%20Foliarium/"


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE", "PATCH"])
def test_http_altri_metodi_rifiutati(server, metodo):
    risposta, _ = _richiesta(server, metodo, "/")
    assert risposta.status == 405
    assert risposta.headers["Allow"] == "GET, HEAD"
