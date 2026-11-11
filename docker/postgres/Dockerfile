# Versione maggiore di PostgreSQL. Il default serve lo stack web
# (docker-compose.yml in radice); la demo la imposta a quella del bundle
# Windows, vedi docker/demo/.
ARG PG_MAJOR=14
# Immagine di base sostituibile: serve dove le build escono da un proxy che
# richiede una CA propria. Normalmente non va toccata.
ARG BASE_IMAGE=postgres:${PG_MAJOR}-bookworm
FROM ${BASE_IMAGE}

# Fuso orario italiano. initdb lo legge da qui e lo scrive in postgresql.conf.
# Deve coincidere con quello dell'applicazione: le date che il database
# registra (accessi, audit) vengono mostrate cosi' come sono, e con il
# default dell'immagine (UTC) risulterebbero un'ora o due indietro.
ENV TZ=Europe/Rome

# Localizzazione (gli script Foliarium si aspettano locale italiano per ordinamenti)
RUN apt-get update \
    && apt-get install -y --no-install-recommends locales \
    && sed -i '/it_IT.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# NOTA: il build context è la root del repo (vedi docker-compose.yml).
# Copio sql_scripts/ in /opt/foliarium-sql/ e l'init runner in
# /docker-entrypoint-initdb.d/ (eseguito al primo avvio).
COPY sql_scripts/                       /opt/foliarium-sql/
COPY docker/postgres/init.sh            /docker-entrypoint-initdb.d/00-init.sh
RUN chmod +x /docker-entrypoint-initdb.d/00-init.sh
