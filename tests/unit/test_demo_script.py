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


def _esegui(*argomenti: str, cartella: Path, ambiente: dict | None = None,
            ingresso: str = "", processori: int | None = None):
    """Lancia demo.sh con un finto `docker` in testa al PATH.

    Il finto registra ogni chiamata e le variabili che demo.sh gli passa.
    Con FINTO_DOCKER_FALLISCE (un modello di `case`) fallisce sulle chiamate
    che vi corrispondono: serve a provare che cosa resta dopo un guasto.
    """
    finti = cartella / "finti"
    finti.mkdir(exist_ok=True)
    finto_docker = finti / "docker"
    finto_docker.write_text(
        '#!/bin/sh\n'
        'echo "$*" >> "$DEMO_CARTELLA_DATI/docker-chiamato"\n'
        'echo "CPU_APP=${DEMO_CPU_APP-} CPU_DB=${DEMO_CPU_DB-} GID=${DEMO_GID_FRAMMENTI-} :: $*"'
        ' >> "$DEMO_CARTELLA_DATI/docker-ambiente"\n'
        'if [ -n "${FINTO_DOCKER_FALLISCE-}" ]; then\n'
        '    case "$*" in $FINTO_DOCKER_FALLISCE) echo "guasto simulato" >&2; exit 1 ;; esac\n'
        'fi\n'
        # Alle ispezioni risponde «healthy»: i comandi che attendono la
        # postazione non restano in attesa di un container che non esiste.
        'case "$*" in *inspect*) echo healthy ;; esac\n'
        # «caddy hash-password» legge la password da standard input.
        "case \"$*\" in *hash-password*) cat > /dev/null; echo '" + HASH + "' ;; esac\n"
        'exit 0\n',
        encoding="utf-8",
    )
    finto_docker.chmod(finto_docker.stat().st_mode | stat.S_IEXEC)
    if processori is not None:
        finto_nproc = finti / "nproc"
        finto_nproc.write_text(f"#!/bin/sh\necho {processori}\n", encoding="utf-8")
        finto_nproc.chmod(finto_nproc.stat().st_mode | stat.S_IEXEC)

    env = dict(os.environ)
    env["PATH"] = f"{finti}{os.pathsep}{env['PATH']}"
    env["DEMO_CARTELLA_DATI"] = str(cartella)
    for variabile in ("DEMO_PREFISSO", "DEMO_CARTELLA_PROXY", "DEMO_CPU_APP",
                      "DEMO_CPU_DB", "DEMO_MEM_APP", "DEMO_MEM_DB",
                      "DEMO_DOMINIO", "DEMO_INDIRIZZO_PUBBLICO"):
        env.pop(variabile, None)
    env.update(ambiente or {})
    return subprocess.run(
        ["bash", str(SCRIPT), *argomenti],
        capture_output=True, text=True, env=env, timeout=60, input=ingresso,
    )


def _docker_chiamato(cartella: Path) -> bool:
    return (cartella / "docker-chiamato").exists()


def _chiamate_docker(cartella: Path) -> list[str]:
    registro = cartella / "docker-chiamato"
    return registro.read_text(encoding="utf-8").splitlines() if registro.exists() else []


def _ambiente_docker(cartella: Path) -> list[str]:
    registro = cartella / "docker-ambiente"
    return registro.read_text(encoding="utf-8").splitlines() if registro.exists() else []


def _file_creati(cartella: Path) -> list[str]:
    return sorted(
        str(p.relative_to(cartella)) for p in cartella.rglob("*")
        if p.is_file() and "finti" not in p.parts
        and p.name not in ("docker-chiamato", "docker-ambiente")
    )


def _valori(file_env: Path) -> dict[str, str]:
    return dict(
        riga.split("=", 1) for riga in file_env.read_text(encoding="utf-8").splitlines()
        if "=" in riga and not riga.startswith("#")
    )


