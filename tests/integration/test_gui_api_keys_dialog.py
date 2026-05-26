"""
tests/integration/test_gui_api_keys_dialog.py
=============================================
Test GUI dei 3 dialog per la gestione chiavi API
(foliarium/ui/dialogs/admin/api_keys.py).

Pattern identico a test_gui_smoke.py: pytest-qt + db_manager mockato.

Copre:
* CreateApiKeyDialog — validazione form, scope di default, scadenza opzionale
* NewKeyResultDialog — visualizzazione + bottone copia (verifica clipboard)
* ApiKeysDialog      — popolamento tabella, toggle "mostra revocate",
                       confronto stati (Attiva/Revocata/Scaduta)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest


try:
    from PyQt6.QtCore import Qt  # noqa: F401
    _QT_OK = True
except ImportError:
    _QT_OK = False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.gui,
    pytest.mark.skipif(not _QT_OK, reason="PyQt6 non disponibile"),
]


@pytest.fixture
def mock_db():
    """Mock conforme alla parte API-keys di CatastoDBManager."""
    db = MagicMock()
    db.list_api_keys = MagicMock(return_value=[])
    db.create_api_key = MagicMock(
        return_value=(42, "flr_aaaa1111bbbb2222cccc3333dddd4444")
    )
    db.revoke_api_key = MagicMock(return_value=True)
    return db


@pytest.fixture
def sample_keys():
    """Dataset di 3 chiavi: attiva, revocata, scaduta."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": 1, "name": "mcp-server", "prefix": "flr_aaaa1111",
            "scopes": ["read:partite", "read:possessori"],
            "created_by": 1, "created_by_username": "admin",
            "created_at": now - timedelta(days=10),
            "expires_at": None, "revoked_at": None,
            "last_used_at": now - timedelta(hours=1),
            "rate_limit_per_min": 60,
        },
        {
            "id": 2, "name": "old-key", "prefix": "flr_bbbb2222",
            "scopes": ["*:*"],
            "created_by": 1, "created_by_username": "admin",
            "created_at": now - timedelta(days=100),
            "expires_at": None,
            "revoked_at": now - timedelta(days=5),
            "last_used_at": None,
            "rate_limit_per_min": 60,
        },
        {
            "id": 3, "name": "expired-key", "prefix": "flr_cccc3333",
            "scopes": ["read:audit"],
            "created_by": 1, "created_by_username": "admin",
            "created_at": now - timedelta(days=400),
            "expires_at": now - timedelta(days=10),
            "revoked_at": None,
            "last_used_at": now - timedelta(days=20),
            "rate_limit_per_min": 60,
        },
    ]


# ─────────────────────────────────────────────────────────────────────
# CreateApiKeyDialog
# ─────────────────────────────────────────────────────────────────────

class TestCreateApiKeyDialog:

    def test_default_scopes_are_read_only(self, qtbot):
        from foliarium.ui.dialogs.admin import CreateApiKeyDialog
        dlg = CreateApiKeyDialog()
        qtbot.addWidget(dlg)

        scopes = dlg.get_scopes()
        # Tutti i read:X di default tranne read:* / *:*
        assert "read:partite" in scopes
        assert "read:comuni" in scopes
        assert "read:audit" in scopes
        assert "write:partite" not in scopes
        assert "*:*" not in scopes
        assert "read:*" not in scopes

    def test_expiry_disabled_returns_none(self, qtbot):
        from foliarium.ui.dialogs.admin import CreateApiKeyDialog
        dlg = CreateApiKeyDialog()
        qtbot.addWidget(dlg)
        assert dlg.expiry_enabled.isChecked() is False
        assert dlg.get_expires_at() is None

    def test_expiry_enabled_returns_datetime(self, qtbot):
        from foliarium.ui.dialogs.admin import CreateApiKeyDialog
        dlg = CreateApiKeyDialog()
        qtbot.addWidget(dlg)
        dlg.expiry_enabled.setChecked(True)
        exp = dlg.get_expires_at()
        assert isinstance(exp, datetime)
        assert exp > datetime.now()

    def test_get_name_strips_whitespace(self, qtbot):
        from foliarium.ui.dialogs.admin import CreateApiKeyDialog
        dlg = CreateApiKeyDialog()
        qtbot.addWidget(dlg)
        dlg.name_edit.setText("  mcp-bot  ")
        assert dlg.get_name() == "mcp-bot"

    def test_validate_rejects_empty_name(self, qtbot, monkeypatch):
        from foliarium.ui.dialogs.admin import CreateApiKeyDialog
        from PyQt6.QtWidgets import QMessageBox
        dlg = CreateApiKeyDialog()
        qtbot.addWidget(dlg)
        # Patch QMessageBox.warning per non bloccare il test
        called = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *a, **k: called.append(True) or QMessageBox.StandardButton.Ok,
        )
        # _validate_and_accept non chiude il dialog se il nome è vuoto
        dlg.name_edit.setText("")
        dlg._validate_and_accept()
        assert called  # warning mostrato
        assert dlg.result() != dlg.DialogCode.Accepted


