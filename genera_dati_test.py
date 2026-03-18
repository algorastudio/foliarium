#!/usr/bin/env python3
"""
genera_dati_test.py — Generatore di dati di test per Foliarium

Popola il database con dati attendibili e realistici che coprono tutte le
casistiche dell'applicazione, inclusi workflow complessi multi-step.

SCENARI COPERTI
  Entità base:
    · 6 comuni (1 soppresso)
    · 3 periodi storici, tutti i tipi di località
    · 13 possessori (attivi e non attivi)
    · Localita varie per ogni comune

  Workflow partite:
    1.  Partita attiva semplice (1 possessore)
    2.  Partita con suffisso (es. "bis")
    3.  Catena vendite A→B→C (3 passaggi)
    4.  Successione ereditaria
    5.  Frazionamento 1→2 lotti
    6.  Proprietà pro-indiviso (2 possessori con quote 1/2)
    7.  Possessore con più partite in comuni diversi
    8.  Partita inattiva senza successori (estinta)
    9.  Partita principale + secondaria (partita_relazione)
    10. Donazione
    11. Divisione coniugale 1→2
    12. Sentenza giudiziale / Usucapione
    13. Permuta

  Entità collegate:
    · Immobili (vari: Casa, Terreno, Fabbricato rurale, Magazzino, Laboratorio)
    · Variazioni (tutti i tipi: Vendita, Successione, Frazionamento, Divisione,
                  Trasferimento, Variazione)
    · Contratti (tutti i tipi: Atto di Compravendita, Dichiarazione di
                  Successione, Atto di Donazione, Sentenza Giudiziale,
                  Atto di Divisione, Permuta, Usucapione, Scrittura Privata)
    · Documenti storici con rilevanze diverse (primaria/secondaria/correlata)
    · Nomi storici di comuni
    · Registri partite e matricole
    · Consultazioni archivio
    · Utenti (admin, archivista, consultatore) con sessioni

USO
  python genera_dati_test.py [--no-reset] [--no-confirm]

  --no-reset    Non cancella i dati esistenti (aggiunge soltanto)
  --no-confirm  Non chiede conferma prima di procedere

VARIABILI D'AMBIENTE
  DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT  (stesse dell'app)
"""

import argparse
import os
import sys
import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

SCHEMA = "catasto"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hash(plain: str) -> str:
    """Hasha una password con bcrypt (rounds=10). Fallback sha256 se bcrypt assente."""
    if _HAS_BCRYPT:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=10)).decode()
    import hashlib
    # ATTENZIONE: questo hash non è sicuro — usare solo se bcrypt non è disponibile
    return "$sha256-fallback$" + hashlib.sha256(plain.encode()).hexdigest()


