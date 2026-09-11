"""
foliarium.ui.errors — Messaggi di errore comprensibili per l'utente finale.

Il layer DB traduce gli errori psycopg2 in eccezioni applicative
(``DBUniqueConstraintError`` e affini) conservando pero' il testo originale
del driver. Mostrarlo cosi' com'e' in un QMessageBox significa scrivere
all'archivista::

    duplicate key value violates unique constraint
    "partita_unique_numero_suffisso_comune"
    DETAIL: Key (comune_id, numero_partita)=(3, 415) already exists.

Questo modulo traduce l'errore in una frase in italiano, aggiunge un
suggerimento su cosa fare e lascia il testo tecnico nei "Dettagli", dove
serve solo a chi legge i log.

Uso tipico::

    from foliarium.ui.errors import show_user_error

    try:
        self.db_manager.aggiungi_comune(...)
    except Exception as e:
        show_user_error(self, "Inserimento comune", e, logger=self.logger)
"""

from __future__ import annotations

import logging
import traceback
from typing import Optional, Tuple

from PyQt6.QtWidgets import QMessageBox

_log = logging.getLogger("CatastoGUI.errors")


# ---------------------------------------------------------------------------
# Mappa dei codici SQLSTATE piu' frequenti in questa applicazione
# ---------------------------------------------------------------------------

#: SQLSTATE -> (spiegazione, cosa puo' fare l'utente)
_SQLSTATE_MESSAGES: dict[str, Tuple[str, str]] = {
    "23505": (
        "Esiste già un record con questi dati.",
        "Modifica i valori che devono essere univoci (ad esempio numero, "
        "nome o codice) oppure cerca il record esistente e modificalo.",
    ),
    "23503": (
        "L'elemento è collegato ad altri record dell'archivio.",
        "Rimuovi o riassegna prima gli elementi collegati (partite, immobili, "
        "possessori), poi riprova.",
    ),
    "23502": (
        "Manca un dato obbligatorio.",
        "Compila tutti i campi contrassegnati con l'asterisco e riprova.",
    ),
    "23514": (
        "Un valore inserito non rispetta le regole dell'archivio.",
        "Controlla date, quote e numeri: potrebbero essere fuori dai limiti "
        "ammessi.",
    ),
    "22001": (
        "Un testo inserito è troppo lungo.",
        "Accorcia il valore del campo segnalato nei dettagli tecnici.",
    ),
    "22003": (
        "Un valore numerico è fuori dall'intervallo ammesso.",
        "Verifica i numeri inseriti (anni, quote, consistenze).",
    ),
    "22007": (
        "Una data non è scritta in un formato valido.",
        "Usa il formato giorno/mese/anno, ad esempio 05/03/1927.",
    ),
    "22008": (
        "Una data è fuori dall'intervallo ammesso.",
        "Controlla l'anno inserito.",
    ),
    "22P02": (
        "Un valore inserito non è del tipo previsto.",
        "Verifica che nei campi numerici non ci siano lettere o spazi.",
    ),
    "28P01": (
        "Utente o password del database non corretti.",
        "Controlla le credenziali in Impostazioni → Configurazione Database.",
    ),
    "3D000": (
        "Il database indicato non esiste.",
        "Verifica il nome del database in Impostazioni → Configurazione Database.",
    ),
    "40001": (
        "Un altro utente ha modificato gli stessi dati nello stesso momento.",
        "Riprova: l'operazione non è stata salvata.",
    ),
    "40P01": (
        "Due operazioni si sono bloccate a vicenda sul database.",
        "Riprova tra qualche istante.",
    ),
    "42501": (
        "L'utente del database non ha i permessi per questa operazione.",
        "Contatta l'amministratore del sistema.",
    ),
    "42P01": (
        "Una tabella richiesta non esiste nel database.",
        "Lo schema del database potrebbe non essere aggiornato: contatta "
        "l'amministratore del sistema.",
    ),
    "42703": (
        "Una colonna richiesta non esiste nel database.",
        "Lo schema del database potrebbe non essere aggiornato: contatta "
        "l'amministratore del sistema.",
    ),
    "53300": (
        "Il database ha raggiunto il numero massimo di connessioni.",
        "Chiudi le altre finestre dell'applicazione e riprova.",
    ),
    "57014": (
        "L'operazione è stata interrotta perché troppo lunga.",
        "Restringi i filtri di ricerca e riprova.",
    ),
}

