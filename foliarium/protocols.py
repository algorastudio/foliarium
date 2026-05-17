"""
foliarium/protocols.py — Contract typing fra db/ e consumer GUI/test.

Six-hats analisi D.11. Definisce protocolli strutturali (structural
subtyping con typing.Protocol) per la superficie d'uso di
CatastoDBManager. Aiuta a:

  - Inserire annotazioni nei widget GUI senza dover importare
    CatastoDBManager (rompe i cicli di import e velocizza il type checking)
  - Dare al type checker (mypy/pyright) il segnale che certi metodi DEVONO
    esistere con quella signature; ogni rinomina lato db/ rompe subito
    il contract invece di scoprirsi a runtime.

Pattern d'uso lato consumer:

    from foliarium.protocols import DBManagerProtocol

    class MyWidget(QWidget):
        def __init__(self, db: DBManagerProtocol, ...):
            ...

    # Runtime: a MyWidget puoi sempre passare un'istanza CatastoDBManager
    # (e' "duck-compatible" col Protocol). Il type checker verifica la
    # chiamata.

Non sostituisce CatastoDBManager — e' SOLO una facciata di tipi. I
metodi qui dichiarati sono i piu' chiamati dai widget e test. Aggiungere
nuovi metodi al Protocol quando un nuovo metodo DB diventa "API pubblica".

Per integrazione con bin/check_api_drift.py: ogni metodo elencato qui
DEVE esistere in db/ — se manca, il drift script lo segnala come usato
ma non definito.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class ComuneOpsProtocol(Protocol):
    """Operazioni su comuni."""

    def aggiungi_comune(
        self,
        nome_comune: str,
        provincia: str,
        regione: str,
        periodo_id: Optional[int] = ...,
        codice_catastale: Optional[str] = ...,
    ) -> int: ...

    def update_comune(self, comune_id: int, dati_modificati: Dict[str, Any]) -> bool: ...

    def get_comune_by_id(self, comune_id: int) -> Optional[Dict[str, Any]]: ...

    def get_all_comuni_details(self) -> List[Dict[str, Any]]: ...

    def archivia_comune(self, comune_id: int) -> bool: ...


@runtime_checkable
class PossessoreOpsProtocol(Protocol):
    """Operazioni su possessori."""

    def create_possessore(
        self,
        nome_completo: str,
        comune_riferimento_id: int,
        paternita: Optional[str] = ...,
        attivo: bool = ...,
        cognome_nome: Optional[str] = ...,
    ) -> int: ...

    def update_possessore(
        self, possessore_id: int, dati_modificati: Dict[str, Any],
    ) -> Any: ...

    def get_possessori_by_comune(
        self,
        comune_id: int,
        filter_text: Optional[str] = ...,
        solo_con_partite: bool = ...,
    ) -> List[Dict[str, Any]]: ...

    def aggiungi_possessore_a_partita(
        self,
        partita_id: int,
        possessore_id: int,
        tipo_partita_rel: str,
        titolo: str,
        quota: Optional[str],
    ) -> bool: ...


@runtime_checkable
class PartitaOpsProtocol(Protocol):
    """Operazioni su partite catastali."""

    def create_partita(
        self,
        comune_id: int,
        numero_partita: int,
        tipo: str,
        stato: str,
        data_impianto: date,
    ) -> int: ...

    def update_partita(
        self, partita_id: int, dati_modificati: Dict[str, Any],
    ) -> Any: ...

    def get_partita_details(self, partita_id: int) -> Optional[Dict[str, Any]]: ...

    def genera_report_proprieta(self, partita_id: int) -> Optional[str]: ...


@runtime_checkable
class ImmobileOpsProtocol(Protocol):
    """Operazioni su immobili."""

    def inserisci_immobile(
        self,
        partita_id: int,
        natura: str,
        localita_id: int,
        numero_civico: Optional[str] = ...,
        classificazione: Optional[str] = ...,
    ) -> int: ...

    def update_immobile(self, immobile_id: int, **kwargs: Any) -> bool: ...

    def transfer_immobile(
        self, immobile_id: int, nuova_partita_id: int,
        registra_variazione: bool = ...,
    ) -> bool: ...

    def search_immobili(
        self,
        partita_id: Optional[int] = ...,
        comune_id: Optional[int] = ...,
    ) -> List[Dict[str, Any]]: ...


@runtime_checkable
class LocalitaOpsProtocol(Protocol):
    """Operazioni su localita."""

    def insert_localita(
        self,
        comune_id: int,
        nome: str,
        tipologia_stradale: str,
    ) -> int: ...

    def get_localita_by_comune(
        self,
        comune_id: int,
        filter_text: Optional[str] = ...,
    ) -> List[Dict[str, Any]]: ...


@runtime_checkable
class AuditOpsProtocol(Protocol):
    """Operazioni di audit log e sessioni."""

    def get_audit_logs(
        self,
        filters: Optional[Dict[str, Any]] = ...,
        page: int = ...,
        page_size: int = ...,
        sort_by: str = ...,
        sort_order: str = ...,
    ) -> Tuple[List[Dict[str, Any]], int]: ...

    def log_app_event(
        self,
        user_id: Optional[int],
        session_id: Optional[int],
        event_type: str,
        details: Dict[str, Any],
    ) -> bool: ...


@runtime_checkable
class DBManagerProtocol(
    ComuneOpsProtocol,
    PossessoreOpsProtocol,
    PartitaOpsProtocol,
    ImmobileOpsProtocol,
    LocalitaOpsProtocol,
    AuditOpsProtocol,
    Protocol,
):
    """Contract completo di CatastoDBManager dal punto di vista dei
    consumer (widget + test). Un widget che annota 'db: DBManagerProtocol'
    accetta automaticamente CatastoDBManager senza importarlo."""

    schema: str

    def initialize_main_pool(self) -> bool: ...

    def close_pool(self) -> None: ...


__all__ = [
    "ComuneOpsProtocol",
    "PossessoreOpsProtocol",
    "PartitaOpsProtocol",
    "ImmobileOpsProtocol",
    "LocalitaOpsProtocol",
    "AuditOpsProtocol",
    "DBManagerProtocol",
]
