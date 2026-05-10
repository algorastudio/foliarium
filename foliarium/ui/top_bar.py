"""
foliarium.ui.top_bar — TopBarWidget

Barra superiore fissa con logo, indicatore DB, info utente, chip licenza,
e pulsante logout. Estratta da gui_main.py in fase C.5 del refactoring.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                             QSizePolicy)

from app_paths import get_logo_svg_path
from config import APP_NAME, APP_SUBTITLE, IS_DEMO_MODE


class TopBarWidget(QFrame):
    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)

        # Logo SVG
        try:
            from PyQt6.QtSvgWidgets import QSvgWidget
            logo_path = get_logo_svg_path(dark=False)
            if logo_path:
                logo = QSvgWidget(str(logo_path))
                logo.setFixedSize(30, 30)
                layout.addWidget(logo)
        except Exception:
            pass

        # Titolo + sottotitolo istituzionale
        title_label = QLabel(APP_NAME)
        title_label.setObjectName("appTitle")
        layout.addWidget(title_label)

        subtitle_label = QLabel(f"/ {APP_SUBTITLE}")
        subtitle_label.setObjectName("appSubtitle")
        layout.addWidget(subtitle_label)

        # Badge visibile solo in modalità demo
        if IS_DEMO_MODE:
            demo_badge = QLabel("  DEMO  ")
            demo_badge.setObjectName("demoBadge")
            layout.addWidget(demo_badge)

        layout.addStretch()

        # Indicatore DB
        self._db_indicator = QLabel("● DB: —")
        self._db_indicator.setObjectName("dbIndicator")
        layout.addWidget(self._db_indicator)

        layout.addSpacing(12)

        # Avatar con iniziali utente
        self._avatar_label = QLabel("—")
        self._avatar_label.setObjectName("avatarWidget")
        self._avatar_label.setFixedSize(28, 28)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._avatar_label)

        layout.addSpacing(6)

        # Nome utente
        self._user_label = QLabel("—")
        self._user_label.setObjectName("userLabel")
        layout.addWidget(self._user_label)

        # Chip ruolo
        self._role_chip = QLabel("")
        self._role_chip.setObjectName("roleChip")
        layout.addWidget(self._role_chip)

        layout.addSpacing(8)

        # Chip scadenza licenza (nascosto finché non serve)
        self._license_chip = QLabel("")
        self._license_chip.setObjectName("licenseExpiryChip")
        self._license_chip.setVisible(False)
        layout.addWidget(self._license_chip)

        # Pulsante Logout
        self._logout_btn = QPushButton("Logout")
        self._logout_btn.setObjectName("logoutButton")
        self._logout_btn.setEnabled(False)
        self._logout_btn.clicked.connect(self.logout_requested)
        layout.addWidget(self._logout_btn)

    @staticmethod
    def _initials(nome: str) -> str:
        """Estrae le iniziali (max 2 lettere) dal nome utente."""
        parts = nome.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return nome[:2].upper() if nome else "—"

    def update_user_info(self, nome: str, ruolo: str, db_connected: bool, db_name: str = ""):
        """Aggiorna label utente, ruolo, avatar e stato DB."""
        if db_connected:
            db_text = f"● DB: {db_name}" if db_name else "● DB: connesso"
            self._db_indicator.setStyleSheet(
                "color: #2E7D32; font-size: 11px; background: #E8F5E9; "
                "border-radius: 10px; padding: 2px 8px; font-weight: 600;"
            )
        else:
            db_text = "● DB: offline"
            self._db_indicator.setStyleSheet(
                "color: #B71C1C; font-size: 11px; background: #FDE8E8; "
                "border-radius: 10px; padding: 2px 8px; font-weight: 600;"
            )
        self._db_indicator.setText(db_text)

        if nome:
            self._avatar_label.setText(self._initials(nome))
            self._user_label.setText(nome)
            self._role_chip.setText(ruolo or "")
            self._role_chip.setProperty("role", (ruolo or "").lower())
            self._role_chip.style().unpolish(self._role_chip)
            self._role_chip.style().polish(self._role_chip)
            self._logout_btn.setEnabled(True)
        else:
            self._avatar_label.setText("—")
            self._user_label.setText("—")
            self._role_chip.setText("")
            self._logout_btn.setEnabled(False)

    def set_logout_enabled(self, enabled: bool):
        self._logout_btn.setEnabled(enabled)

    def set_license_expiry(self, days_left: Optional[int]) -> None:
        """Mostra/nasconde il chip di scadenza licenza nella top bar.

        days_left=None → nasconde il chip (licenza perpetua o non disponibile).
        days_left<=30  → chip arancione/rosso visibile.
        """
        if days_left is None or days_left > 30:
            self._license_chip.setVisible(False)
            return
        if days_left <= 0:
            text = "Licenza scaduta!"
            color = "#B71C1C"
        elif days_left <= 7:
            text = f"Licenza: scade in {days_left}g"
            color = "#E65100"
        else:
            text = f"Licenza: {days_left}gg alla scadenza"
            color = "#F57F17"
        self._license_chip.setText(f"  {text}  ")
        self._license_chip.setStyleSheet(
            f"background: {color}; color: white; border-radius: 4px; "
            "font-size: 11px; font-weight: bold; padding: 2px 6px;"
        )
        self._license_chip.setVisible(True)
