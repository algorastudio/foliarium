"""
db/models.py — Dataclass models per type safety (zero runtime cost).
Usati per mapping DB rows → structured Python objects.

Uso:
    row = cur.fetchone()
    partita = Partita(**row)  # Type-safe
    print(partita.numero_partita)  # IDE hints
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Partita:
    """Partita catastale."""
    id: int
    numero_partita: int
    suffisso_partita: Optional[str] = None
    data_impianto: Optional[datetime] = None
    stato: str = "Attiva"
    tipo_partita: Optional[str] = None
    numero_provenienza: Optional[int] = None
    comune_id: Optional[int] = None
    data_creazione: Optional[datetime] = None
    data_modifica: Optional[datetime] = None


@dataclass
class Possessore:
    """Proprietario/possessore."""
    id: int
    cognome_nome: str
    nome_completo: str
    paternita: Optional[str] = None
    data_creazione: Optional[datetime] = None
    data_modifica: Optional[datetime] = None


@dataclass
class Localita:
    """Strada, piazza, via, etc."""
    id: int
    nome: str
    tipologia_stradale: Optional[str] = None
    comune_id: Optional[int] = None
    data_creazione: Optional[datetime] = None
    data_modifica: Optional[datetime] = None


@dataclass
class Immobile:
    """Bene immobile (fabbricato, terreno, etc.)."""
    id: int
    numero_immobile: str
    partita_id: int
    localita_id: int
    numero_civico: Optional[str] = None
    foglio: Optional[str] = None
    particella: Optional[str] = None
    natura: Optional[str] = None
    categoria: Optional[str] = None
    consistenza: Optional[str] = None
    data_creazione: Optional[datetime] = None
    data_modifica: Optional[datetime] = None


@dataclass
class Variazione:
    """Variazione partita (eredità, fusione, scissione, etc.)."""
    id: int
    partita_origine_id: int
    partita_destinazione_id: int
    tipo_variazione: str
    data_variazione: Optional[datetime] = None
    numero_atto: Optional[str] = None
    data_creazione: Optional[datetime] = None
    data_modifica: Optional[datetime] = None


@dataclass
class Documento:
    """Documento allegato a partita."""
    id: int
    partita_id: int
    titolo: str
    tipo: Optional[str] = None
    percorso_file: Optional[str] = None
    anno: Optional[int] = None
    descrizione: Optional[str] = None
    data_creazione: Optional[datetime] = None
    data_modifica: Optional[datetime] = None


@dataclass
class Utente:
    """Utente applicazione."""
    id: int
    username: str
    email: Optional[str] = None
    ruolo: str = "Viewer"
    attivo: bool = True
    data_creazione: Optional[datetime] = None
    data_ultimo_accesso: Optional[datetime] = None


@dataclass
class Comune:
    """Comune italiano."""
    id: int
    nome: str
    provincia: str
    regione: str
    codice_catastale: Optional[str] = None
    data_istituzione: Optional[datetime] = None
    data_soppressione: Optional[datetime] = None
    note: Optional[str] = None
    data_creazione: Optional[datetime] = None
    data_modifica: Optional[datetime] = None
