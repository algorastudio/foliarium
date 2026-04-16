"""
tests/unit/test_update_checker.py
==================================
Unit test per update_checker.py — parsing versioni, ricerca asset,
verifica SHA-256, fetch release info.

Tutti i test mockano le chiamate di rete (urllib) per essere offline.
"""

import hashlib
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from update_checker import (
    _find_asset,
    _parse_version,
    _verify_sha256,
    _fetch_checksum,
    _fetch_release_info,
    check_for_updates,
)


# ===========================================================================
# _parse_version
# ===========================================================================


@pytest.mark.unit
class TestParseVersion:
    def test_simple(self):
        assert _parse_version("1.5.3") == (1, 5, 3)

    def test_with_v_prefix(self):
        assert _parse_version("v2.0.1") == (2, 0, 1)

    def test_two_parts(self):
        assert _parse_version("1.6") == (1, 6)

    def test_four_parts_truncated(self):
        """Solo i primi 3 segmenti vengono usati."""
        assert _parse_version("1.2.3.4") == (1, 2, 3)

    def test_empty_string(self):
        assert _parse_version("") == (0, 0, 0)

    def test_non_numeric(self):
        assert _parse_version("abc") == (0, 0, 0)

    def test_none_input(self):
        """None causa AttributeError — la funzione accetta solo stringhe."""
        with pytest.raises(AttributeError):
            _parse_version(None)

    def test_comparison_newer(self):
        assert _parse_version("v2.0.0") > _parse_version("v1.9.9")

    def test_comparison_equal(self):
        assert _parse_version("1.6.0") == _parse_version("v1.6.0")

    def test_comparison_older(self):
        assert _parse_version("1.5.3") < _parse_version("1.6.0")


# ===========================================================================
# _find_asset
# ===========================================================================


@pytest.mark.unit
class TestFindAsset:
    def test_finds_installer(self):
        assets = [
            {"name": "Foliarium_1.6.0_Setup.exe", "browser_download_url": "http://..."},
            {"name": "Foliarium_1.6.0_Portabile.zip", "browser_download_url": "http://..."},
        ]
        result = _find_asset(assets, "_Setup.exe")
        assert result is not None
        assert result["name"] == "Foliarium_1.6.0_Setup.exe"

    def test_finds_portable(self):
        assets = [
            {"name": "Foliarium_1.6.0_Setup.exe"},
            {"name": "Foliarium_1.6.0_Portabile.zip"},
        ]
        result = _find_asset(assets, "_Portabile.zip")
        assert result is not None
        assert "Portabile" in result["name"]

    def test_not_found(self):
        assets = [{"name": "README.md"}]
        result = _find_asset(assets, "_Setup.exe")
        assert result is None

    def test_empty_list(self):
        assert _find_asset([], "_Setup.exe") is None

    def test_missing_name_key(self):
        assets = [{"url": "http://..."}]
        result = _find_asset(assets, "_Setup.exe")
        assert result is None


# ===========================================================================
# _verify_sha256
# ===========================================================================


@pytest.mark.unit
class TestVerifySha256:
    def test_correct_hash(self, tmp_path):
        test_file = tmp_path / "test.bin"
        content = b"Hello Foliarium"
        test_file.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert _verify_sha256(str(test_file), expected)

    def test_wrong_hash(self, tmp_path):
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"Hello")
        assert not _verify_sha256(str(test_file), "0" * 64)

    def test_case_insensitive(self, tmp_path):
        test_file = tmp_path / "test.bin"
        content = b"test data"
        test_file.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest().upper()
        assert _verify_sha256(str(test_file), expected)

    def test_hash_with_filename_suffix(self, tmp_path):
        """Formato sha256sum: 'hash  filename'."""
        test_file = tmp_path / "test.bin"
        content = b"data"
        test_file.write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()
        hash_line = f"{sha}  test.bin"
        assert _verify_sha256(str(test_file), hash_line)

    def test_nonexistent_file(self):
        assert not _verify_sha256("/nonexistent/file.bin", "abc123")

    def test_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.bin"
        test_file.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert _verify_sha256(str(test_file), expected)


# ===========================================================================
# _fetch_checksum
# ===========================================================================


@pytest.mark.unit
class TestFetchChecksum:
    @patch("update_checker.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"abc123def456  Foliarium_Setup.exe\n"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _fetch_checksum("http://example.com/file.sha256")
        assert result == "abc123def456  Foliarium_Setup.exe"

    @patch("update_checker.urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Network error")
        result = _fetch_checksum("http://example.com/file.sha256")
        assert result is None


# ===========================================================================
# _fetch_release_info
# ===========================================================================


@pytest.mark.unit
class TestFetchReleaseInfo:
    @patch("update_checker.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        release_data = {"tag_name": "v1.7.0", "assets": []}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(release_data).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _fetch_release_info(timeout=1)
        assert result is not None
        assert result["tag_name"] == "v1.7.0"

    @patch("update_checker.urllib.request.urlopen")
    def test_url_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("No network")

        result = _fetch_release_info(timeout=1)
        assert result is None

    @patch("update_checker.urllib.request.urlopen")
    def test_generic_exception(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Something broke")
        result = _fetch_release_info(timeout=1)
        assert result is None


# ===========================================================================
# check_for_updates (logica di alto livello)
# ===========================================================================


@pytest.mark.unit
class TestCheckForUpdates:
    @patch("update_checker._fetch_release_info", return_value=None)
    def test_no_network(self, _mock):
        """Se GitHub non raggiungibile, ritorna False."""
        result = check_for_updates(None)
        assert result is False

    @patch("update_checker._show_update_available_dialog")
    @patch("update_checker._fetch_release_info")
    @patch("config.IS_TEST_ENV", False)
    @patch("config.IS_DEMO_MODE", False)
    @patch("config.APP_VERSION", "1.6.0")
    def test_same_version(self, mock_fetch, mock_dialog):
        mock_fetch.return_value = {"tag_name": "v1.6.0", "assets": []}
        result = check_for_updates(None)
        assert result is False
        mock_dialog.assert_not_called()

    @patch("update_checker._show_update_available_dialog")
    @patch("update_checker._fetch_release_info")
    @patch("config.IS_TEST_ENV", False)
    @patch("config.IS_DEMO_MODE", False)
    @patch("config.APP_VERSION", "1.6.0")
    def test_older_remote(self, mock_fetch, mock_dialog):
        mock_fetch.return_value = {"tag_name": "v1.5.0", "assets": []}
        result = check_for_updates(None)
        assert result is False

    @patch("update_checker._show_update_available_dialog")
    @patch("update_checker._fetch_release_info")
    @patch("config.IS_TEST_ENV", False)
    @patch("config.IS_DEMO_MODE", False)
    @patch("config.APP_VERSION", "1.6.0")
    def test_newer_remote_shows_dialog(self, mock_fetch, mock_dialog):
        mock_fetch.return_value = {
            "tag_name": "v2.0.0",
            "assets": [],
            "body": "New release notes",
        }
        result = check_for_updates(MagicMock())
        assert result is True
        mock_dialog.assert_called_once()
