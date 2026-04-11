import os
import base64
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from monitor.legacy_code.os_class import os_manager


@pytest.fixture
def manager():
    return os_manager(parent=None)


class TestGetRustdeskId:

    # ------------------------------------------------------------------ helpers

    def _write_toml(self, directory, content):
        """Write a RustDesk.toml file in *directory* and return its path."""
        path = os.path.join(directory, "RustDesk.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    # ------------------------------------------------------------------ CLI tests

    def test_returns_id_from_cli(self, manager):
        """When the CLI returns an ID, that value is returned."""
        with patch.object(manager, "_find_rustdesk_executable", return_value="/usr/bin/rustdesk"):
            mock_result = MagicMock()
            mock_result.stdout = "123 456 789\n"
            with patch("subprocess.run", return_value=mock_result):
                assert manager.get_rustdesk_id() == "123 456 789"

    def test_cli_strips_whitespace(self, manager):
        """Whitespace around the CLI output is stripped."""
        with patch.object(manager, "_find_rustdesk_executable", return_value="/usr/bin/rustdesk"):
            mock_result = MagicMock()
            mock_result.stdout = "  987 654 321  \n"
            with patch("subprocess.run", return_value=mock_result):
                assert manager.get_rustdesk_id() == "987 654 321"

    def test_falls_back_to_config_when_cli_empty(self, manager):
        """If CLI returns empty stdout, config file is tried."""
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, "id = 'config-id-001'\n")

            with patch.object(manager, "_find_rustdesk_executable", return_value="/usr/bin/rustdesk"):
                mock_result = MagicMock()
                mock_result.stdout = ""
                with patch("subprocess.run", return_value=mock_result):
                    with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                        assert manager.get_rustdesk_id() == "config-id-001"

    def test_falls_back_to_config_when_cli_raises(self, manager):
        """If CLI subprocess raises an exception, config file is tried."""
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, "id = 'config-id-002'\n")

            with patch.object(manager, "_find_rustdesk_executable", return_value="/usr/bin/rustdesk"):
                with patch("subprocess.run", side_effect=OSError("not found")):
                    with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                        assert manager.get_rustdesk_id() == "config-id-002"

    def test_falls_back_to_config_when_no_executable(self, manager):
        """If no executable is found, config file is tried."""
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, "id = 'config-id-003'\n")

            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "config-id-003"

    # ------------------------------------------------------------------ config file tests

    def test_parses_id_with_single_quotes(self, manager):
        """Parses `id = 'value'` format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, "id = 'abc123'\n")
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "abc123"

    def test_parses_id_with_double_quotes(self, manager):
        """Parses `id = "value"` format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, 'id = "xyz789"\n')
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "xyz789"

    def test_parses_id_without_quotes(self, manager):
        """Parses `id = value` format (no quotes)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, "id = noquotes\n")
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "noquotes"

    def test_skips_missing_config_file(self, manager):
        """A path that does not exist is silently skipped."""
        with patch.object(manager, "_find_rustdesk_executable", return_value=None):
            with patch.object(manager, "_get_rustdesk_config_paths",
                              return_value=["/nonexistent/path/RustDesk.toml"]):
                assert manager.get_rustdesk_id() is None

    def test_uses_first_valid_config_path(self, manager):
        """When multiple config paths exist, the first valid one wins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            first_path = self._write_toml(tmpdir, "id = 'first-id'\n")
            second_path = os.path.join(tmpdir, "second.toml")
            with open(second_path, "w") as f:
                f.write("id = 'second-id'\n")

            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths",
                                  return_value=[first_path, second_path]):
                    assert manager.get_rustdesk_id() == "first-id"

    def test_skips_non_id_lines(self, manager):
        """Lines that are not the `id` key are not mistakenly matched."""
        content = (
            "relay-server = 'relay.example.com'\n"
            "some_id = 'should-not-match'\n"
            "id = 'correct-id'\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, content)
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "correct-id"

    # ------------------------------------------------------------------ no RustDesk installed

    def test_returns_none_when_not_installed(self, manager):
        """Returns None when RustDesk is not installed and no config exists."""
        with patch.object(manager, "_find_rustdesk_executable", return_value=None):
            with patch.object(manager, "_get_rustdesk_config_paths", return_value=[]):
                assert manager.get_rustdesk_id() is None

    # ------------------------------------------------------------------ helper method tests

    def test_find_rustdesk_executable_returns_none_when_absent(self, manager):
        """_find_rustdesk_executable returns None when no executable exists."""
        with patch("psutil.process_iter", return_value=[]):
            with patch("shutil.which", return_value=None):
                with patch("os.path.isfile", return_value=False):
                    with patch("glob.glob", return_value=[]):
                        assert manager._find_rustdesk_executable() is None

    def test_find_rustdesk_executable_finds_via_which(self, manager):
        """_find_rustdesk_executable returns the PATH result when shutil.which succeeds."""
        fake_path = "/usr/local/bin/rustdesk"
        with patch("psutil.process_iter", return_value=[]):
            with patch("shutil.which", return_value=fake_path):
                with patch("os.path.isfile", return_value=True):
                    assert manager._find_rustdesk_executable() == fake_path

    def test_config_paths_returned_for_windows(self, manager):
        """_get_rustdesk_config_paths returns Windows-specific paths on Windows."""
        with patch.object(manager, "current_os", "Windows"):
            with patch.dict(os.environ, {"APPDATA": r"C:\Users\test\AppData\Roaming"}):
                paths = manager._get_rustdesk_config_paths()
        assert any("RustDesk.toml" in p for p in paths)
        assert any("AppData" in p or "ServiceProfiles" in p for p in paths)

    def test_config_paths_returned_for_linux(self, manager):
        """_get_rustdesk_config_paths returns Linux-specific paths on Linux."""
        with patch.object(manager, "current_os", "Linux"):
            paths = manager._get_rustdesk_config_paths()
        assert any(".config/rustdesk/RustDesk.toml" in p for p in paths)

    # ------------------------------------------------------------------ enc_id decryption tests

    def _make_enc_id_toml(self, plaintext_id: str, key_offset: int = 0) -> str:
        """
        Build a valid RustDesk 1.2+ style TOML with enc_id and key_pair.
        key_offset allows testing non-zero-offset key slices (must be 0 or 16).
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # 32-byte first sub-array; encrypt using the 16-byte window at key_offset
        key_bytes_32 = bytes(range(32))
        aes_key = key_bytes_32[key_offset:key_offset + 16]
        nonce = bytes(12)

        ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext_id.encode(), None)
        b64 = base64.b64encode(ciphertext).decode()
        enc_id = "00" + b64  # "00" version prefix

        # Represent key_bytes_32 as a TOML inline integer array
        key_array = ", ".join(str(b) for b in key_bytes_32)
        return (
            f"enc_id = '{enc_id}'\n"
            f"password = 'irrelevant'\n"
            f"salt = 'abc'\n"
            f"key_pair = [\n"
            f"    [{key_array}],\n"
            f"    [1, 2, 3]\n"
            f"]\n"
        )

    def test_decodes_enc_id_when_no_plain_id(self, manager):
        """Falls back to enc_id decryption when the config has no plain 'id' key."""
        toml = self._make_enc_id_toml("987654321")
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, toml)
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "987654321"

    def test_decodes_enc_id_with_offset_key(self, manager):
        """Multi-candidate logic finds the correct key even when offset != 0."""
        toml = self._make_enc_id_toml("111222333", key_offset=16)
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, toml)
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "111222333"

    def test_plain_id_takes_priority_over_enc_id(self, manager):
        """When both plain 'id' and 'enc_id' are present, plain 'id' wins."""
        toml = "id = 'direct-id'\n" + self._make_enc_id_toml("should-not-be-returned")
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, toml)
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    assert manager.get_rustdesk_id() == "direct-id"

    def test_decode_enc_id_returns_none_without_key_pair(self, manager):
        """_decode_enc_id returns None when key_pair_raw is None."""
        assert manager._decode_enc_id("00AAAA", None) is None

    def test_decode_enc_id_returns_none_on_bad_ciphertext(self, manager):
        """_decode_enc_id returns None when all key candidates fail authentication."""
        key_array = ", ".join(str(b) for b in range(32))
        key_pair_raw = f"[[{key_array}], [1, 2, 3]]"
        # "00" prefix + random base64 that will fail AES-GCM authentication for all candidates
        assert manager._decode_enc_id("00aGVsbG8=", key_pair_raw) is None

    # ------------------------------------------------------------------ NaCl secretbox tests

    def _make_nacl_enc_id(self, plaintext: str, key: bytes) -> str:
        """Build a RustDesk-style enc_id encrypted with NaCl secretbox."""
        import nacl.secret
        box = nacl.secret.SecretBox(key)
        # .ciphertext strips the prepended nonce, giving MAC + encrypted data
        ciphertext = box.encrypt(plaintext.encode(), nonce=bytes(24)).ciphertext
        return "00" + base64.b64encode(ciphertext).decode()

    def test_decode_enc_id_nacl_succeeds(self, manager):
        """_decode_enc_id_nacl decrypts correctly when the UUID key matches."""
        key = (b"my-fake-machine-uuid-padded-here" + b"\x00" * 32)[:32]
        enc_id = self._make_nacl_enc_id("987654321", key)
        with patch.object(manager, "_get_machine_uuid_bytes", return_value=[key]):
            assert manager._decode_enc_id_nacl(enc_id) == "987654321"

    def test_decode_enc_id_nacl_tries_all_candidates(self, manager):
        """_decode_enc_id_nacl falls through wrong candidates to the correct one."""
        wrong_key = b"W" * 32
        correct_key = b"C" * 32
        enc_id = self._make_nacl_enc_id("555444333", correct_key)
        with patch.object(manager, "_get_machine_uuid_bytes", return_value=[wrong_key, correct_key]):
            assert manager._decode_enc_id_nacl(enc_id) == "555444333"

    def test_decode_enc_id_nacl_returns_none_on_wrong_key(self, manager):
        """_decode_enc_id_nacl returns None when no candidate matches."""
        enc_id = self._make_nacl_enc_id("123", b"A" * 32)
        with patch.object(manager, "_get_machine_uuid_bytes", return_value=[b"B" * 32]):
            assert manager._decode_enc_id_nacl(enc_id) is None

    def test_decode_enc_id_nacl_returns_none_without_uuid(self, manager):
        """_decode_enc_id_nacl returns None when no machine UUID is available."""
        with patch.object(manager, "_get_machine_uuid_bytes", return_value=[]):
            assert manager._decode_enc_id_nacl("00AAAA") is None

    def test_nacl_is_tried_after_aes_gcm_fails(self, manager):
        """get_rustdesk_id falls back to NaCl after AES-GCM candidates all fail."""
        key = b"uuid-key-padded-to-32-bytes--000"
        enc_id = self._make_nacl_enc_id("111222333", key)
        toml = f"enc_id = '{enc_id}'\nsalt = 'abc'\nkey_pair = []\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = self._write_toml(tmpdir, toml)
            with patch.object(manager, "_find_rustdesk_executable", return_value=None):
                with patch.object(manager, "_get_rustdesk_config_paths", return_value=[toml_path]):
                    with patch.object(manager, "_get_machine_uuid_bytes", return_value=[key]):
                        assert manager.get_rustdesk_id() == "111222333"