def _db_params() -> Dict[str, Any]:
    return dict(
        host=os.environ.get("DB_HOST", "localhost"),
        dbname=os.environ.get("DB_NAME", "catasto_storico"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", ""),
        port=int(os.environ.get("DB_PORT", "5432")),
        options=f"-c search_path={SCHEMA},public",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Generatore principale
# ─────────────────────────────────────────────────────────────────────────────

class DataGenerator:
    def __init__(self, conn: psycopg2.extensions.connection, reset: bool):
        self.conn = conn
        self.conn.autocommit = False
        self.cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.reset = reset
        self.ids: Dict[str, Any] = {}   # registro di tutti gli ID generati
        self.stats: Dict[str, int] = {} # contatori per il riepilogo finale

    # ── utilità interne ──────────────────────────────────────────────────────

    def _q(self, sql: str, params=None) -> Optional[Dict]:
        self.cur.execute(sql, params)
        if self.cur.description:
            return self.cur.fetchone()
        return None

    def _insert(self, table: str, row: Dict[str, Any]) -> int:
        cols = ", ".join(row.keys())
        phs  = ", ".join(["%s"] * len(row))
        sql  = f"INSERT INTO {table} ({cols}) VALUES ({phs}) RETURNING id"
        result = self._q(sql, list(row.values()))
        return result["id"]

    def _count(self, entity: str, n: int = 1):
        self.stats[entity] = self.stats.get(entity, 0) + n

    def _tid(self, key: str) -> int:
        """Recupera un ID registrato; solleva KeyError con messaggio utile."""
        if key not in self.ids:
            raise KeyError(f"ID '{key}' non trovato — verifica l'ordine di inserimento")
        return self.ids[key]

    # ── orchestrazione ───────────────────────────────────────────────────────

    def run(self):
        try:
            if self.reset:
                self._reset()
            self._periodi_storici()
            self._tipi_localita()
            self._comuni()
            self._localita()
            self._possessori()
            # ── workflow ──
            self._s01_partita_semplice()
            self._s02_suffisso()
            self._s03_catena_vendite()
            self._s04_successione()
            self._s05_frazionamento()
            self._s06_pro_indiviso()
            self._s07_possessore_multi_partita()
            self._s08_estinta()
            self._s09_principale_secondaria()
            self._s10_donazione()
            self._s11_divisione()
            self._s12_sentenza()
            self._s13_permuta()
            # ── entità collegate ──
            self._documenti_storici()
            self._nomi_storici()
            self._registri()
            self._consultazioni()
            self._utenti()
            self._sessioni()
            self.conn.commit()
            self._summary()
        except Exception:
            self.conn.rollback()
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # Reset
    # ─────────────────────────────────────────────────────────────────────────

    def _reset(self):
        print("⚠  Reset dati in corso...")
        # Truncate in ordine inverso rispetto alle FK; CASCADE gestisce il resto
        self.cur.execute("""
            TRUNCATE
                sessioni_accesso, utente_permesso, utente,
                consultazione,
                documento_partita, documento_storico,
                nome_storico,
                contratto, variazione,
                partita_relazione,
                immobile, partita_possessore,
                partita, possessore, localita,
                registro_matricole, registro_partite,
                comune
            CASCADE
        """)
        print("   ✓ Tabelle svuotate\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Lookup tables
    # ─────────────────────────────────────────────────────────────────────────

    def _periodi_storici(self):
        print("📅 Periodi storici...")
        periodi = [
            ("Regno di Sardegna",    1720, 1861,
             "Periodo del Regno di Sardegna prima dell'unità d'Italia"),
            ("Regno d'Italia",       1861, 1946,
             "Dall'Unità d'Italia alla Costituzione Repubblicana"),
            ("Repubblica Italiana",  1946, None,
             "Dalla Costituzione in poi"),
        ]
        for nome, inizio, fine, descr in periodi:
            row = self._q(
                "INSERT INTO periodo_storico (nome, anno_inizio, anno_fine, descrizione)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (nome) DO UPDATE SET anno_inizio=EXCLUDED.anno_inizio"
                " RETURNING id",
                (nome, inizio, fine, descr),
            )
            self.ids[f"periodo_{nome[:3].lower()}"] = row["id"]  # sard/reg/rep
        self._count("periodo_storico", 3)
        print(f"   ✓ 3 periodi\n")

    def _tipi_localita(self):
        print("🏷  Tipi di località...")
        tipi = [
            "Via", "Viale", "Corso", "Piazza", "Vicolo", "Largo",
            "Salita", "Calata", "Contrada", "Borgata", "Regione",
            "Frazione", "Strada", "Traversa", "Passaggio", "Località", "Altro",
        ]
        for t in tipi:
            row = self._q(
                "INSERT INTO tipo_localita (nome)"
                " VALUES (%s) ON CONFLICT (nome) DO UPDATE SET nome=EXCLUDED.nome"
                " RETURNING id",
                (t,),
            )
            self.ids[f"tl_{t.lower()}"] = row["id"]
        self._count("tipo_localita", len(tipi))
        print(f"   ✓ {len(tipi)} tipi\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Comuni
    # ─────────────────────────────────────────────────────────────────────────

    def _comuni(self):
        print("🏙  Comuni...")
        pid_regno = self.ids["periodo_reg"]
        pid_rep   = self.ids["periodo_rep"]

        comuni = [
            # (chiave, nome, prov, regione, codice, data_ist, data_sopp, note, periodo_id)
            ("savona",  "Savona",           "SV", "Liguria", "I480",
             date(1861, 1, 1), None,            "Capoluogo di provincia", pid_regno),
            ("cairo",   "Cairo Montenotte", "SV", "Liguria", "B369",
             date(1861, 1, 1), None,            "Comune dell'entroterra savonese", pid_regno),
            ("albissola","Albissola Marina","SV", "Liguria", "A153",
             date(1861, 1, 1), None,            "Comune costiero ceramico", pid_regno),
            ("celle",   "Celle Ligure",     "SV", "Liguria", "C443",
             date(1861, 1, 1), None,            "Comune costiero", pid_regno),
            ("vado",    "Vado Ligure",      "SV", "Liguria", "L526",
             date(1861, 1, 1), None,            "Comune portuale", pid_regno),
            # Comune soppresso — edge case
            ("zinola",  "Zinola",           "SV", "Liguria", "M174",
             date(1861, 1, 1), date(1965, 1, 1),
             "Frazione soppressa, incorporata in Savona nel 1965", pid_rep),
        ]

        for key, nome, prov, reg, cod, ist, sopp, note, per in comuni:
            cid = self._insert("comune", dict(
                nome=nome, provincia=prov, regione=reg,
                codice_catastale=cod,
                data_istituzione=ist, data_soppressione=sopp,
                note=note, periodo_id=per,
            ))
            self.ids[f"com_{key}"] = cid

        self._count("comune", len(comuni))
        print(f"   ✓ {len(comuni)} comuni (1 soppresso)\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Località
    # ─────────────────────────────────────────────────────────────────────────

    def _localita(self):
        print("📍 Località...")

        def tl(nome: str) -> int:
            return self.ids[f"tl_{nome.lower()}"]

        # (chiave, comune_key, nome, tipo, civico)
        rows = [
            # ── Savona ──
            ("sav_roma",       "savona",   "Via Roma",           tl("Via"),     "1"),
            ("sav_paleocapa",  "savona",   "Via Paleocapa",      tl("Via"),     "15"),
            ("sav_corso",      "savona",   "Corso Italia",       tl("Corso"),   "42"),
            ("sav_sisto",      "savona",   "Piazza Sisto IV",    tl("Piazza"),  None),
            ("sav_torino",     "savona",   "Via Torino",         tl("Via"),     "8"),
            ("sav_dante",      "savona",   "Viale Dante",        tl("Viale"),   "22"),
            ("sav_porto",      "savona",   "Contrada del Porto", tl("Contrada"),None),
            # ── Cairo Montenotte ──
            ("cai_ferriere",   "cairo",    "Via Ferriere",       tl("Via"),     "3"),
            ("cai_prov",       "cairo",    "Via Provinciale",    tl("Via"),     "10"),
            ("cai_vittoria",   "cairo",    "Piazza della Vittoria", tl("Piazza"), None),
            ("cai_ferrania",   "cairo",    "Borgata Ferrania",   tl("Borgata"), None),
            ("cai_colonia",    "cairo",    "Contrada Colonia",   tl("Contrada"),None),
            # ── Albissola Marina ──
            ("alb_aurelia",    "albissola","Via Aurelia",        tl("Via"),     "100"),
            ("alb_rimemb",     "albissola","Viale della Rimembranza", tl("Viale"), "5"),
            ("alb_natta",      "albissola","Piazza Natta",       tl("Piazza"),  None),
            ("alb_grana",      "albissola","Borgata Grana",      tl("Borgata"), None),
            ("alb_colombo",    "albissola","Via Colombo",        tl("Via"),     "12"),
            # ── Celle Ligure ──
            ("cel_colla",      "celle",    "Via Colla",          tl("Via"),     "2"),
            ("cel_boaglio",    "celle",    "Piazza Boaglio",     tl("Piazza"),  None),
            ("cel_margherita", "celle",    "Via Margherita",     tl("Via"),     "7"),
            ("cel_genesio",    "celle",    "Borgata San Genesio",tl("Borgata"), None),
            ("cel_castello",   "celle",    "Salita al Castello", tl("Salita"),  None),
            # ── Vado Ligure ──
            ("vad_sabazia",    "vado",     "Via Sabazia",        tl("Via"),     "4"),
            ("vad_ferraris",   "vado",     "Corso Ferraris",     tl("Corso"),   "20"),
            ("vad_cavour",     "vado",     "Piazza Cavour",      tl("Piazza"),  None),
            ("vad_porto",      "vado",     "Via del Porto",      tl("Via"),     "1"),
            # ── Zinola ──
            ("zin_principale", "zinola",   "Via Principale",     tl("Via"),     "1"),
        ]

        for key, com_key, nome, tipo_id, civico in rows:
            lid = self._insert("localita", dict(
                comune_id=self.ids[f"com_{com_key}"],
                nome=nome, tipo_id=tipo_id, civico=civico,
            ))
            self.ids[f"loc_{key}"] = lid

        self._count("localita", len(rows))
        print(f"   ✓ {len(rows)} località\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Possessori
    # ─────────────────────────────────────────────────────────────────────────

    def _possessori(self):
        print("👤 Possessori...")

        # (chiave, comune_key, cognome_nome, nome_completo, paternita, attivo)
        rows = [
            # Savona
            ("rossi",     "savona",   "ROSSI MARIO",       "ROSSI MARIO fu GIOVANNI",         "fu GIOVANNI",  True),
            ("ferrari",   "savona",   "FERRARI ANNA",      "FERRARI ANNA fu CARLO",            "fu CARLO",     True),
            ("bianchi",   "savona",   "BIANCHI PIETRO",    "BIANCHI PIETRO fu LUIGI",          "fu LUIGI",     True),
            ("scarsi",    "savona",   "SCARSI VITTORIA",   "SCARSI VITTORIA fu BATTISTA",      "fu BATTISTA",  True),
            # Cairo
            ("rebora",    "cairo",    "REBORA GIOVANNI",   "REBORA GIOVANNI fu GIACOMO",       "fu GIACOMO",   True),
            ("zunino",    "cairo",    "ZUNINO LUISA",      "ZUNINO LUISA fu ANGELO",           "fu ANGELO",    True),
            # Albissola
            ("calcagno",  "albissola","CALCAGNO CARLO",    "CALCAGNO CARLO fu BENEDETTO",      "fu BENEDETTO", True),
            ("ferraris",  "albissola","FERRARIS EMILIA",   "FERRARIS EMILIA fu FRANCESCO",     "fu FRANCESCO", True),
            # Celle
            ("pistarino", "celle",    "PISTARINO BATTISTA","PISTARINO BATTISTA fu GIACOMO",    "fu GIACOMO",   True),
            ("mortola",   "celle",    "MORTOLA ANGELA",    "MORTOLA ANGELA fu DOMENICO",       "fu DOMENICO",  True),
            # Vado
            ("semino",    "vado",     "SEMINO GIUSEPPE",   "SEMINO GIUSEPPE fu ANTONIO",       "fu ANTONIO",   True),
            ("ferretti",  "vado",     "FERRETTI MARTA",    "FERRETTI MARTA fu LUIGI",          "fu LUIGI",     True),
            # Edge case: possessore non attivo (Savona)
            ("oliva",     "savona",   "OLIVA RENATO",      "OLIVA RENATO fu CARLO",            "fu CARLO",     False),
        ]

        for key, com_key, cogn, nome, pat, attivo in rows:
            pid = self._insert("possessore", dict(
                comune_id=self.ids[f"com_{com_key}"],
                cognome_nome=cogn, nome_completo=nome,
                paternita=pat, attivo=attivo,
            ))
            self.ids[f"pos_{key}"] = pid

        self._count("possessore", len(rows))
        print(f"   ✓ {len(rows)} possessori (1 non attivo)\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Utility per workflow
    # ─────────────────────────────────────────────────────────────────────────

    def _partita(self, key: str, com_key: str, numero: int, stato: str,
                 data_imp: date, tipo: str = "principale",
                 suffisso: Optional[str] = None,
                 data_chius: Optional[date] = None,
                 num_prov: Optional[str] = None) -> int:
        pid = self._insert("partita", dict(
            comune_id=self.ids[f"com_{com_key}"],
            numero_partita=numero,
            suffisso_partita=suffisso,
            data_impianto=data_imp,
            data_chiusura=data_chius,
            numero_provenienza=num_prov,
            stato=stato,
            tipo=tipo,
        ))
        self.ids[f"par_{key}"] = pid
        self._count("partita")
        return pid

    def _link(self, partita_key: str, pos_key: str, tipo: str = "principale",
              titolo: str = "proprietà esclusiva", quota: Optional[str] = None):
        self._q(
            "INSERT INTO partita_possessore"
            " (partita_id, possessore_id, tipo_partita, titolo, quota)"
            " VALUES (%s, %s, %s, %s, %s)",
            (self.ids[f"par_{partita_key}"], self.ids[f"pos_{pos_key}"],
             tipo, titolo, quota),
        )
        self._count("partita_possessore")

    def _immobile(self, partita_key: str, loc_key: str, natura: str,
                  classificazione: str = "",
                  piani: Optional[int] = None, vani: Optional[int] = None,
                  consistenza: Optional[str] = None) -> int:
        iid = self._insert("immobile", dict(
            partita_id=self.ids[f"par_{partita_key}"],
            localita_id=self.ids[f"loc_{loc_key}"],
            natura=natura,
            classificazione=classificazione or None,
            numero_piani=piani,
            numero_vani=vani,
            consistenza=consistenza,
        ))
        self._count("immobile")
        return iid

    def _variazione(self, key: str, orig_key: str, dest_key: Optional[str],
                    tipo: str, data: date,
                    rif: Optional[str] = None,
                    nominativo: Optional[str] = None) -> int:
        dest_id = self.ids.get(f"par_{dest_key}") if dest_key else None
        vid = self._insert("variazione", dict(
            partita_origine_id=self.ids[f"par_{orig_key}"],
            partita_destinazione_id=dest_id,
            tipo=tipo,
            data_variazione=data,
            numero_riferimento=rif,
            nominativo_riferimento=nominativo,
        ))
        self.ids[f"var_{key}"] = vid
        self._count("variazione")
        return vid

    def _contratto(self, var_key: str, tipo: str, data: date,
                   notaio: Optional[str] = None,
                   repertorio: Optional[str] = None,
                   note: Optional[str] = None):
        self._q(
            "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)",
            (self.ids[f"var_{var_key}"], tipo, data, notaio, repertorio, note),
        )
        self._count("contratto")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 1 — Partita attiva semplice
    # ─────────────────────────────────────────────────────────────────────────

    def _s01_partita_semplice(self):
        print("📋 Scenario 1: Partita attiva semplice (Savona 101)...")
        self._partita("sav_101", "savona", 101, "attiva", date(1955, 3, 20))
        self._link("sav_101", "rossi")
        self._immobile("sav_101", "sav_roma",
                        "Casa d'abitazione", "Abitazione civile",
                        piani=3, vani=8, consistenza="210 mq")
        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 2 — Partita con suffisso "bis"
    # ─────────────────────────────────────────────────────────────────────────

    def _s02_suffisso(self):
        print("📋 Scenario 2: Partita con suffisso 'bis' (Savona 102/bis)...")
        self._partita("sav_102bis", "savona", 102, "attiva",
                      date(1960, 6, 1), suffisso="bis")
        self._link("sav_102bis", "ferrari")
        self._immobile("sav_102bis", "sav_dante",
                        "Terreno", "Terreno agricolo",
                        consistenza="1.200 mq")
        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 3 — Catena vendite A→B→C  (3 passaggi di proprietà)
    # ─────────────────────────────────────────────────────────────────────────

    def _s03_catena_vendite(self):
        print("📋 Scenario 3: Catena vendite A→B→C (Savona 110→111→112)...")

        # A: partita originale 1880, inattiva
        self._partita("sav_110", "savona", 110, "inattiva",
                      date(1880, 1, 1), data_chius=date(1900, 4, 15))
        self._link("sav_110", "bianchi")
        self._immobile("sav_110", "sav_paleocapa",
                        "Casa", "Abitazione civile",
                        piani=2, vani=6, consistenza="160 mq")

        # B: dopo prima vendita 1900, inattiva
        self._partita("sav_111", "savona", 111, "inattiva",
                      date(1900, 4, 15), data_chius=date(1925, 9, 10),
                      num_prov="110")
        self._link("sav_111", "scarsi")
        self._immobile("sav_111", "sav_paleocapa",
                        "Casa", "Abitazione civile",
                        piani=2, vani=6, consistenza="160 mq")

        # C: dopo seconda vendita 1925, attiva
        self._partita("sav_112", "savona", 112, "attiva",
                      date(1925, 9, 10), num_prov="111")
        self._link("sav_112", "rebora")
        self._immobile("sav_112", "sav_paleocapa",
                        "Casa ristrutturata", "Abitazione civile",
                        piani=3, vani=9, consistenza="210 mq")

        # Variazioni + contratti
        self._variazione("sav_110_111", "sav_110", "sav_111",
                         "Vendita", date(1900, 4, 15),
                         rif="Rep. 1245/1900",
                         nominativo="Notaio Avv. Giuseppe Ferretti")
        self._contratto("sav_110_111", "Atto di Compravendita",
                         date(1900, 4, 15),
                         notaio="Avv. Giuseppe Ferretti",
                         repertorio="Rep. 1245/1900")

        self._variazione("sav_111_112", "sav_111", "sav_112",
                         "Vendita", date(1925, 9, 10),
                         rif="Rep. 3301/1925",
                         nominativo="Notaio Dott. Enrico Moro")
        self._contratto("sav_111_112", "Atto di Compravendita",
                         date(1925, 9, 10),
                         notaio="Dott. Enrico Moro",
                         repertorio="Rep. 3301/1925")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 4 — Successione ereditaria
    # ─────────────────────────────────────────────────────────────────────────

    def _s04_successione(self):
        print("📋 Scenario 4: Successione ereditaria (Cairo 201→202)...")

        self._partita("cai_201", "cairo", 201, "inattiva",
                      date(1890, 1, 1), data_chius=date(1955, 7, 22))
        self._link("cai_201", "zunino")
        self._immobile("cai_201", "cai_ferriere",
                        "Fabbricato rurale", "Abitazione rurale",
                        piani=2, vani=5, consistenza="180 mq")

        self._partita("cai_202", "cairo", 202, "attiva",
                      date(1955, 7, 22), num_prov="201")
        self._link("cai_202", "calcagno")
        self._immobile("cai_202", "cai_ferriere",
                        "Fabbricato ristrutturato", "Abitazione civile",
                        piani=2, vani=6, consistenza="190 mq")

        self._variazione("cai_201_202", "cai_201", "cai_202",
                         "Successione", date(1955, 7, 22),
                         nominativo="Pretura di Cairo Montenotte")
        self._contratto("cai_201_202", "Dichiarazione di Successione",
                         date(1955, 7, 22),
                         note="Successione mortis causa ZUNINO LUISA")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 5 — Frazionamento 1→2 lotti
    # ─────────────────────────────────────────────────────────────────────────

    def _s05_frazionamento(self):
        print("📋 Scenario 5: Frazionamento 1→2 lotti (Celle 301→302+303)...")

        # Partita originale
        self._partita("cel_301", "celle", 301, "inattiva",
                      date(1930, 5, 5), data_chius=date(1960, 10, 15))
        self._link("cel_301", "pistarino")
        self._immobile("cel_301", "cel_colla",
                        "Terreno", "Terreno agricolo",
                        consistenza="4.500 mq")

        # Lotto A
        self._partita("cel_302", "celle", 302, "attiva",
                      date(1960, 10, 15), num_prov="301")
        self._link("cel_302", "pistarino")
        self._immobile("cel_302", "cel_colla",
                        "Terreno lotto A", "Terreno edificabile",
                        consistenza="2.100 mq")

        # Lotto B
        self._partita("cel_303", "celle", 303, "attiva",
                      date(1960, 10, 15), num_prov="301")
        self._link("cel_303", "mortola")
        self._immobile("cel_303", "cel_colla",
                        "Terreno lotto B", "Terreno agricolo",
                        consistenza="2.400 mq")

        # 2 variazioni dallo stesso origine
        self._variazione("cel_301_302", "cel_301", "cel_302",
                         "Frazionamento", date(1960, 10, 15),
                         rif="Fraz. N.12/1960")
        self._contratto("cel_301_302", "Atto di Divisione",
                         date(1960, 10, 15),
                         notaio="Geom. Antonio Berta",
                         repertorio="Fraz. N.12/1960",
                         note="Frazionamento lotto A")

        self._variazione("cel_301_303", "cel_301", "cel_303",
                         "Frazionamento", date(1960, 10, 15),
                         rif="Fraz. N.12/1960")
        self._contratto("cel_301_303", "Atto di Divisione",
                         date(1960, 10, 15),
                         notaio="Geom. Antonio Berta",
                         repertorio="Fraz. N.12/1960",
                         note="Frazionamento lotto B")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 6 — Proprietà pro-indiviso (2 possessori, quote 1/2)
    # ─────────────────────────────────────────────────────────────────────────

    def _s06_pro_indiviso(self):
        print("📋 Scenario 6: Proprietà pro-indiviso (Savona 401, 2 possessori)...")

        self._partita("sav_401", "savona", 401, "attiva", date(1958, 3, 1))
        self._link("sav_401", "bianchi",
                   titolo="proprietà pro-indiviso", quota="1/2")
        self._link("sav_401", "scarsi",
                   titolo="proprietà pro-indiviso", quota="1/2")
        self._immobile("sav_401", "sav_sisto",
                        "Magazzino", "Deposito commerciale",
                        piani=1, consistenza="120 mq")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 7 — Possessore con più partite in comuni diversi
    # ─────────────────────────────────────────────────────────────────────────

    def _s07_possessore_multi_partita(self):
        print("📋 Scenario 7: REBORA GIOVANNI — 3 partite in comuni diversi...")

        # Partita Cairo
        self._partita("cai_501", "cairo", 501, "attiva", date(1962, 8, 20))
        self._link("cai_501", "rebora")
        self._immobile("cai_501", "cai_prov",
                        "Terreno agricolo", "Terreno", consistenza="3.200 mq")

        # Partita Celle
        self._partita("cel_502", "celle", 502, "attiva", date(1968, 11, 5))
        self._link("cel_502", "rebora")
        self._immobile("cel_502", "cel_margherita",
                        "Casa", "Abitazione civile",
                        piani=2, vani=5, consistenza="140 mq")

        # Partita Savona
        self._partita("sav_503", "savona", 503, "attiva", date(1975, 2, 14))
        self._link("sav_503", "rebora")
        self._immobile("sav_503", "sav_torino",
                        "Laboratorio artigianale", "Artigianale",
                        piani=1, consistenza="80 mq")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 8 — Partita inattiva senza successori (estinta)
    # ─────────────────────────────────────────────────────────────────────────

    def _s08_estinta(self):
        print("📋 Scenario 8: Partita inattiva senza successori (Vado 601)...")

        self._partita("vad_601", "vado", 601, "inattiva",
                      date(1920, 4, 1), data_chius=date(1945, 12, 31))
        self._link("vad_601", "semino")
        self._immobile("vad_601", "vad_porto",
                        "Magazzino portuale", "Deposito",
                        piani=1, consistenza="350 mq")
        # Nessuna variazione in uscita — partita terminata senza successori

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 9 — Partita principale + secondaria
    # ─────────────────────────────────────────────────────────────────────────

    def _s09_principale_secondaria(self):
        print("📋 Scenario 9: Partita principale + secondaria (Albissola 701+702)...")

        self._partita("alb_701", "albissola", 701, "attiva",
                      date(1972, 5, 30), tipo="principale")
        self._link("alb_701", "calcagno", tipo="principale")
        self._immobile("alb_701", "alb_grana",
                        "Fabbricato", "Abitazione civile",
                        piani=3, vani=7, consistenza="190 mq")

        self._partita("alb_702", "albissola", 702, "attiva",
                      date(1972, 5, 30), tipo="secondaria")
        self._link("alb_702", "calcagno", tipo="secondaria")
        self._immobile("alb_702", "alb_grana",
                        "Rimessa/Garage", "Pertinenza",
                        piani=1, consistenza="25 mq")

        # Relazione tra partita principale e secondaria
        self._q(
            "INSERT INTO partita_relazione"
            " (partita_principale_id, partita_secondaria_id)"
            " VALUES (%s, %s)",
            (self.ids["par_alb_701"], self.ids["par_alb_702"]),
        )
        self._count("partita_relazione")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 10 — Donazione
    # ─────────────────────────────────────────────────────────────────────────

    def _s10_donazione(self):
        print("📋 Scenario 10: Donazione (Albissola 801→802)...")

        self._partita("alb_801", "albissola", 801, "inattiva",
                      date(1935, 1, 10), data_chius=date(1970, 3, 25))
        self._link("alb_801", "ferraris")
        self._immobile("alb_801", "alb_aurelia",
                        "Casa", "Abitazione civile",
                        piani=2, vani=6, consistenza="155 mq")

        self._partita("alb_802", "albissola", 802, "attiva",
                      date(1970, 3, 25), num_prov="801")
        self._link("alb_802", "calcagno")
        self._immobile("alb_802", "alb_aurelia",
                        "Casa", "Abitazione civile",
                        piani=2, vani=6, consistenza="155 mq")

        self._variazione("alb_801_802", "alb_801", "alb_802",
                         "Trasferimento", date(1970, 3, 25),
                         rif="Rep. 8876/1970",
                         nominativo="Notaio Dr. Luca Amoretti")
        self._contratto("alb_801_802", "Atto di Donazione",
                         date(1970, 3, 25),
                         notaio="Dr. Luca Amoretti",
                         repertorio="Rep. 8876/1970",
                         note="Donazione da madre a figlio")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 11 — Divisione coniugale 1→2
    # ─────────────────────────────────────────────────────────────────────────

    def _s11_divisione(self):
        print("📋 Scenario 11: Divisione coniugale 1→2 (Savona 901→902+903)...")

        # Coniugi BIANCHI + SCARSI: immobile cointestato
        self._partita("sav_901", "savona", 901, "inattiva",
                      date(1950, 9, 1), data_chius=date(1975, 6, 15))
        self._link("sav_901", "bianchi", titolo="proprietà pro-indiviso", quota="1/2")
        self._link("sav_901", "scarsi",  titolo="proprietà pro-indiviso", quota="1/2")
        self._immobile("sav_901", "sav_corso",
                        "Fabbricato", "Abitazione civile",
                        piani=4, vani=12, consistenza="350 mq")

        # Quota BIANCHI
        self._partita("sav_902", "savona", 902, "attiva",
                      date(1975, 6, 15), num_prov="901")
        self._link("sav_902", "bianchi")
        self._immobile("sav_902", "sav_corso",
                        "Appartamento A", "Abitazione civile",
                        piani=2, vani=6, consistenza="165 mq")

        # Quota SCARSI
        self._partita("sav_903", "savona", 903, "attiva",
                      date(1975, 6, 15), num_prov="901")
        self._link("sav_903", "scarsi")
        self._immobile("sav_903", "sav_corso",
                        "Appartamento B", "Abitazione civile",
                        piani=2, vani=6, consistenza="165 mq")

        # 2 variazioni di divisione dalla stessa partita origine
        self._variazione("sav_901_902", "sav_901", "sav_902",
                         "Divisione", date(1975, 6, 15),
                         rif="Sent. Trib. SV 123/1975",
                         nominativo="Tribunale di Savona")
        self._contratto("sav_901_902", "Atto di Divisione",
                         date(1975, 6, 15),
                         note="Divisione giudiziale coniugi — quota BIANCHI PIETRO")

        self._variazione("sav_901_903", "sav_901", "sav_903",
                         "Divisione", date(1975, 6, 15),
                         rif="Sent. Trib. SV 123/1975",
                         nominativo="Tribunale di Savona")
        self._contratto("sav_901_903", "Atto di Divisione",
                         date(1975, 6, 15),
                         note="Divisione giudiziale coniugi — quota SCARSI VITTORIA")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 12 — Sentenza giudiziale / Usucapione
    # ─────────────────────────────────────────────────────────────────────────

    def _s12_sentenza(self):
        print("📋 Scenario 12: Sentenza giudiziale/Usucapione (Celle 1001→1002)...")

        self._partita("cel_1001", "celle", 1001, "inattiva",
                      date(1948, 4, 1), data_chius=date(1980, 11, 30))
        self._link("cel_1001", "mortola")
        self._immobile("cel_1001", "cel_genesio",
                        "Casa colonica", "Abitazione rurale",
                        piani=2, vani=5, consistenza="170 mq")

        self._partita("cel_1002", "celle", 1002, "attiva",
                      date(1980, 11, 30), num_prov="1001")
        self._link("cel_1002", "pistarino")
        self._immobile("cel_1002", "cel_genesio",
                        "Casa colonica", "Abitazione rurale",
                        piani=2, vani=5, consistenza="170 mq")

        self._variazione("cel_1001_1002", "cel_1001", "cel_1002",
                         "Variazione", date(1980, 11, 30),
                         rif="App. Genova N.44/1980",
                         nominativo="Corte d'Appello di Genova")
        self._contratto("cel_1001_1002", "Usucapione",
                         date(1980, 11, 30),
                         note="Usucapione accertata dalla Corte d'Appello di Genova")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 13 — Permuta
    # ─────────────────────────────────────────────────────────────────────────

    def _s13_permuta(self):
        print("📋 Scenario 13: Permuta (Cairo 1101→1102)...")

        self._partita("cai_1101", "cairo", 1101, "inattiva",
                      date(1958, 7, 7), data_chius=date(1985, 5, 20))
        self._link("cai_1101", "rebora")
        self._immobile("cai_1101", "cai_ferrania",
                        "Terreno", "Terreno agricolo", consistenza="2.800 mq")

        self._partita("cai_1102", "cairo", 1102, "attiva",
                      date(1985, 5, 20), num_prov="1101")
        self._link("cai_1102", "zunino")
        self._immobile("cai_1102", "cai_ferrania",
                        "Terreno edificabile", "Terreno", consistenza="2.800 mq")

        self._variazione("cai_1101_1102", "cai_1101", "cai_1102",
                         "Trasferimento", date(1985, 5, 20),
                         rif="Rep. 12004/1985",
                         nominativo="Notaio Dr. Santangelo")
        self._contratto("cai_1101_1102", "Permuta",
                         date(1985, 5, 20),
                         notaio="Dr. Santangelo",
                         repertorio="Rep. 12004/1985",
                         note="Permuta con terreno in Comune di Altare")

        print("   ✓\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Documenti storici
    # ─────────────────────────────────────────────────────────────────────────

    def _documenti_storici(self):
        print("📄 Documenti storici...")
        pid_regno = self.ids["periodo_reg"]
        pid_rep   = self.ids["periodo_rep"]

        docs: List[Tuple] = [
            # (chiave, titolo, tipo, anno, periodo_id, descrizione)
            ("doc_mappa_1880",
             "Catasto Gregoriano — Foglio 5 — Savona",
             "Mappa catastale", 1880, pid_regno,
             "Foglio originale del catasto gregoriano dell'area portuale di Savona"),
            ("doc_atto_1900",
             "Atto di Compravendita Bianchi—Scarsi 1900",
             "Atto notarile", 1900, pid_regno,
             "Atto rep. 1245/1900 — rogito Ferretti — immobile Paleocapa"),
            ("doc_mappa_1950",
             "Mappa Catastale Savona — Sezione Urbana 1950",
             "Mappa catastale", 1950, pid_rep,
             "Aggiornamento postbellico del catasto urbano"),
            ("doc_registro_cairo",
             "Registro delle Partite — Comune di Cairo Montenotte 1930",
             "Registro partite", 1930, pid_regno,
             "Volume originale del registro partite comunale"),
        ]

        for key, titolo, tipo, anno, perid, descr in docs:
            did = self._insert("documento_storico", dict(
                titolo=titolo, tipo_documento=tipo, anno=anno,
                periodo_id=perid, descrizione=descr,
            ))
            self.ids[f"doc_{key}"] = did
            self._count("documento_storico")

        # ── Associazioni documento ↔ partita ──
        links: List[Tuple] = [
            # (doc_key, partita_key, rilevanza, note)
            ("doc_mappa_1880",    "sav_110",   "primaria",    "Partita originaria mappata nel catasto"),
            ("doc_mappa_1880",    "sav_111",   "secondaria",  "Partita successiva sullo stesso fondo"),
            ("doc_atto_1900",     "sav_111",   "primaria",    "Atto che origina questa partita"),
            ("doc_mappa_1950",    "sav_101",   "correlata",   "Immobile presente nella mappa"),
            ("doc_mappa_1950",    "sav_401",   "correlata",   "Immobile presente nella mappa"),
            ("doc_registro_cairo","cai_201",   "primaria",    "Partita registrata nel volume"),
            ("doc_registro_cairo","cai_202",   "secondaria",  "Partita successore nel registro"),
        ]

        for doc_key, par_key, rile, note in links:
            self._q(
                "INSERT INTO documento_partita"
                " (documento_id, partita_id, rilevanza, note)"
                " VALUES (%s, %s, %s, %s)",
                (self.ids[f"doc_{doc_key}"], self.ids[f"par_{par_key}"], rile, note),
            )
            self._count("documento_partita")

        print(f"   ✓ {len(docs)} documenti, {len(links)} associazioni\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Nomi storici
    # ─────────────────────────────────────────────────────────────────────────

    def _nomi_storici(self):
        print("📜 Nomi storici...")
        pid_regno = self.ids["periodo_reg"]

        rows = [
            # (comune_key, nome_storico, periodo_id, anno_inizio, anno_fine, note)
            ("zinola",  "Zinola di Savona",  pid_regno, 1861, 1920,
             "Denominazione usata nei registri pre-unitari"),
            ("cairo",   "Cairo",             pid_regno, 1861, 1900,
             "Denominazione breve usata nel periodo sabaudo"),
        ]

        for com_key, nome, perid, a_inizio, a_fine, note in rows:
            self._insert("nome_storico", dict(
                entita_tipo="comune",
                entita_id=self.ids[f"com_{com_key}"],
                nome=nome, periodo_id=perid,
                anno_inizio=a_inizio, anno_fine=a_fine,
                note=note,
            ))
            self._count("nome_storico")

        print(f"   ✓ {len(rows)} nomi storici\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Registri partite e matricole
    # ─────────────────────────────────────────────────────────────────────────

    def _registri(self):
        print("📚 Registri partite e matricole...")

        rp = [
            # (comune_key, anno, n_volumi, conservazione)
            ("savona",    1880, 3, "Buono"),
            ("savona",    1920, 2, "Discreto — alcune pagine danneggiate"),
            ("cairo",     1890, 2, "Buono"),
            ("albissola", 1895, 1, "Ottimo"),
            ("celle",     1910, 1, "Buono"),
            ("vado",      1905, 2, "Mediocre — copertina mancante"),
        ]

        rm = [
            ("savona",    1880, 2, "Buono"),
            ("cairo",     1890, 1, "Buono"),
            ("albissola", 1895, 1, "Buono"),
        ]

        for com_key, anno, vols, cons in rp:
            self._insert("registro_partite", dict(
                comune_id=self.ids[f"com_{com_key}"],
                anno_impianto=anno, numero_volumi=vols,
                stato_conservazione=cons,
            ))
            self._count("registro_partite")

        for com_key, anno, vols, cons in rm:
            self._insert("registro_matricole", dict(
                comune_id=self.ids[f"com_{com_key}"],
                anno_impianto=anno, numero_volumi=vols,
                stato_conservazione=cons,
            ))
            self._count("registro_matricole")

        print(f"   ✓ {len(rp)} registri partite, {len(rm)} registri matricole\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Consultazioni archivio
    # ─────────────────────────────────────────────────────────────────────────

    def _consultazioni(self):
        print("🔍 Consultazioni archivio...")

        rows = [
            # (data, richiedente, doc_identita, motivazione, materiale, funzionario)
            (date(2023, 3, 15),
             "Studio Legale Avv. Moro",
             "CF: MROMRN70A01I480X",
             "Ricerca successoria eredità BIANCHI",
             "Partite 110, 111, 112 — Variazioni 1900 e 1925",
             "Arch. Giulia Ferretti"),

            (date(2023, 6, 20),
             "Prof. Univ. Genova — Dip. Storia",
             "Tess. UniGe 88441",
             "Ricerca storica catasto ligure XIX sec.",
             "Documenti storici, mappe 1880—1920",
             "Arch. Giulia Ferretti"),

            (date(2024, 1, 10),
             "Bianchi Carlo (privato)",
             "CI: CA123456",
             "Verifica proprietà immobile ereditato",
             "Partita 902 — Variazione 1975",
             "Dr. Roberto Neri"),

            (date(2024, 4, 5),
             "Studio Tecnico Geom. Berta",
             "P.IVA 00123456789",
             "Pratica frazionamento Celle Ligure",
             "Partite 301, 302, 303 — Planimetrie",
             "Arch. Giulia Ferretti"),

            (date(2024, 9, 15),
             "Notaio Dr. Ferretti",
             "Albo Notai SV N.42",
             "Rogito compravendita — verifica titolo",
             "Partita 401 — Titolarità possessori",
             "Dr. Roberto Neri"),

            (date(2025, 1, 20),
             "Archivio di Stato — Sezione Storica",
             "Cod.Ente AS-SV-001",
             "Catalogazione fondi catastali",
             "Documenti storici 1880—1960 — Registri Comuni Savona e Cairo",
             "Arch. Giulia Ferretti"),
        ]

        for data, rich, doc_id, motiv, mater, funz in rows:
            self._q(
                "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)",
                (data, rich, doc_id, motiv, mater, funz),
            )
            self._count("consultazione")

        print(f"   ✓ {len(rows)} consultazioni\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Utenti
    # ─────────────────────────────────────────────────────────────────────────

    def _utenti(self):
        print("👥 Utenti...")

        # Tutti i ruoli + un utente non attivo
        users = [
            # (key, username, password, nome_completo, email, ruolo, attivo)
            ("admin",  "admin",           "Foliarium2024!",
             "Marco Santoro",   "m.santoro@archivio.it",    "admin",       True),
            ("arch1",  "giulia.ferretti", "Archivio2024!",
             "Giulia Ferretti", "g.ferretti@archivio.it",   "archivista",  True),
            ("cons1",  "roberto.neri",    "Consult2024!",
             "Roberto Neri",    "r.neri@archivio.it",       "consultatore",True),
            ("arch2",  "laura.bianchi",   "Archivio2024!",
             "Laura Bianchi",   "l.bianchi@archivio.it",    "archivista",  False),  # disattivo
        ]

        for key, uname, pwd, nome, email, ruolo, attivo in users:
            uid = self._insert("utente", dict(
                username=uname,
                password_hash=_hash(pwd),
                nome_completo=nome,
                email=email,
                ruolo=ruolo,
                attivo=attivo,
            ))
            self.ids[f"usr_{key}"] = uid
            self._count("utente")

        # Assegna permessi all'admin
        perms = self._q(
            "SELECT array_agg(id) AS ids FROM permesso",
        )
        if perms and perms["ids"]:
            for pid in perms["ids"]:
                try:
                    self._q(
                        "INSERT INTO utente_permesso (utente_id, permesso_id)"
                        " VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (self.ids["usr_admin"], pid),
                    )
                except Exception:
                    pass

        print(f"   ✓ {len(users)} utenti\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Sessioni di accesso
    # ─────────────────────────────────────────────────────────────────────────

    def _sessioni(self):
        print("🔐 Sessioni di accesso...")

        from datetime import datetime, timedelta

        sessioni = [
            # (utente_key, azione, esito, data_login, data_logout, ip, dettagli)
            ("admin",  "login",      True,
             datetime(2025, 1, 10, 8, 30), datetime(2025, 1, 10, 17, 0),
             "192.168.1.10", None),
            ("arch1",  "login",      True,
             datetime(2025, 1, 11, 9, 0),  datetime(2025, 1, 11, 16, 30),
             "192.168.1.11", None),
            ("cons1",  "login",      True,
             datetime(2025, 1, 12, 10, 0), None,   # sessione ancora aperta
             "192.168.1.20", None),
            ("arch2",  "fail_login", False,
             datetime(2025, 1, 13, 8, 45), None,
             "192.168.1.11", "Account disattivato"),
            ("admin",  "login",      True,
             datetime(2025, 2, 1, 8, 15),  datetime(2025, 2, 1, 19, 0),
             "192.168.1.10", None),
            ("admin",  "login",      True,
             datetime(2025, 3, 10, 8, 0),  None,  # sessione attiva
             "192.168.1.10", None),
        ]

        for u_key, azione, esito, dl, dlo, ip, det in sessioni:
            attiva = (dlo is None and esito)
            self._insert("sessioni_accesso", dict(
                utente_id=self.ids[f"usr_{u_key}"],
                id_sessione=str(uuid.uuid4()),
                data_login=dl,
                data_logout=dlo,
                indirizzo_ip=ip,
                applicazione="Foliarium",
                azione=azione,
                esito=esito,
                dettagli=det,
                attiva=attiva,
            ))
            self._count("sessioni_accesso")

        print(f"   ✓ {len(sessioni)} sessioni\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Riepilogo finale
    # ─────────────────────────────────────────────────────────────────────────

    def _summary(self):
        order = [
            "periodo_storico", "tipo_localita", "comune", "localita",
            "possessore", "partita", "partita_possessore", "immobile",
            "variazione", "contratto", "partita_relazione",
            "documento_storico", "documento_partita",
            "nome_storico", "registro_partite", "registro_matricole",
            "consultazione", "utente", "sessioni_accesso",
        ]
        total = sum(self.stats.values())
        print("─" * 52)
        print(f"{'ENTITÀ':<30} {'RECORD':>8}")
        print("─" * 52)
        for entity in order:
            n = self.stats.get(entity, 0)
            if n:
                print(f"  {entity:<28} {n:>8}")
        print("─" * 52)
        print(f"  {'TOTALE':<28} {total:>8}")
        print("─" * 52)
        print("\n✅ Dati di test generati con successo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genera dati di test per Foliarium",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-reset", dest="reset", action="store_false", default=True,
        help="Non cancella i dati esistenti prima di inserire",
    )
    parser.add_argument(
        "--no-confirm", dest="confirm", action="store_false", default=True,
        help="Non chiede conferma prima di procedere",
    )
    args = parser.parse_args()

    params = _db_params()
    print(f"\nFoliarium — Generatore dati di test")
    print(f"DB: {params['user']}@{params['host']}:{params['port']}/{params['dbname']}")
    print(f"Schema: {SCHEMA}")
    print(f"Modalità: {'RESET + inserimento' if args.reset else 'Solo inserimento'}")
    if not _HAS_BCRYPT:
        print("⚠  bcrypt non trovato — le password useranno sha256 (solo per test!)")
    print()

    if args.confirm and args.reset:
        risposta = input(
            "⚠  Questa operazione CANCELLERÀ tutti i dati esistenti.\n"
            "   Digita 'SI' per confermare: "
        )
        if risposta.strip().upper() != "SI":
            print("Operazione annullata.")
            sys.exit(0)
        print()

    try:
        conn = psycopg2.connect(**params)
    except psycopg2.OperationalError as e:
        print(f"❌ Impossibile connettersi al database:\n   {e}", file=sys.stderr)
        sys.exit(1)

    try:
        gen = DataGenerator(conn, reset=args.reset)
        gen.run()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
