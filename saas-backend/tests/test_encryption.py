"""Tests for encryption utilities and EncryptedString TypeDecorator."""

import pytest

from app.utils.encryption import decrypt_pii, encrypt_pii, EncryptedString


class TestEncryptDecryptPII:
    def test_round_trip(self):
        plain = "11999887766"
        encrypted = encrypt_pii(plain)
        assert encrypted != plain
        assert decrypt_pii(encrypted) == plain

    def test_different_nonces(self):
        plain = "same-value"
        enc1 = encrypt_pii(plain)
        enc2 = encrypt_pii(plain)
        assert enc1 != enc2  # Different nonces produce different ciphertexts
        assert decrypt_pii(enc1) == plain
        assert decrypt_pii(enc2) == plain

    def test_empty_string(self):
        encrypted = encrypt_pii("")
        assert decrypt_pii(encrypted) == ""

    def test_unicode(self):
        plain = "João +55 (11) 99999-8888"
        encrypted = encrypt_pii(plain)
        assert decrypt_pii(encrypted) == plain

    def test_decrypt_invalid_raises(self):
        with pytest.raises(Exception):
            decrypt_pii("not-valid-base64-encrypted-data!!!")

    def test_cpf_aliases(self):
        from app.utils.encryption import encrypt_cpf, decrypt_cpf
        assert encrypt_cpf is encrypt_pii
        assert decrypt_cpf is decrypt_pii


class TestEncryptedStringType:
    def setup_method(self):
        self.type_dec = EncryptedString()

    def test_bind_none(self):
        assert self.type_dec.process_bind_param(None, None) is None

    def test_bind_empty(self):
        assert self.type_dec.process_bind_param("", None) == ""

    def test_bind_encrypts(self):
        result = self.type_dec.process_bind_param("11999887766", None)
        assert result is not None
        assert result != "11999887766"
        assert decrypt_pii(result) == "11999887766"

    def test_result_none(self):
        assert self.type_dec.process_result_value(None, None) is None

    def test_result_empty(self):
        assert self.type_dec.process_result_value("", None) == ""

    def test_result_decrypts(self):
        encrypted = encrypt_pii("11999887766")
        result = self.type_dec.process_result_value(encrypted, None)
        assert result == "11999887766"

    def test_result_plain_text_fallback(self):
        """Pre-migration plain text values should be returned as-is."""
        result = self.type_dec.process_result_value("11999887766", None)
        assert result == "11999887766"
