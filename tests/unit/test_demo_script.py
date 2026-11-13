"""
tests/unit/test_demo_script.py
==============================
Script di gestione delle postazioni della demo (`docker/demo/demo.sh`) e
file di configurazione che usa.

Qui non si avvia Docker: i test sostituiscono `docker` con un finto
eseguibile che si limita a registrare di essere stato chiamato. Si verifica
cio' che deve valere PRIMA che Docker entri in gioco (i nomi ostili vanno
respinti senza effetti) e la forma di cio' che lo script genera, in
particolare la configurazione del proxy, da cui dipende chi puo' vedere lo
schermo di una postazione.

La prova con i container veri e' `docker/demo/prova.sh`.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]
DEMO = RADICE / "docker" / "demo"
SCRIPT = DEMO / "demo.sh"

TOKEN = "ab" * 32
HASH = "$2a$14$abcdefghijklmnopqrstuuABCDEFGHIJKLMNOPQRSTUVWXYZ0123456"


def _esegui(*argomenti: str, cartella: Path, ambiente: dict | None = None):
    """Lancia demo.sh con un finto `docker` in testa al PATH."""
    finti = cartella / "finti"
    finti.mkdir(exist_ok=True)
    finto_docker = finti / "docker"
    finto_docker.write_text(
        '#!/bin/sh\ntouch "$DEMO_CARTELLA_DATI/docker-chiamato"\nexit 0\n',
        encoding="utf-8",
    )
    finto_docker.chmod(finto_docker.stat().st_mode | stat.S_IEXEC)

    env = dict(os.environ)
    env["PATH"] = f"{finti}{os.pathsep}{env['PATH']}"
    env["DEMO_CARTELLA_DATI"] = str(cartella)
    env.pop("DEMO_PREFISSO", None)
    env.update(ambiente or {})
    return subprocess.run(
        ["bash", str(SCRIPT), *argomenti],
        capture_output=True, text=True, env=env, timeout=60,
    )


def _docker_chiamato(cartella: Path) -> bool:
    return (cartella / "docker-chiamato").exists()


def _file_creati(cartella: Path) -> list[str]:
    return sorted(
        str(p.relative_to(cartella)) for p in cartella.rglob("*")
        if p.is_file() and "finti" not in p.parts
    )


# ---------------------------------------------------------------------------
# Uso e nomi
# ---------------------------------------------------------------------------

def test_sintassi_bash():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0


def test_senza_argomenti_mostra_i_cinque_comandi(tmp_path):
    esito = _esegui(cartella=tmp_path)
    assert esito.returncode == 2
    for comando in ("costruisci", "crea", "ripristina", "rimuovi", "elenco"):
        assert comando in esito.stderr
    assert not _docker_chiamato(tmp_path)


def test_comando_sconosciuto(tmp_path):
    esito = _esegui("distruggi-tutto", cartella=tmp_path)
    assert esito.returncode == 2
    assert not _docker_chiamato(tmp_path)


@pytest.mark.parametrize("nome", [
    "", "A", "Cliente", "../x", "a b", "a/b", "1cliente", "x", "a" * 32,
    "nome;rm", "-n", "a_b", "a.b", "nome\nnuovo", "$(id)", "città",
])
def test_nome_non_valido_rifiutato_senza_effetti(nome, tmp_path):
    # Il nome finisce in percorsi, nomi di progetto Compose e configurazione
    # del proxy: va respinto prima di toccare Docker o il disco.
    esito = _esegui("crea", nome, cartella=tmp_path)
    assert esito.returncode == 2
    assert "nome non valido" in esito.stderr.lower()
    assert not _docker_chiamato(tmp_path)
    assert _file_creati(tmp_path) == []


def test_crea_senza_nome(tmp_path):
    esito = _esegui("crea", cartella=tmp_path)
    assert esito.returncode == 2
    assert not _docker_chiamato(tmp_path)


def test_nome_riservato(tmp_path):
    # Il progetto Compose del proxy si chiama <prefisso>-proxy.
    esito = _esegui("crea", "proxy", cartella=tmp_path)
    assert esito.returncode == 2
    assert "riservato" in esito.stderr.lower()
    assert _file_creati(tmp_path) == []


def test_crea_su_nome_esistente(tmp_path):
    (tmp_path / "postazioni").mkdir()
    (tmp_path / "postazioni" / "doppia.env").write_text("DEMO_NOME=doppia\n", encoding="utf-8")
    esito = _esegui("crea", "doppia", cartella=tmp_path)
    assert esito.returncode == 3
    assert "esiste" in esito.stderr.lower()
    assert not _docker_chiamato(tmp_path)
    assert (tmp_path / "postazioni" / "doppia.env").read_text(encoding="utf-8") == "DEMO_NOME=doppia\n"


def test_elenco_senza_postazioni(tmp_path):
    esito = _esegui("elenco", cartella=tmp_path)
    assert esito.returncode == 0
    assert "Nessuna postazione" in esito.stdout
    assert not _docker_chiamato(tmp_path)


# ---------------------------------------------------------------------------
# Configurazione del proxy generata per una postazione
# ---------------------------------------------------------------------------

@pytest.fixture
def frammento(tmp_path) -> str:
    esito = _esegui("_frammento", "cliente-a", HASH, TOKEN, cartella=tmp_path)
    assert esito.returncode == 0, esito.stderr
    assert not _docker_chiamato(tmp_path)
    return esito.stdout


def _blocchi(frammento: str) -> dict[str, str]:
    """Blocchi di primo livello del frammento, per riga d'intestazione."""
    blocchi: dict[str, str] = {}
    corrente, righe, profondita = None, [], 0
    for riga in frammento.splitlines():
        pulita = riga.strip()
        if profondita == 0 and pulita.endswith("{"):
            corrente, righe = pulita[:-1].strip(), []
        profondita += pulita.count("{") - pulita.count("}")
        if corrente is not None:
            righe.append(riga)
            if profondita == 0:
                blocchi[corrente] = "\n".join(righe)
                corrente = None
    return blocchi


