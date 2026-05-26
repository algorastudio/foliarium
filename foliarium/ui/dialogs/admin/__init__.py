"""
foliarium/ui/dialogs/admin/ — Dialog di amministrazione e configurazione.

Package estratto dal modulo monolitico dialogs/admin.py (1.907 LOC).
Suddiviso per dominio:
  helpers.py      — qdate_to_datetime, datetime_to_qdate,
                    _validate_password_strength, _hash_password, _verify_password
  connessione.py  — DBConfigDialog
  documento.py    — DocumentViewerDialog
  utente.py       — CreateUserDialog, UserSelectionDialog
  sistema.py      — BackupReminderSettingsDialog, EulaDialog, SMTPSettingsDialog
  help_viewer.py  — HelpViewerDialog
  licenza.py      — LicenseDialog
  login.py        — LoginDialog

Questo __init__ re-esporta tutte le classi e gli helper: gli import
esistenti (`from foliarium.ui.dialogs.admin import ...`) restano invariati.
"""

from foliarium.ui.dialogs.admin.helpers import (        # noqa: F401
    qdate_to_datetime,
    datetime_to_qdate,
    _validate_password_strength,
    _hash_password,
    _verify_password,
)
from foliarium.ui.dialogs.admin.connessione import DBConfigDialog       # noqa: F401
from foliarium.ui.dialogs.admin.documento import DocumentViewerDialog   # noqa: F401
from foliarium.ui.dialogs.admin.utente import (         # noqa: F401
    CreateUserDialog,
    UserSelectionDialog,
)
from foliarium.ui.dialogs.admin.sistema import (        # noqa: F401
    BackupReminderSettingsDialog,
    EulaDialog,
    SMTPSettingsDialog,
)
from foliarium.ui.dialogs.admin.help_viewer import HelpViewerDialog     # noqa: F401
from foliarium.ui.dialogs.admin.licenza import LicenseDialog            # noqa: F401
from foliarium.ui.dialogs.admin.login import LoginDialog                # noqa: F401
from foliarium.ui.dialogs.admin.api_keys import (                       # noqa: F401
    ApiKeysDialog,
    CreateApiKeyDialog,
    NewKeyResultDialog,
)

__all__ = [
    "qdate_to_datetime",
    "datetime_to_qdate",
    "_validate_password_strength",
    "_hash_password",
    "_verify_password",
    "DBConfigDialog",
    "DocumentViewerDialog",
    "CreateUserDialog",
    "UserSelectionDialog",
    "BackupReminderSettingsDialog",
    "EulaDialog",
    "SMTPSettingsDialog",
    "HelpViewerDialog",
    "LicenseDialog",
    "LoginDialog",
    "ApiKeysDialog",
    "CreateApiKeyDialog",
    "NewKeyResultDialog",
]
