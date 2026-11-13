# Immagine della demo: l'applicazione desktop Foliarium su uno schermo
# virtuale, raggiungibile dal browser.
#
# Il contesto di build e' la radice del repository:
#   docker build -f docker/demo/Dockerfile -t foliarium-demo-app:locale .
# Cio' che entra nel contesto lo decide docker/demo/Dockerfile.dockerignore,
# che ha precedenza sul .dockerignore in radice (pensato per lo stack web:
# esclude docs/, di cui qui il manuale interno ha bisogno).

# Immagine di base sostituibile: serve dove le build escono da un proxy che
# richiede una CA propria. Normalmente non va toccata.
ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

# Stessa versione maggiore del server: pg_dump rifiuta di lavorare contro un
# server piu' recente, e un dump piu' recente non si ripristina su uno piu'
# vecchio. La imposta docker/demo/demo.sh, insieme a quella dell'immagine db.
ARG PG_MAJOR=16

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# - librerie native di Qt: quelle del Dockerfile in radice, piu' libatomic1,
#   richiesta da QtPdf (che l'applicazione importa all'avvio)
# - schermo virtuale con server VNC, gestore di finestre, client noVNC
# - niente browser e niente caratteri Microsoft: vedi docker/demo/README.md
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libegl1 libglib2.0-0 libxkbcommon0 libxkbcommon-x11-0 \
        libdbus-1-3 libfontconfig1 libfreetype6 libatomic1 \
        libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
        libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-sync1 \
        libxcb-xfixes0 libxcb-xkb1 libxcb-xinerama0 \
        tigervnc-standalone-server openbox novnc websockify \
        x11-utils xdg-utils procps curl ca-certificates \
        locales tzdata \
    && sed -i '/it_IT.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && ln -snf /usr/share/zoneinfo/Europe/Rome /etc/localtime \
    && echo "Europe/Rome" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Client PostgreSQL dal repository PGDG (come .devcontainer/setup.sh): Debian
# offre una sola versione, che puo' non coincidere con quella del server.
RUN . /etc/os-release \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends "postgresql-client-${PG_MAJOR}" \
    && rm -rf /var/lib/apt/lists/*

# Dipendenze Python: l'elenco dell'applicazione desktop, senza varianti, per
# non avere un terzo requirements da tenere allineato.
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Portachiavi. Foliarium conserva nel portachiavi di sistema la chiave dei
# backup cifrati (che sono l'opzione predefinita) e le password SMTP e del
# database. In un container un portachiavi non c'e', e il backup dalla GUI
# fallirebbe. keyrings.alt ne fornisce uno su file, attivato piu' sotto con
# PYTHON_KEYRING_BACKEND: sta nella cartella personale della postazione e
# sparisce con «ripristina». Non e' cifrato: va bene per dati dimostrativi,
# non per un'installazione vera.
RUN pip install "keyrings.alt>=5,<6"

# Aspetto e file. In uno strato a parte, dopo le dipendenze Python: cambiare
# questo elenco non deve costringere a reinstallarle.
# - caratteri liberi al posto di quelli di Windows chiesti dai temi (gli
#   alias stanno in fonts-foliarium.conf) e caratteri per le emoji;
# - x11-xserver-utils: xsetroot, per il colore di fondo dello schermo;
# - file: serve a xdg-open per riconoscere il tipo di un file.
RUN apt-get update && apt-get install -y --no-install-recommends \
        fontconfig fonts-liberation2 fonts-crosextra-carlito fonts-open-sans \
        fonts-noto-core fonts-noto-color-emoji \
        x11-xserver-utils file \
    && rm -rf /var/lib/apt/lists/*
COPY docker/demo/fonts-foliarium.conf /etc/fonts/conf.d/45-foliarium.conf
RUN fc-cache -f

# Utente senza privilegi. La cartella del socket X va creata da root: Xvnc,
# avviato da utente normale, non puo' darle i permessi che si aspetta.
RUN useradd --create-home --uid 1000 --shell /bin/bash foliarium \
    && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

# --- Applicazione ----------------------------------------------------------
# Elenco esplicito dei moduli in radice: generate_key.py e generate_license.py
# firmano le licenze e in un'immagine esposta al pubblico non devono esserci.
WORKDIR /opt/foliarium
COPY app_paths.py app_utils.py catasto_db_manager.py catasto_exceptions.py \
     config.py dialogs.py gui_main.py gui_widgets.py \
     partita_workflow_widgets.py search_widgets.py validators.py \
     mkdocs.yml ./
COPY foliarium/   ./foliarium/
COPY db/          ./db/
COPY core/        ./core/
COPY api/         ./api/
COPY utils/       ./utils/
COPY styles/      ./styles/
COPY resources/   ./resources/
COPY sql_scripts/ ./sql_scripts/
COPY docs/        ./docs/

# --- Strumenti della demo --------------------------------------------------
COPY docker/demo/avvio.sh docker/demo/controllo-salute.sh \
     docker/demo/file_server.py docker/demo/cattura_schermo.py \
     docker/demo/visualizza_pdf.py docker/demo/openbox-rc.xml \
     /opt/foliarium-demo/
COPY docker/demo/web/ /opt/foliarium-demo/web/
COPY docker/demo/esempi-import/ /opt/foliarium-demo/esempi-import/

# I PDF che Foliarium apre con «il programma predefinito» (QDesktopServices,
# cioe' xdg-open) finiscono nell'anteprima della demo. Senza un programma
# associato il pulsante «Apri» non farebbe nulla.
COPY docker/demo/foliarium-pdf.desktop /usr/share/applications/foliarium-pdf.desktop
RUN printf '[Default Applications]\napplication/pdf=foliarium-pdf.desktop\n' \
        > /usr/share/applications/mimeapps.list
RUN chmod 755 /opt/foliarium-demo/avvio.sh /opt/foliarium-demo/controllo-salute.sh \
    && ln -s /usr/share/novnc /opt/foliarium-demo/web/novnc \
    && python -m compileall -q /opt/foliarium /opt/foliarium-demo

# DB_SSLMODE=prefer: per un host che non e' "localhost" l'applicazione
# pretende TLS (db/base.py, _resolve_sslmode), ma il database della
# postazione e' un container sulla stessa macchina, raggiunto su una rete
# Docker privata, e non ha certificati. Senza questa riga la connessione
# fallisce e il programma resta fermo su un errore modale.
ENV LANG=it_IT.UTF-8 \
    LC_ALL=it_IT.UTF-8 \
    TZ=Europe/Rome \
    DISPLAY=:1 \
    QT_QPA_PLATFORM=xcb \
    FOLIARIUM_DEMO=1 \
    DB_SSLMODE=prefer \
    PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring \
    XDG_RUNTIME_DIR=/tmp/runtime-foliarium \
    HOME=/home/foliarium

USER foliarium
WORKDIR /home/foliarium

# 6080: pagina e WebSocket dello schermo — 6081: download dei file.
# La porta VNC (5900) ascolta solo in locale e non va esposta.
EXPOSE 6080 6081

HEALTHCHECK --interval=15s --timeout=5s --start-period=120s --retries=4 \
    CMD /opt/foliarium-demo/controllo-salute.sh

ENTRYPOINT ["/opt/foliarium-demo/avvio.sh"]
