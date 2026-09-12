"""
tests/unit/test_roles_schema.py
===============================
Allineamento fra i ruoli di `core.session_manager.Role` e quelli ammessi
dallo schema del database.

Il difetto che questi test sorvegliano e' nato dall'assenza di un punto in
cui le due fonti si incontrassero: `Role` chiamava il terzo ruolo
`visualizzatore`, mentre schema, interfaccia e validazione DB lo chiamano
`consultatore`. Il risultato era una matrice dei permessi che rispondeva
sempre `False` a un consultatore, senza che nulla lo segnalasse.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.session_manager import Role, SessionManager

pytestmark = pytest.mark.unit


# Percorso dello script che crea catasto.utente con il vincolo CHECK sul ruolo.
_SCHEMA_SQL = (
    Path(__file__).resolve().parents[2]
    / "sql_scripts"
    / "07_user-management.sql"
)


def _ruoli_ammessi_dallo_schema() -> set[str]:
    """Estrae i valori del vincolo CHECK su `ruolo` dallo script di schema."""
    sql = _SCHEMA_SQL.read_text(encoding="utf-8")
    match = re.search(
        r"ruolo\s+VARCHAR\(\d+\)[^,]*?CHECK\s*\(\s*ruolo\s+IN\s*\(([^)]*)\)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, (
        f"Vincolo CHECK su 'ruolo' non trovato in {_SCHEMA_SQL.name}: "
        "se lo schema e' cambiato, aggiornare questa regex."
    )
    return set(re.findall(r"'([^']+)'", match.group(1)))


class TestRuoliSchema:
    """I ruoli dichiarati in Python coincidono con quelli dello schema."""

    def test_schema_dichiara_tre_ruoli(self):
        assert _ruoli_ammessi_dallo_schema() == {
            "admin",
            "archivista",
            "consultatore",
        }

    def test_role_all_coincide_con_lo_schema(self):
        """Il test che avrebbe intercettato il disallineamento originale."""
        assert Role._ALL == _ruoli_ammessi_dallo_schema()

    @pytest.mark.parametrize("ruolo", sorted(_ruoli_ammessi_dallo_schema()))
    def test_ruolo_dello_schema_e_valido_e_ha_permessi(self, ruolo):
        assert Role.is_valid(ruolo), f"Role non riconosce il ruolo '{ruolo}'"
        assert Role.permissions_for(ruolo), (
            f"Il ruolo '{ruolo}' non ha alcun permesso: la matrice "
            "_PERMISSIONS non copre tutti i ruoli dello schema."
        )

    def test_ruolo_sconosciuto_non_e_valido(self):
        assert not Role.is_valid("visualizzatore")
        assert Role.permissions_for("visualizzatore") == set()


class TestPermessiConsultatore:
    """Il consultatore consulta: legge, cerca ed esporta, e nulla piu'."""

    CONCESSI = ("view", "search", "export")
    NEGATI = ("insert", "delete", "manage_users")

    @pytest.mark.parametrize("permesso", CONCESSI)
    def test_permessi_concessi(self, permesso):
        assert permesso in Role.permissions_for(Role.CONSULTATORE)

    @pytest.mark.parametrize("permesso", NEGATI)
    def test_permessi_negati(self, permesso):
        assert permesso not in Role.permissions_for(Role.CONSULTATORE)

    def test_sessione_di_un_consultatore(self):
        """Il percorso reale: has_permission() passa da SessionManager."""
        session = SessionManager()
        session.login(7, {"nome": "Consultatore", "ruolo": "consultatore"})

        assert session.can(*self.CONCESSI)
        assert not session.can_any(*self.NEGATI)
        assert not session.is_admin()
