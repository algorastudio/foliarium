"""
tests/unit/test_catasto_exceptions.py
=======================================
Unit test per catasto_exceptions.py — eccezioni personalizzate del layer DB.
Marker: unit
"""
from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from catasto_exceptions import (
    DBMError,
    DBUniqueConstraintError,
    DBNotFoundError,
    DBDataError,
)


@pytest.mark.unit
class TestDBMError:

    def test_is_exception(self):
        assert issubclass(DBMError, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(DBMError):
            raise DBMError("errore base")

    def test_message_preserved(self):
        try:
            raise DBMError("messaggio test")
        except DBMError as e:
            assert str(e) == "messaggio test"

    def test_catch_as_exception(self):
        with pytest.raises(Exception):
            raise DBMError("catturato come Exception")


@pytest.mark.unit
class TestDBUniqueConstraintError:

    def test_is_dbmerror(self):
        assert issubclass(DBUniqueConstraintError, DBMError)

    def test_is_exception(self):
        assert issubclass(DBUniqueConstraintError, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(DBUniqueConstraintError):
            raise DBUniqueConstraintError("duplicato")

    def test_catch_as_dbmerror(self):
        with pytest.raises(DBMError):
            raise DBUniqueConstraintError("duplicato")

    def test_constraint_name_stored(self):
        e = DBUniqueConstraintError("duplicato", constraint_name="uq_username")
        assert e.constraint_name == "uq_username"

    def test_details_stored(self):
        e = DBUniqueConstraintError("duplicato", details="dettagli")
        assert e.details == "dettagli"

    def test_constraint_name_none_by_default(self):
        e = DBUniqueConstraintError("duplicato")
        assert e.constraint_name is None

    def test_details_none_by_default(self):
        e = DBUniqueConstraintError("duplicato")
        assert e.details is None

    def test_message_preserved(self):
        try:
            raise DBUniqueConstraintError("Username già esistente")
        except DBUniqueConstraintError as e:
            assert "Username già esistente" in str(e)


@pytest.mark.unit
class TestDBNotFoundError:

    def test_is_dbmerror(self):
        assert issubclass(DBNotFoundError, DBMError)

    def test_is_exception(self):
        assert issubclass(DBNotFoundError, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(DBNotFoundError):
            raise DBNotFoundError("non trovato")

    def test_catch_as_dbmerror(self):
        with pytest.raises(DBMError):
            raise DBNotFoundError("non trovato")

    def test_message_preserved(self):
        try:
            raise DBNotFoundError("Partita ID 99 non trovata")
        except DBNotFoundError as e:
            assert "99" in str(e)


@pytest.mark.unit
class TestDBDataError:

    def test_is_dbmerror(self):
        assert issubclass(DBDataError, DBMError)

    def test_is_exception(self):
        assert issubclass(DBDataError, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(DBDataError):
            raise DBDataError("dato non valido")

    def test_catch_as_dbmerror(self):
        with pytest.raises(DBMError):
            raise DBDataError("dato non valido")

    def test_message_preserved(self):
        try:
            raise DBDataError("ID non valido")
        except DBDataError as e:
            assert "ID non valido" in str(e)


@pytest.mark.unit
class TestExceptionHierarchy:

    def test_dbnotfound_not_dbunique(self):
        """DBNotFoundError should not be caught as DBUniqueConstraintError."""
        with pytest.raises(DBNotFoundError):
            try:
                raise DBNotFoundError("test")
            except DBUniqueConstraintError:
                pass  # should not be caught here

    def test_dbuniqueconstraint_not_dbnotfound(self):
        """DBUniqueConstraintError should not be caught as DBNotFoundError."""
        with pytest.raises(DBUniqueConstraintError):
            try:
                raise DBUniqueConstraintError("test")
            except DBNotFoundError:
                pass

    def test_all_are_dbmerror_siblings(self):
        """All custom exceptions inherit from DBMError."""
        errs = [DBUniqueConstraintError("a"), DBNotFoundError("b"), DBDataError("c")]
        for err in errs:
            assert isinstance(err, DBMError)

    def test_backward_compat_import_from_catasto_db_manager(self):
        """Exceptions must also be importable from catasto_db_manager for backward compat."""
        from catasto_db_manager import DBMError as DBMError2
        assert DBMError2 is DBMError

    def test_chained_exception(self):
        """Verify exception chaining works as expected."""
        try:
            try:
                raise ValueError("original")
            except ValueError as e:
                raise DBDataError("wrapped") from e
        except DBDataError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