def test_il_websocket_passa_solo_con_il_token(frammento):
    blocchi = _blocchi(frammento)
    schermo = blocchi[f"handle /cliente-a/ws/{TOKEN}"]
    # Senza credenziali Basic (Safari non le invia sui WebSocket): lo
    # protegge il token, che sta nel percorso.
    assert "basic_auth" not in schermo
    assert "reverse_proxy app-cliente-a:6080" in schermo
    assert "rewrite * /websockify" in schermo


def test_tutto_il_resto_chiede_le_credenziali(frammento):
    blocchi = _blocchi(frammento)
    protetti = [
        "handle /cliente-a/sessione.json",
        "handle /cliente-a/file/*",
        "handle /cliente-a/*",
    ]
    for intestazione in protetti:
        assert "basic_auth" in blocchi[intestazione], intestazione
        assert HASH in blocchi[intestazione], intestazione
    # Nessun altro blocco oltre a quello del WebSocket e' senza credenziali.
    senza = [i for i, corpo in blocchi.items() if "basic_auth" not in corpo]
    assert senza == [f"handle /cliente-a/ws/{TOKEN}"]


def test_il_token_viene_consegnato_solo_dalla_pagina_di_sessione(frammento):
    blocchi = _blocchi(frammento)
    sessione = blocchi["handle /cliente-a/sessione.json"]
    assert f'{{"ws":"ws/{TOKEN}"}}' in sessione
    assert "no-store" in sessione
    assert frammento.count(TOKEN) == 2  # percorso del WebSocket + sessione.json


def test_le_destinazioni_sono_quelle_della_postazione(frammento):
    blocchi = _blocchi(frammento)
    file = blocchi["handle /cliente-a/file/*"]
    assert "reverse_proxy app-cliente-a:6081" in file
    assert "uri strip_prefix /cliente-a/file" in file
    pagina = blocchi["handle /cliente-a/*"]
    assert "reverse_proxy app-cliente-a:6080" in pagina
    assert "uri strip_prefix /cliente-a" in pagina
    assert "redir /cliente-a /cliente-a/" in frammento