def _permessi(percorso: Path) -> int:
    return stat.S_IMODE(percorso.stat().st_mode)


def _indici(chiamate: list[str], *frammenti: str) -> list[int]:
    return [i for i, c in enumerate(chiamate) if all(f in c for f in frammenti)]


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


# ---------------------------------------------------------------------------
# ripristina e rimuovi
# ---------------------------------------------------------------------------

CONTENUTO_ENV = (
    "DEMO_NOME=cliente-a\nDEMO_PASSWORD=Abc123\nDEMO_DB_PASS=Xyz789\n"
    "DEMO_WS_TOKEN=" + TOKEN + "\n"
)


@pytest.fixture
def postazione(tmp_path) -> Path:
    """Cartella dati con una postazione «cliente-a» gia' registrata."""
    (tmp_path / "postazioni").mkdir()
    (tmp_path / "proxy").mkdir()
    (tmp_path / "postazioni" / "cliente-a.env").write_text(CONTENUTO_ENV, encoding="utf-8")
    (tmp_path / "proxy" / "cliente-a.caddy").write_text("# frammento\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("comando", ["ripristina", "rimuovi"])
def test_postazione_inesistente(comando, tmp_path):
    esito = _esegui(comando, "mai-creata", "--si", cartella=tmp_path)
    assert esito.returncode == 3
    assert "non esiste" in esito.stderr
    assert not _docker_chiamato(tmp_path)


@pytest.mark.parametrize("comando", ["ripristina", "rimuovi"])
def test_nome_ostile_anche_qui(comando, postazione):
    esito = _esegui(comando, "../cliente-a", "--si", cartella=postazione)
    assert esito.returncode == 2
    assert not _docker_chiamato(postazione)
    assert (postazione / "postazioni" / "cliente-a.env").exists()


def test_ripristina_cancella_i_dati_e_conserva_le_credenziali(postazione):
    esito = _esegui("ripristina", "cliente-a", cartella=postazione)
    assert esito.returncode == 0, esito.stderr
    chiamate = _chiamate_docker(postazione)
    giu = [i for i, c in enumerate(chiamate) if "foliarium-demo-cliente-a" in c and "down -v" in c]
    su = [i for i, c in enumerate(chiamate) if "foliarium-demo-cliente-a" in c and "up -d" in c]
    assert giu and su and giu[0] < su[0], chiamate
    # Stesso file, byte per byte: credenziali e token non cambiano.
    assert (postazione / "postazioni" / "cliente-a.env").read_text(encoding="utf-8") == CONTENUTO_ENV
    assert (postazione / "proxy" / "cliente-a.caddy").exists()


def test_prima_di_fermarla_la_stacca_dal_proxy(postazione):
    # Il proxy sta sulla rete della postazione: finche' vi resta collegato,
    # Docker non puo' eliminare la rete e «down» fallisce.
    _esegui("ripristina", "cliente-a", cartella=postazione)
    chiamate = _chiamate_docker(postazione)
    stacca = [i for i, c in enumerate(chiamate) if c.startswith("network disconnect")]
    giu = [i for i, c in enumerate(chiamate) if "down -v" in c]
    assert stacca and giu and stacca[0] < giu[0], chiamate
    assert "foliarium-demo-cliente-a_default foliarium-demo-proxy" in chiamate[stacca[0]]


def test_rimuovi_senza_conferma_non_tocca_nulla(postazione):
    esito = _esegui("rimuovi", "cliente-a", cartella=postazione, ingresso="un-altro-nome\n")
    assert esito.returncode == 1
    assert "annullata" in esito.stderr
    assert not _docker_chiamato(postazione)
    assert (postazione / "postazioni" / "cliente-a.env").exists()
    assert (postazione / "proxy" / "cliente-a.caddy").exists()


def test_rimuovi_senza_risposta_non_tocca_nulla(postazione):
    # Standard input chiuso (per esempio da cron): vale come un no.
    esito = _esegui("rimuovi", "cliente-a", cartella=postazione, ingresso="")
    assert esito.returncode == 1
    assert (postazione / "postazioni" / "cliente-a.env").exists()


def test_rimuovi_confermato_digitando_il_nome(postazione):
    esito = _esegui("rimuovi", "cliente-a", cartella=postazione, ingresso="cliente-a\n")
    assert esito.returncode == 0, esito.stderr
    assert not (postazione / "postazioni" / "cliente-a.env").exists()
    assert not (postazione / "proxy" / "cliente-a.caddy").exists()
    assert any("down -v" in c for c in _chiamate_docker(postazione))


def test_rimuovi_con_si_non_chiede_conferma(postazione):
    esito = _esegui("rimuovi", "cliente-a", "--si", cartella=postazione)
    assert esito.returncode == 0, esito.stderr
    assert _file_creati(postazione) == []


def test_un_prefisso_diverso_non_tocca_l_installazione_predefinita(postazione):
    # La prova automatica usa un prefisso suo: non deve mai nominare i
    # progetti dell'installazione vera.
    esito = _esegui("ripristina", "cliente-a", cartella=postazione,
                    ambiente={"DEMO_PREFISSO": "foliarium-prova"})
    assert esito.returncode == 0, esito.stderr
    chiamate = "\n".join(_chiamate_docker(postazione))
    assert "foliarium-prova-cliente-a" in chiamate
    assert "foliarium-demo" not in chiamate.replace("foliarium-demo-app:locale", "").replace("foliarium-demo-db:locale", "")


# ---------------------------------------------------------------------------
# crea: cio' che scrive, e cio' che resta se fallisce
# ---------------------------------------------------------------------------

PROXY_NON_PARTE = "*-p foliarium-demo-proxy *up -d*"
POSTAZIONE_NON_PARTE = "*-p foliarium-demo-cliente-a *up -d*"


def test_crea_scrive_credenziali_e_frammento_e_li_stampa(tmp_path):
    esito = _esegui("crea", "cliente-a", cartella=tmp_path)
    assert esito.returncode == 0, esito.stderr
    valori = _valori(tmp_path / "postazioni" / "cliente-a.env")
    assert valori["DEMO_NOME"] == "cliente-a"
    assert re.fullmatch(r"[A-Za-z0-9]{20}", valori["DEMO_PASSWORD"])
    assert re.fullmatch(r"[A-Za-z0-9]{24}", valori["DEMO_DB_PASS"])
    assert re.fullmatch(r"[a-f0-9]{64}", valori["DEMO_WS_TOKEN"])
    frammento = (tmp_path / "proxy" / "cliente-a.caddy").read_text(encoding="utf-8")
    assert f"/cliente-a/ws/{valori['DEMO_WS_TOKEN']}" in frammento
    assert HASH in frammento
    # Nel frammento la password non c'e': al proxy basta l'hash.
    assert valori["DEMO_PASSWORD"] not in frammento
    assert valori["DEMO_DB_PASS"] not in frammento
    assert f"Password  : {valori['DEMO_PASSWORD']}" in esito.stdout
    assert "/cliente-a/" in esito.stdout


def test_i_file_con_i_segreti_non_sono_leggibili_da_altri_utenti(tmp_path):
    # Il file .env contiene le password. Il frammento del proxy contiene il
    # token dello schermo, che per lo schermo vale quanto la password: chi lo
    # legge comanda la postazione senza credenziali. Su un server che ospita
    # altro, nessuno dei due deve essere leggibile da un altro utente.
    # Cartelle gia' presenti con permessi larghi vengono ristrette.
    (tmp_path / "postazioni").mkdir(mode=0o755)
    (tmp_path / "proxy").mkdir(mode=0o755)
    esito = _esegui("crea", "cliente-a", cartella=tmp_path)
    assert esito.returncode == 0, esito.stderr
    assert _permessi(tmp_path / "postazioni") == 0o700
    assert _permessi(tmp_path / "postazioni" / "cliente-a.env") == 0o600
    # Gruppo in lettura: e' da li' che il proxy legge (vedi il test seguente).
    assert _permessi(tmp_path / "proxy") == 0o750
    assert _permessi(tmp_path / "proxy" / "cliente-a.caddy") == 0o640


def test_il_proxy_legge_i_frammenti_tramite_il_gruppo(tmp_path):
    # Il proxy gira senza capability: non puo' scavalcare i permessi dei
    # file. Legge i frammenti perche' riceve come gruppo supplementare quello
    # di chi esegue demo.sh, non perche' i frammenti siano leggibili da tutti.
    proxy = _yaml("compose.proxy.yml")["services"]["proxy"]
    assert proxy["cap_drop"] == ["ALL"]
    assert proxy["cap_add"] == ["NET_BIND_SERVICE"]
    assert proxy["group_add"] == ["${DEMO_GID_FRAMMENTI:?manca DEMO_GID_FRAMMENTI}"]

    _esegui("crea", "cliente-a", cartella=tmp_path)
    avvii = [r for r in _ambiente_docker(tmp_path)
             if "-p foliarium-demo-proxy " in r and "up -d" in r]
    assert avvii, _ambiente_docker(tmp_path)
    assert all(f" GID={os.getgid()} " in r for r in avvii), avvii


@pytest.mark.parametrize("guasto", [PROXY_NON_PARTE, POSTAZIONE_NON_PARTE])
def test_crea_fallita_non_lascia_nulla(guasto, tmp_path):
    # Il proxy che non parte e' il guasto piu' probabile al primo «crea»: le
    # porte 80 e 443 gia' occupate da un altro web server. Una postazione a
    # meta' non si potrebbe ne' usare ne' ricreare con lo stesso nome.
    esito = _esegui("crea", "cliente-a", cartella=tmp_path,
                    ambiente={"FINTO_DOCKER_FALLISCE": guasto})
    assert esito.returncode == 1
    assert "creazione di «cliente-a» fallita" in esito.stderr
    assert "guasto simulato" in esito.stderr      # la causa resta visibile
    assert "Password" not in esito.stdout
    assert _file_creati(tmp_path) == []
    chiamate = _chiamate_docker(tmp_path)
    giu = _indici(chiamate, "-p foliarium-demo-cliente-a ", "down -v")
    assert giu, chiamate
    # Prima va staccata dal proxy, o Docker non puo' eliminarne la rete.
    stacca = _indici(chiamate, "network disconnect foliarium-demo-cliente-a_default")
    assert stacca and stacca[0] < giu[0], chiamate
    # Il nome si puo' riusare subito.
    assert _esegui("crea", "cliente-a", cartella=tmp_path).returncode == 0


def test_crea_fallita_non_tocca_le_altre_postazioni(postazione, tmp_path):
    # «postazione» contiene gia' cliente-a: il guasto durante la creazione di
    # un'altra non deve costarle nulla.
    esito = _esegui("crea", "cliente-b", cartella=postazione,
                    ambiente={"FINTO_DOCKER_FALLISCE": PROXY_NON_PARTE})
    assert esito.returncode == 1
    assert _file_creati(postazione) == ["postazioni/cliente-a.env", "proxy/cliente-a.caddy"]
    assert (postazione / "postazioni" / "cliente-a.env").read_text(encoding="utf-8") == CONTENUTO_ENV
    assert not _indici(_chiamate_docker(postazione), "-p foliarium-demo-cliente-a ", "down")


# ---------------------------------------------------------------------------
# ripristina --nuove-credenziali: il passaggio a un altro cliente
# ---------------------------------------------------------------------------

def test_ripristina_con_nuove_credenziali_cambia_password_e_token(postazione):
    # Chi ha usato la postazione conosce password e indirizzo dello schermo.
    # Prima di darla a un altro cliente vanno cambiati entrambi, o il primo
    # rientra nella sessione del secondo.
    esito = _esegui("ripristina", "cliente-a", "--nuove-credenziali", cartella=postazione)
    assert esito.returncode == 0, esito.stderr
    valori = _valori(postazione / "postazioni" / "cliente-a.env")
    assert valori["DEMO_NOME"] == "cliente-a"
    assert re.fullmatch(r"[A-Za-z0-9]{20}", valori["DEMO_PASSWORD"])
    assert valori["DEMO_PASSWORD"] != "Abc123"
    assert valori["DEMO_DB_PASS"] != "Xyz789"
    assert re.fullmatch(r"[a-f0-9]{64}", valori["DEMO_WS_TOKEN"])
    assert valori["DEMO_WS_TOKEN"] != TOKEN
    frammento = (postazione / "proxy" / "cliente-a.caddy").read_text(encoding="utf-8")
    assert f"/cliente-a/ws/{valori['DEMO_WS_TOKEN']}" in frammento
    assert TOKEN not in frammento
    assert HASH in frammento
    assert f"Password  : {valori['DEMO_PASSWORD']}" in esito.stdout
    assert _permessi(postazione / "postazioni" / "cliente-a.env") == 0o600
    assert _permessi(postazione / "proxy" / "cliente-a.caddy") == 0o640

    chiamate = _chiamate_docker(postazione)
    giu = _indici(chiamate, "-p foliarium-demo-cliente-a ", "down -v")
    su = _indici(chiamate, "-p foliarium-demo-cliente-a ", "up -d")
    ricarica = _indici(chiamate, "caddy reload")
    # Dati cancellati, poi ripartenza; e il proxy rilegge la configurazione,
    # altrimenti continuerebbe ad accettare la password di prima.
    assert giu and su and ricarica and giu[0] < su[0] < ricarica[-1], chiamate


def test_ripristina_rifiuta_un_opzione_sconosciuta(postazione):
    esito = _esegui("ripristina", "cliente-a", "--nuove-credenzial", cartella=postazione)
    assert esito.returncode == 2
    assert not _docker_chiamato(postazione)
    assert (postazione / "postazioni" / "cliente-a.env").read_text(encoding="utf-8") == CONTENUTO_ENV


def test_nuove_credenziali_non_riuscite_lasciano_quelle_di_prima(postazione):
    # Se l'hash della nuova password non si puo' calcolare, la postazione
    # deve restare com'era: non spenta, e non con credenziali a meta'.
    esito = _esegui("ripristina", "cliente-a", "--nuove-credenziali", cartella=postazione,
                    ambiente={"FINTO_DOCKER_FALLISCE": "*hash-password*"})
    assert esito.returncode == 1
    assert (postazione / "postazioni" / "cliente-a.env").read_text(encoding="utf-8") == CONTENUTO_ENV
    assert (postazione / "proxy" / "cliente-a.caddy").read_text(encoding="utf-8") == "# frammento\n"
    assert not _indici(_chiamate_docker(postazione), "down -v")


def test_la_guida_non_prescrive_di_riusare_le_credenziali_fra_clienti():
    guida = (DEMO / "README.md").read_text(encoding="utf-8")
    assert "--nuove-credenziali" in guida
    assert "fra un cliente e l'altro" not in guida.split("--nuove-credenziali")[0]


# ---------------------------------------------------------------------------
# Limiti di risorse
# ---------------------------------------------------------------------------

def test_ogni_container_di_una_postazione_ha_limiti_di_memoria_cpu_e_processi():
    # Le postazioni condividono una macchina: nessuna deve poterla occupare
    # tutta a danno delle altre, ne' di cio' che il server ospita gia'.
    servizi = _yaml("compose.postazione.yml")["services"]
    for nome, servizio in servizi.items():
        assert "mem_limit" in servizio, nome
        assert "cpus" in servizio, nome
        assert isinstance(servizio.get("pids_limit"), int), nome
        assert servizio["cap_drop"] == ["ALL"], nome
        assert "no-new-privileges:true" in servizio["security_opt"], nome
    assert servizi["app"]["cpus"] == "${DEMO_CPU_APP:-2}"
    assert servizi["db"]["cpus"] == "${DEMO_CPU_DB:-1}"


def test_il_database_non_gira_da_root():
    db = _yaml("compose.postazione.yml")["services"]["db"]
    assert db["user"] == "postgres"


def test_il_proxy_ha_un_limite_di_memoria():
    assert "mem_limit" in _yaml("compose.proxy.yml")["services"]["proxy"]


@pytest.mark.parametrize("processori, atteso_app, atteso_db", [
    (1, "1", "1"),
    (2, "2", "1"),
    (16, "2", "1"),
])
def test_il_limite_di_cpu_non_supera_i_processori_della_macchina(
        processori, atteso_app, atteso_db, postazione):
    # Docker rifiuta di avviare un container con un limite di CPU superiore
    # ai processori presenti: su un server piccolo «crea» fallirebbe.
    esito = _esegui("ripristina", "cliente-a", cartella=postazione, processori=processori)
    assert esito.returncode == 0, esito.stderr
    avvii = [r for r in _ambiente_docker(postazione)
             if "-p foliarium-demo-cliente-a " in r and "up -d" in r]
    assert avvii and all(
        r.startswith(f"CPU_APP={atteso_app} CPU_DB={atteso_db} ") for r in avvii), avvii


def test_i_limiti_di_cpu_si_cambiano_in_demo_env(postazione):
    (postazione / "demo.env").write_text("DEMO_CPU_APP=0.5\nDEMO_CPU_DB=0.25\n", encoding="utf-8")
    esito = _esegui("ripristina", "cliente-a", cartella=postazione, processori=8)
    assert esito.returncode == 0, esito.stderr
    avvii = [r for r in _ambiente_docker(postazione)
             if "-p foliarium-demo-cliente-a " in r and "up -d" in r]
    assert avvii and all(r.startswith("CPU_APP=0.5 CPU_DB=0.25 ") for r in avvii), avvii
    esempio = (DEMO / "demo.env.example").read_text(encoding="utf-8")
    assert "DEMO_CPU_APP" in esempio and "DEMO_CPU_DB" in esempio


# ---------------------------------------------------------------------------
# Guasti che non devono passare inosservati
# ---------------------------------------------------------------------------

SEGNALE_INIT = "foliarium_init_completato"


def test_il_database_e_sano_solo_a_inizializzazione_conclusa():
    # Se uno script iniziale fallisce, il container del database esce e
    # viene riavviato; al secondo avvio l'immagine trova la cartella dei dati
    # gia' presente, salta l'inizializzazione e risponde, con uno schema a
    # meta' e senza utente «demo». Solo init.sh sa di essere arrivato in
    # fondo: lascia un segnale, e il controllo di salute lo pretende.
    db = _yaml("compose.postazione.yml")["services"]["db"]
    controllo = " ".join(db["healthcheck"]["test"])
    assert "pg_isready" in controllo
    assert f'test -f "$$PGDATA/{SEGNALE_INIT}"' in controllo
    init = (RADICE / "docker" / "postgres" / "init.sh").read_text(encoding="utf-8")
    righe = [r.strip() for r in init.splitlines() if r.strip() and not r.strip().startswith("#")]
    # Il segnale si lascia dopo l'ultimo script applicato, non prima.
    ultima_applicazione = max(i for i, r in enumerate(righe) if r.startswith(("applica ", "applica_tollerante ")))
    segnale = [i for i, r in enumerate(righe) if SEGNALE_INIT in r and r.startswith("touch ")]
    assert segnale and segnale[0] > ultima_applicazione, righe[-6:]


def test_se_il_ciclo_che_rilancia_il_programma_muore_il_container_esce():
    # Con il ciclo morto nessuno rilancerebbe piu' Foliarium: la postazione
    # resterebbe accesa con la scrivania vuota. Uscendo, Docker la riavvia.
    avvio = (DEMO / "avvio.sh").read_text(encoding="utf-8")
    attese = [r for r in avvio.splitlines() if r.strip().startswith("wait -n")]
    assert len(attese) == 1, attese
    for processo in ("PID_SCHERMO", "PID_FINESTRE", "PID_PONTE", "PID_FILE", "PID_CICLO"):
        assert f'"${processo}"' in attese[0], processo


def test_la_pagina_dello_schermo_non_si_puo_incorniciare():
    # Una pagina altrui che incornicia la demo potrebbe far cliccare il
    # cliente, gia' autenticato, su un programma che non vede.
    caddyfile = (DEMO / "Caddyfile").read_text(encoding="utf-8")
    assert re.search(r"^\s*X-Frame-Options\s+DENY\s*$", caddyfile, re.M)


# Moduli in radice che nell'immagine NON devono esserci, e perche'.
MODULI_FUORI_DALL_IMMAGINE = {
    "generate_key.py", "generate_license.py",       # firmano le licenze
    "setup_database.py", "setup_db.py",             # installazione su Windows
    "migrate_database.py", "_leggi_config.py",      # manutenzione
    "run_api.py", "webview_main.py",                # interfaccia web
}


def test_ogni_modulo_in_radice_e_copiato_nell_immagine_o_escluso_di_proposito():
    # I moduli in radice entrano nell'immagine per elenco. Uno nuovo,
    # dimenticato, non farebbe fallire la build: mancherebbe al momento
    # dell'import, magari al clic di un cliente. Chi ne aggiunge uno deve
    # decidere qui da che parte sta.
    dockerfile = (DEMO / "Dockerfile").read_text(encoding="utf-8")
    blocco = re.search(r"WORKDIR /opt/foliarium\nCOPY (.*?) \./\n", dockerfile, re.S)
    assert blocco, "elenco dei moduli in radice non trovato nel Dockerfile"
    copiati = set(re.findall(r"[\w]+\.py", blocco.group(1)))
    in_radice = {p.name for p in RADICE.glob("*.py")}
    assert copiati & MODULI_FUORI_DALL_IMMAGINE == set()
    assert in_radice == copiati | MODULI_FUORI_DALL_IMMAGINE, (
        f"non classificati: {sorted(in_radice - copiati - MODULI_FUORI_DALL_IMMAGINE)}; "
        f"elencati ma assenti: {sorted((copiati | MODULI_FUORI_DALL_IMMAGINE) - in_radice)}"
    )


# ---------------------------------------------------------------------------
# Regressioni
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("script", ["demo.sh", "prova.sh", "avvio.sh"])
def test_niente_grep_q_in_coda_a_una_pipe_con_pipefail(script):
    # `comando | grep -q testo` con `set -o pipefail` fallisce a caso: grep
    # esce appena trova il testo, il comando a monte riceve SIGPIPE e la
    # pipe intera risulta fallita anche se il testo c'era. In CI la verifica
    # «la finestra principale esiste» falliva cosi' con la finestra a schermo.
    # Si cattura l'uscita in una variabile e la si confronta con `case`.
    testo = (DEMO / script).read_text(encoding="utf-8")
    if "pipefail" not in testo:
        pytest.skip("lo script non usa pipefail")
    colpevoli = [
        riga.strip() for riga in testo.splitlines()
        if re.search(r"\|\s*grep\s+(-\w*q\w*|--quiet)", riga) and not riga.lstrip().startswith("#")
    ]
    assert colpevoli == []