#: Prefissi SQLSTATE per le classi di errore piu' generiche.
_SQLSTATE_CLASSES: dict[str, Tuple[str, str]] = {
    "08": (
        "Collegamento al database interrotto.",
        "Verifica che il server PostgreSQL sia acceso e raggiungibile, "
        "poi riprova.",
    ),
    "53": (
        "Il database ha esaurito le risorse disponibili.",
        "Riprova più tardi; se il problema persiste contatta l'amministratore.",
    ),
}

#: Vincoli noti dello schema -> frase specifica per l'utente.
#: Piu' preciso della frase generica sul 23505.
_CONSTRAINT_MESSAGES: dict[str, str] = {
    "partita_unique_numero_suffisso_comune":
        "Esiste già una partita con questo numero (ed eventuale suffisso) "
        "in questo comune.",
    "localita_comune_nome_tipo_unique":
        "Esiste già una località con questo nome e tipologia in questo comune.",
    "localita_comune_id_nome_unique":
        "Esiste già una località con questo nome in questo comune.",
    "localita_comune_id_nome_key":
        "Esiste già una località con questo nome in questo comune.",
    "localita_comune_id_nome_civico_key":
        "Esiste già una località con questo nome e numero civico in questo comune.",
}

#: Tabelle -> nome leggibile, per comporre i messaggi sui vincoli sconosciuti.
_TABLE_LABELS: dict[str, str] = {
    "comune": "comune",
    "possessore": "possessore",
    "partita": "partita",
    "localita": "località",
    "immobile": "immobile",
    "variazione": "variazione",
    "contratto": "contratto",
    "consultazione": "consultazione",
    "utente": "utente",
    "periodo_storico": "periodo storico",
    "tipo_localita": "tipologia di località",
    "tipo_possesso": "tipo di possesso",
}


# ---------------------------------------------------------------------------
# Analisi dell'eccezione
# ---------------------------------------------------------------------------

def _find_db_cause(exc: BaseException) -> Optional[BaseException]:
    """Risale la catena __cause__ fino all'errore psycopg2 originale.

    Il decoratore db_handle_errors rilancia con ``raise ... from e``, quindi
    il codice SQLSTATE resta disponibile qualche anello piu' in basso.
    """
    seen = set()
    corrente: Optional[BaseException] = exc
    while corrente is not None and id(corrente) not in seen:
        seen.add(id(corrente))
        if getattr(corrente, "pgcode", None):
            return corrente
        corrente = corrente.__cause__ or corrente.__context__
    return None


def _constraint_name(db_exc: Optional[BaseException], testo: str) -> str:
    """Estrae il nome del vincolo violato da diag o, in mancanza, dal testo."""
    diag = getattr(db_exc, "diag", None)
    nome = getattr(diag, "constraint_name", None) if diag else None
    if nome:
        return nome
    # Fallback: il nome compare fra virgolette nel messaggio del driver
    if 'constraint "' in testo:
        return testo.split('constraint "', 1)[1].split('"', 1)[0]
    return ""


def _table_label(db_exc: Optional[BaseException], constraint: str) -> str:
    """Nome leggibile della tabella coinvolta, se riconoscibile."""
    diag = getattr(db_exc, "diag", None)
    tabella = getattr(diag, "table_name", None) if diag else None
    if tabella and tabella in _TABLE_LABELS:
        return _TABLE_LABELS[tabella]
    for nome, etichetta in _TABLE_LABELS.items():
        if constraint.startswith(nome + "_") or constraint.startswith("uq_" + nome):
            return etichetta
    return ""