def test_solo_blocchi_handle(frammento):
    # In Caddy `handle` e `handle_path` sono direttive diverse e vengono
    # ordinate per tipo prima che per percorso: mescolarle farebbe vincere
    # un blocco generico su uno specifico. Con i soli `handle` l'ordine e'
    # quello del percorso piu' lungo, cioe' quello voluto.
    assert "handle_path" not in frammento


def test_il_frammento_rifiuta_un_nome_ostile(tmp_path):
    esito = _esegui("_frammento", "a/*", HASH, TOKEN, cartella=tmp_path)
    assert esito.returncode == 2


# ---------------------------------------------------------------------------
# File Compose
# ---------------------------------------------------------------------------

def _yaml(nome: str) -> dict:
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load((DEMO / nome).read_text(encoding="utf-8"))


def test_la_postazione_non_pubblica_porte_e_non_costruisce():
    servizi = _yaml("compose.postazione.yml")["services"]
    assert set(servizi) == {"app", "db"}
    for nome, servizio in servizi.items():
        assert "ports" not in servizio, f"{nome} non deve pubblicare porte sull'host"
        assert "build" not in servizio, f"{nome}: le immagini le produce `costruisci`"
        assert servizio["restart"] == "unless-stopped"


def test_il_container_del_programma_e_senza_privilegi():
    app = _yaml("compose.postazione.yml")["services"]["app"]
    assert app["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in app["security_opt"]
    assert app["init"] is True
    assert app["depends_on"]["db"]["condition"] == "service_healthy"
    assert any(str(v).endswith(":/home/foliarium") for v in app["volumes"])
    assert "docker.sock" not in (DEMO / "compose.postazione.yml").read_text(encoding="utf-8")


def test_il_database_riceve_la_password_della_demo():
    db = _yaml("compose.postazione.yml")["services"]["db"]
    assert "FOLIARIUM_DEMO_PASSWORD" in db["environment"]
    assert "pg_isready" in " ".join(db["healthcheck"]["test"])
    # Via TCP: durante l'inizializzazione postgres ascolta solo sul socket,
    # e il programma non deve partire prima che sia finita.
    assert "-h 127.0.0.1" in " ".join(db["healthcheck"]["test"])


def test_solo_il_proxy_pubblica_porte():
    base = _yaml("compose.proxy.yml")["services"]["proxy"]
    assert "ports" not in base
    pubblico = _yaml("compose.proxy.pubblico.yml")["services"]["proxy"]["ports"]
    assert any(str(p).startswith("80:") for p in pubblico)
    assert any(str(p).startswith("443:") for p in pubblico)
    locale = _yaml("compose.proxy.locale.yml")["services"]["proxy"]["ports"]
    # Dietro un web server esistente il proxy non deve essere raggiungibile
    # dall'esterno saltando HTTPS.
    assert all(str(p).startswith("127.0.0.1:") for p in locale)


def test_il_proxy_non_vede_le_password_in_chiaro():
    # I file .env delle postazioni contengono le password; al proxy servono
    # solo gli hash. Deve montare la cartella dei frammenti, non quella dei .env.
    testo = (DEMO / "compose.proxy.yml").read_text(encoding="utf-8")
    assert "DEMO_CARTELLA_PROXY" in testo
    assert "postazioni" not in re.sub(r"#.*", "", testo).replace("/etc/caddy/postazioni", "")


def test_il_caddyfile_importa_i_frammenti_e_chiude_il_resto():
    caddyfile = (DEMO / "Caddyfile").read_text(encoding="utf-8")
    assert "{$DEMO_SITO}" in caddyfile
    assert "import /etc/caddy/postazioni/*.caddy" in caddyfile
    assert "404" in caddyfile
    assert "noindex" in caddyfile


def test_i_dati_delle_postazioni_non_entrano_in_git_ne_nell_immagine():
    gitignore = (RADICE / ".gitignore").read_text(encoding="utf-8")
    dockerignore = (DEMO / "Dockerfile.dockerignore").read_text(encoding="utf-8")
    for percorso in ("docker/demo/postazioni", "docker/demo/proxy", "docker/demo/demo.env"):
        assert percorso in gitignore, percorso
        assert percorso in dockerignore, percorso
