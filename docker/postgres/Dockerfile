FROM postgres:14-bookworm

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
