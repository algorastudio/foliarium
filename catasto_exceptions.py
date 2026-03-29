"""
catasto_exceptions.py — Eccezioni personalizzate del layer database di Foliarium.

Estratte da catasto_db_manager.py per consentire l'importazione delle eccezioni
senza caricare l'intero modulo DB (che dipende da PyQt6 e psycopg2).

Backward compatibility garantita:
    from catasto_db_manager import DBMError  # funziona ancora
    from catasto_exceptions import DBMError   # nuovo percorso preferito
"""


class DBMError(Exception):
    """Classe base per errori specifici del DBManager."""
    pass


class DBUniqueConstraintError(DBMError):
    """Sollevata quando un vincolo di unicità viene violato."""

    def __init__(self, message, constraint_name=None, details=None):
        super().__init__(message)
        self.constraint_name = constraint_name
        self.details = details


class DBNotFoundError(DBMError):
    """Sollevata quando un record atteso non viene trovato per un'operazione."""
    pass


class DBDataError(DBMError):
    """Sollevata per errori relativi a dati o parametri forniti non validi."""
    pass