def describe_error(exc: BaseException) -> Tuple[str, str, str]:
    """Traduce un'eccezione in ``(messaggio, suggerimento, dettagli tecnici)``.

    Il messaggio e il suggerimento sono in italiano corrente; i dettagli
    contengono il testo originale e il codice SQLSTATE, da allegare a una
    richiesta di assistenza.
    """
    testo_originale = str(exc).strip()
    db_exc = _find_db_cause(exc)
    pgcode = str(getattr(db_exc, "pgcode", "") or "")

    dettagli_righe = [f"{type(exc).__name__}: {testo_originale}"]
    if db_exc is not None and db_exc is not exc:
        dettagli_righe.append(f"Causa: {type(db_exc).__name__}: {db_exc}".strip())
    if pgcode:
        dettagli_righe.append(f"Codice SQLSTATE: {pgcode}")

    messaggio = ""
    suggerimento = ""

    if pgcode:
        constraint = _constraint_name(db_exc, testo_originale)
        if constraint:
            dettagli_righe.append(f"Vincolo: {constraint}")
        if pgcode == "23505" and constraint in _CONSTRAINT_MESSAGES:
            messaggio = _CONSTRAINT_MESSAGES[constraint]
        elif pgcode in _SQLSTATE_MESSAGES:
            messaggio, suggerimento = _SQLSTATE_MESSAGES[pgcode]
            etichetta = _table_label(db_exc, constraint)
            if etichetta and pgcode == "23505":
                messaggio = f"Esiste già un {etichetta} con questi dati."
            elif etichetta and pgcode == "23503":
                messaggio = (
                    f"Il {etichetta} è collegato ad altri record dell'archivio."
                )
        else:
            classe = _SQLSTATE_CLASSES.get(pgcode[:2])
            if classe:
                messaggio, suggerimento = classe

        if messaggio and not suggerimento:
            suggerimento = _SQLSTATE_MESSAGES.get(pgcode, ("", ""))[1]

    if not messaggio:
        # Nessun codice riconosciuto: si mostra comunque una frase neutra,
        # il testo tecnico resta nei dettagli.
        messaggio = "L'operazione non è stata completata."
        suggerimento = (
            "Riprova; se l'errore si ripete usa Help → Esporta log per "
            "supporto e allega il file alla segnalazione."
        )

    return messaggio, suggerimento, "\n".join(dettagli_righe)


# ---------------------------------------------------------------------------
# Dialogo
# ---------------------------------------------------------------------------

def _main_window(widget):
    """Risale ai genitori fino alla finestra che sa esportare i log."""
    corrente = widget
    while corrente is not None:
        if hasattr(corrente, "_esporta_log_zip"):
            return corrente
        corrente = corrente.parent() if hasattr(corrente, "parent") else None
    try:
        from PyQt6.QtWidgets import QApplication
        for finestra in QApplication.topLevelWidgets():
            if hasattr(finestra, "_esporta_log_zip"):
                return finestra
    except Exception:
        pass
    return None


def show_user_error(
    parent,
    contesto: str,
    exc: BaseException,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Mostra l'errore all'utente in italiano, con i dettagli a scomparsa.

    Args:
        parent:   widget genitore del dialogo.
        contesto: che cosa si stava facendo, es. "Inserimento comune".
        exc:      l'eccezione catturata.
        logger:   logger su cui registrare il traceback completo.
    """
    (logger or _log).error(
        "%s fallito: %s", contesto, exc,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    messaggio, suggerimento, dettagli = describe_error(exc)

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(contesto)
    box.setText(f"<b>{messaggio}</b>")
    if suggerimento:
        box.setInformativeText(suggerimento)
    # I dettagli restano dietro il pulsante "Mostra dettagli" di Qt: servono
    # al supporto, non all'archivista.
    testo_tecnico = dettagli
    if exc.__traceback__ is not None:
        testo_tecnico += "\n\n" + "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ).strip()
    box.setDetailedText(testo_tecnico)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)

    # Scorciatoia verso Help -> Esporta log: chi segnala il problema si porta
    # dietro i log senza doverli cercare nel menu.
    finestra = _main_window(parent)
    btn_log = None
    if finestra is not None:
        btn_log = box.addButton(
            "Esporta log per supporto…", QMessageBox.ButtonRole.ActionRole)

    box.exec()

    if btn_log is not None and box.clickedButton() is btn_log:
        try:
            finestra._esporta_log_zip()
        except Exception as errore_log:      # pragma: no cover - percorso di servizio
            (logger or _log).warning("Esportazione log fallita: %s", errore_log)


__all__ = ["describe_error", "show_user_error"]