# ─────────────────────────────────────────────────────────────────────
# NewKeyResultDialog
# ─────────────────────────────────────────────────────────────────────

class TestNewKeyResultDialog:

    def test_displays_plaintext(self, qtbot):
        from foliarium.ui.dialogs.admin import NewKeyResultDialog
        plain = "flr_" + "a" * 32
        dlg = NewKeyResultDialog(plain, "my-key")
        qtbot.addWidget(dlg)
        assert plain in dlg.key_field.toPlainText()

    def test_copy_button_copies_to_clipboard_and_disables(self, qtbot):
        from foliarium.ui.dialogs.admin import NewKeyResultDialog
        from PyQt6.QtWidgets import QApplication

        plain = "flr_" + "b" * 32
        dlg = NewKeyResultDialog(plain, "x")
        qtbot.addWidget(dlg)
        dlg._copy_to_clipboard()
        assert QApplication.clipboard().text() == plain
        assert dlg.copy_btn.isEnabled() is False


# ─────────────────────────────────────────────────────────────────────
# ApiKeysDialog
# ─────────────────────────────────────────────────────────────────────

class TestApiKeysDialog:

    def test_populates_table_from_db(self, qtbot, mock_db, sample_keys):
        from foliarium.ui.dialogs.admin import ApiKeysDialog
        # Solo le 2 non revocate vengono restituite da default (DB filtra)
        mock_db.list_api_keys.return_value = [sample_keys[0], sample_keys[2]]
        dlg = ApiKeysDialog(mock_db, current_user_id=1)
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 2
        # Prima chiamata: include_revoked=False
        mock_db.list_api_keys.assert_called_with(include_revoked=False)

    def test_states_are_labeled_correctly(self, qtbot, mock_db, sample_keys):
        from foliarium.ui.dialogs.admin import ApiKeysDialog
        # Includo tutte e tre per verificare i 3 stati possibili
        mock_db.list_api_keys.return_value = sample_keys
        dlg = ApiKeysDialog(mock_db, current_user_id=1)
        qtbot.addWidget(dlg)

        stati = [dlg.table.item(i, 6).text() for i in range(dlg.table.rowCount())]
        assert "Attiva" in stati
        assert "Revocata" in stati
        assert "Scaduta" in stati

    def test_show_revoked_toggle_calls_db_with_flag(self, qtbot, mock_db):
        from foliarium.ui.dialogs.admin import ApiKeysDialog
        dlg = ApiKeysDialog(mock_db, current_user_id=1)
        qtbot.addWidget(dlg)
        mock_db.list_api_keys.reset_mock()
        dlg.show_revoked.setChecked(True)
        mock_db.list_api_keys.assert_called_with(include_revoked=True)

    def test_revoke_without_selection_shows_info(self, qtbot, mock_db, monkeypatch):
        from foliarium.ui.dialogs.admin import ApiKeysDialog
        from PyQt6.QtWidgets import QMessageBox
        dlg = ApiKeysDialog(mock_db, current_user_id=1)
        qtbot.addWidget(dlg)
        called = []
        monkeypatch.setattr(
            QMessageBox, "information",
            lambda *a, **k: called.append(True) or QMessageBox.StandardButton.Ok,
        )
        # Tabella vuota → nessuna selezione → _on_revoke mostra "info"
        dlg._on_revoke()
        assert called
        mock_db.revoke_api_key.assert_not_called()

    def test_columns_hidden_id(self, qtbot, mock_db):
        from foliarium.ui.dialogs.admin import ApiKeysDialog
        dlg = ApiKeysDialog(mock_db, current_user_id=1)
        qtbot.addWidget(dlg)
        # COL_ID nascosta
        assert dlg.table.isColumnHidden(dlg.COL_ID) is True
