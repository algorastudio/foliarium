"""
db/utenti.py — Mixin gestione utenti, autenticazione e permessi.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any

import uuid
import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import (
    DBMError,
    DBUniqueConstraintError,
    DBNotFoundError,
    DBDataError,
)


class DBUtentiMixin:
    """Mixin gestione utenti, autenticazione e permessi."""

    def create_user(
        self,
        username: str,
        password_hash: str,
        nome_completo: str,
        email: str,
        ruolo: str,
    ) -> bool:
        """Chiama la procedura SQL crea_utente in modo transazionale e sicuro."""
        call_proc = f"CALL {self.schema}.crea_utente(%s, %s, %s, %s, %s)"
        params = (username, password_hash, nome_completo, email, ruolo)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.debug(
                        f"Chiamata procedura crea_utente per username: {username}"
                    )
                    cur.execute(call_proc, params)

            # Il commit è automatico qui
            self.logger.info(
                f"Utente '{username}' creato con successo tramite procedura."
            )
            return True

        except psycopg2.errors.UniqueViolation as uve:
            # Il rollback è automatico
            constraint = getattr(uve.diag, "constraint_name", "N/D")
            self.logger.error(
                f"Errore creazione utente '{username}': Username o Email già esistente (vincolo: {constraint})."
            )
            raise DBUniqueConstraintError(
                f"Username '{username}' o Email '{email}' già esistente.",
                constraint_name=constraint,
            ) from uve

        except psycopg2.Error as db_err:
            # Il rollback è automatico
            self.logger.error(
                f"Errore DB creazione utente '{username}': {db_err}", exc_info=True
            )
            raise DBMError(
                f"Errore database durante la creazione dell'utente: {getattr(db_err, 'pgerror', str(db_err))}"
            ) from db_err

        except Exception as e:
            self.logger.error(
                f"Errore Python creazione utente '{username}': {e}", exc_info=True
            )
            raise DBMError(
                f"Errore di sistema imprevisto durante la creazione dell'utente: {e}"
            ) from e

    def get_user_credentials(self, username: str) -> Optional[Dict]:
        """
        Recupera le credenziali e le informazioni di base dell'utente dal database.
        Utilizza il pattern 'with' per una gestione sicura della connessione.
        """
        if not username:
            return None

        # Adattato per usare il context manager _get_connection
        sql = f"""
            SELECT id, username, password_hash, nome_completo, ruolo, attivo
            FROM {self.schema}.utente
            WHERE username = %s;
        """
        try:
            # --- CORREZIONE CRUCIALE: Uso del 'with' statement ---
            with self._get_connection() as conn:
                # Uso del DictCursor per ottenere risultati come dizionari
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(sql, (username,))
                    user_data = cur.fetchone()
                    if user_data:
                        return dict(user_data)
            return None
        except Exception as e:
            self.logger.error(
                f"Errore durante il recupero delle credenziali per l'utente '{username}': {e}",
                exc_info=True,
            )
            return None

    def register_access(
        self,
        user_id: int,
        action: str,
        esito: bool,
        indirizzo_ip: Optional[str] = None,
        dettagli: Optional[str] = None,
        application_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Registra un evento di sessione in modo transazionale e sicuro.
        Genera e restituisce un UUID per la sessione in caso di login riuscito.
        """
        session_id_to_return: Optional[str] = None
        if action == "login" and esito:
            session_id_to_return = str(uuid.uuid4())
            self.logger.info(
                f"Nuovo ID sessione generato per login utente {user_id}: {session_id_to_return}"
            )
        elif action == "fail_login":
            session_id_to_return = str(uuid.uuid4())
            self.logger.info(
                f"ID evento generato per fail_login utente {user_id}: {session_id_to_return}"
            )

        call_proc_str = (
            f"CALL {self.schema}.registra_evento_sessione(%s, %s, %s, %s, %s, %s, %s);"
        )
        params = (
            user_id,
            session_id_to_return,
            action,
            esito,
            indirizzo_ip,
            application_name if application_name else self.application_name,
            dettagli,
        )

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.debug(
                        f"Chiamata a procedura registra_evento_sessione per utente {user_id}, azione {action}"
                    )
                    cur.execute(call_proc_str, params)

            # Il commit è automatico se la procedura ha successo
            self.logger.info(
                f"Evento sessione registrato: Utente ID {user_id}, Azione {action}, Esito {esito}."
            )
            return session_id_to_return

        except psycopg2.Error as db_err:
            # Il rollback è automatico in caso di errore
            pgerror_msg = getattr(db_err, "pgerror", str(db_err))
            self.logger.error(
                f"Errore DB in register_access per utente {user_id}: {pgerror_msg}",
                exc_info=True,
            )
            raise DBMError(
                f"Errore database durante la registrazione dell'evento: {pgerror_msg}"
            ) from db_err
        except Exception as e:
            self.logger.error(
                f"Errore Python in register_access per utente {user_id}: {e}",
                exc_info=True,
            )
            raise DBMError(
                f"Errore di sistema imprevisto durante la registrazione dell'evento: {e}"
            ) from e

    def logout_user(
        self, user_id: int, session_id: str, ip_address: Optional[str]
    ) -> bool:
        """
        Esegue il logout e gestisce la potenziale perdita di connessione con il server.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    call_proc_str = (
                        f"CALL {self.schema}.logout_utente_sessione(%s, %s, %s, %s);"
                    )
                    params = (user_id, session_id, ip_address, self.application_name)
                    self.logger.debug(
                        f"Chiamata a logout_utente_sessione per utente {user_id}, sessione {session_id[:8]}..."
                    )
                    cur.execute(call_proc_str, params)

                    self.logger.debug(
                        "Pulizia delle variabili di sessione per l'audit."
                    )
                    cur.execute(
                        f"SELECT set_config('{self.schema}.app_user_id', NULL, false);"
                    )
                    cur.execute(
                        f"SELECT set_config('{self.schema}.session_id', NULL, false);"
                    )

            self.logger.info(
                f"Logout per utente ID {user_id}, sessione {session_id[:8]}... completato."
            )
            return True

        # --- CORREZIONE: Gestione esplicita della perdita di connessione ---
        except psycopg2.OperationalError as op_err:
            self.logger.critical(
                f"Logout fallito: persa la connessione con il server DB. Errore: {op_err}",
                exc_info=True,
            )
            # Azione critica: il pool non è più valido. Chiudiamolo forzatamente.
            self.close_pool()
            return False  # Segnala il fallimento

        except Exception as e:
            self.logger.error(
                f"Errore durante il processo di logout per l'utente {user_id}: {e}",
                exc_info=True,
            )
            return False

    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        """Chiama la funzione SQL ha_permesso e restituisce True se l'utente ha il permesso richiesto."""
        try:
            query = "SELECT ha_permesso(%s, %s) AS permesso"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (utente_id, permesso_nome))
                    result = cur.fetchone()
                    return bool(result["permesso"]) if result else False
        except psycopg2.Error as db_err:
            self.logger.error(
                f"Errore DB verifica permesso '{permesso_nome}' per utente ID {utente_id}: {db_err}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Errore Python verifica permesso '{permesso_nome}' per utente ID {utente_id}: {e}"
            )
            return False

    def get_utenti(self, solo_attivi: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco di utenti in modo sicuro, con filtro opzionale."""
        query = f"SELECT id, username, nome_completo, email, ruolo, attivo, ultimo_accesso FROM {self.schema}.utente"
        params = []

        if solo_attivi is not None:
            query += " WHERE attivo = %s"
            params.append(solo_attivi)

        query += " ORDER BY username;"

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params) if params else None)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperati {len(results)} utenti.")
                    return results
        except Exception as e:
            self.logger.error(
                f"Errore DB durante il recupero degli utenti: {e}", exc_info=True
            )
            return []

    def get_utente_by_id(self, utente_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di un singolo utente tramite ID, in modo sicuro."""
        if not isinstance(utente_id, int) or utente_id <= 0:
            self.logger.error(f"get_utente_by_id: utente_id non valido: {utente_id}")
            return None

        query = f"SELECT id, username, nome_completo, email, ruolo, attivo FROM {self.schema}.utente WHERE id = %s"
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (utente_id,))
                    user_data = cur.fetchone()
                    if user_data:
                        return dict(user_data)
                    else:
                        self.logger.warning(
                            f"Nessun utente trovato con ID: {utente_id}"
                        )
                        return None
        except Exception as e:
            self.logger.error(
                f"Errore DB in get_utente_by_id (ID: {utente_id}): {e}", exc_info=True
            )
            return None

    def update_user_details(
        self,
        utente_id: int,
        nome_completo: Optional[str] = None,
        email: Optional[str] = None,
        ruolo: Optional[str] = None,
        attivo: Optional[bool] = None,
    ) -> bool:
        """Aggiorna i dettagli di un utente in modo transazionale e sicuro."""
        if not any(
            [
                nome_completo is not None,
                email is not None,
                ruolo is not None,
                attivo is not None,
            ]
        ):
            self.logger.warning(
                f"Nessun dettaglio valido fornito per aggiornare utente ID {utente_id}."
            )
            return False

        fields_to_update, params = [], []
        if nome_completo is not None:
            fields_to_update.append("nome_completo = %s")
            params.append(nome_completo)
        if email is not None:
            fields_to_update.append("email = %s")
            params.append(email)
        if ruolo is not None:
            if ruolo not in ["admin", "archivista", "consultatore"]:
                raise DBDataError(f"Ruolo non valido: {ruolo}")
            fields_to_update.append("ruolo = %s")
            params.append(ruolo)
        if attivo is not None:
            fields_to_update.append("attivo = %s")
            params.append(attivo)

        if not fields_to_update:
            return True  # Nessuna modifica richiesta

        fields_to_update.append("data_modifica = CURRENT_TIMESTAMP")
        query = f"UPDATE {self.schema}.utente SET {', '.join(fields_to_update)} WHERE id = %s"
        params.append(utente_id)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(
                            f"Utente con ID {utente_id} non trovato per l'aggiornamento."
                        )

            self.logger.info(f"Dettagli utente ID {utente_id} aggiornati.")
            return True
        except (DBNotFoundError, DBDataError, DBUniqueConstraintError) as e:
            self.logger.error(
                f"Errore previsto aggiornando utente {utente_id}: {e}", exc_info=True
            )
            raise e
        except Exception as e:
            self.logger.error(
                f"Errore imprevisto DB aggiornando utente {utente_id}: {e}",
                exc_info=True,
            )
            raise DBMError(f"Impossibile aggiornare l'utente: {e}") from e

    def reset_user_password(self, utente_id: int, new_password_hash: str) -> bool:
        """Resetta la password di un utente in modo transazionale e sicuro."""
        query = f"UPDATE {self.schema}.utente SET password_hash = %s, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (new_password_hash, utente_id))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(
                            f"Utente con ID {utente_id} non trovato per reset password."
                        )

            self.logger.info(f"Password resettata per utente ID {utente_id}.")
            return True
        except DBNotFoundError as e:
            self.logger.warning(e)
            raise e
        except Exception as e:
            self.logger.error(
                f"Errore DB durante il reset password per utente ID {utente_id}: {e}",
                exc_info=True,
            )
            raise DBMError(f"Errore database durante il reset password: {e}") from e

    def _update_user_active_status(
        self, utente_id: int, nuovo_stato_attivo: bool
    ) -> bool:
        """Metodo helper per attivare o disattivare un utente in modo transazionale."""
        query = f"UPDATE {self.schema}.utente SET attivo = %s, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (nuovo_stato_attivo, utente_id))
                    if cur.rowcount == 0:
                        raise DBNotFoundError(
                            f"Utente con ID {utente_id} non trovato per aggiornamento stato."
                        )

            status_str = "attivato" if nuovo_stato_attivo else "disattivato"
            self.logger.info(f"Utente ID {utente_id} {status_str}.")
            return True
        except (DBNotFoundError, DBMError) as e:
            self.logger.error(
                f"Errore previsto aggiornando stato utente {utente_id}: {e}"
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Errore imprevisto aggiornando stato utente {utente_id}: {e}",
                exc_info=True,
            )
            raise DBMError(f"Impossibile aggiornare lo stato dell'utente: {e}") from e

    def deactivate_user(self, utente_id: int) -> bool:
        """Disattiva un utente. Utilizza _update_user_active_status."""
        return self._update_user_active_status(utente_id, False)

    def activate_user(self, utente_id: int) -> bool:
        """Riattiva un utente. Utilizza _update_user_active_status."""
        return self._update_user_active_status(utente_id, True)

    def delete_user_permanently(self, utente_id: int) -> bool:
        """Elimina fisicamente un utente in modo transazionale e sicuro."""
        utente_da_eliminare = self.get_utente_by_id(
            utente_id
        )  # Usa il metodo già refattorizzato
        if not utente_da_eliminare:
            self.logger.warning(
                f"Tentativo di eliminare utente ID {utente_id} non trovato."
            )
            return False

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # La logica di controllo e l'eliminazione avvengono nella stessa transazione
                    if utente_da_eliminare.get("ruolo") == "admin":
                        cur.execute(
                            f"SELECT COUNT(*) AS count FROM {self.schema}.utente WHERE ruolo = 'admin' AND attivo = TRUE"
                        )
                        count_result = cur.fetchone()
                        if count_result and count_result["count"] <= 1:
                            self.logger.error(
                                f"Tentativo di eliminare l'unico admin attivo (ID: {utente_id}). Operazione negata."
                            )
                            # Non solleviamo un'eccezione, ma restituiamo False per bloccare l'operazione
                            # Il context manager eseguirà un rollback/commit innocuo.
                            return False

                    # Se i controlli sono superati, procedi con l'eliminazione
                    cur.execute(
                        f"DELETE FROM {self.schema}.utente WHERE id = %s", (utente_id,)
                    )

                    if cur.rowcount == 0:
                        # Caso limite in cui l'utente viene eliminato tra il get iniziale e qui
                        raise DBNotFoundError(
                            f"Utente ID {utente_id} scomparso prima dell'eliminazione finale."
                        )

            # Il commit è automatico se tutto va a buon fine
            self.logger.info(
                f"Utente ID {utente_id} eliminato fisicamente con successo."
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Errore durante l'eliminazione dell'utente ID {utente_id}: {e}",
                exc_info=True,
            )
            raise DBMError(f"Impossibile eliminare l'utente: {e}") from e
