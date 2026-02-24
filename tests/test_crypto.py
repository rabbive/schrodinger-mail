"""Tests for crypto_utils.py — Kyber, Dilithium, AES-256-GCM, payloads, and key derivation."""

import os

import pytest

import crypto_utils


# ── KEM (Kyber768) ────────────────────────────────────────────────────────────

class TestKEM:
    def test_keygen_produces_valid_keys(self):
        pk, sk = crypto_utils.generate_kem_keypair()
        assert isinstance(pk, bytes) and len(pk) > 0
        assert isinstance(sk, bytes) and len(sk) > 0

    def test_encapsulate_decapsulate_roundtrip(self):
        pk, sk = crypto_utils.generate_kem_keypair()
        encap_key, shared_secret_sender = crypto_utils.kem_encapsulate(pk)
        shared_secret_receiver = crypto_utils.kem_decapsulate(encap_key, sk)
        assert shared_secret_sender == shared_secret_receiver
        assert len(shared_secret_sender) == 32

    def test_wrong_sk_gives_different_secret(self):
        pk1, sk1 = crypto_utils.generate_kem_keypair()
        _, sk2 = crypto_utils.generate_kem_keypair()
        encap_key, ss1 = crypto_utils.kem_encapsulate(pk1)
        ss2 = crypto_utils.kem_decapsulate(encap_key, sk2)
        assert ss1 != ss2

    def test_algorithm_name_resolved(self):
        assert crypto_utils.KEM_ALG in ("Kyber768", "ML-KEM-768")


# ── Digital Signatures (Dilithium3) ──────────────────────────────────────────

class TestSignatures:
    def test_sign_and_verify(self):
        pk, sk = crypto_utils.generate_sig_keypair()
        msg = b"Hello, quantum world!"
        sig = crypto_utils.sign(msg, sk)
        assert crypto_utils.verify(msg, sig, pk) is True

    def test_wrong_key_fails_verification(self):
        _, sk = crypto_utils.generate_sig_keypair()
        pk2, _ = crypto_utils.generate_sig_keypair()
        msg = b"Authentic message"
        sig = crypto_utils.sign(msg, sk)
        assert crypto_utils.verify(msg, sig, pk2) is False

    def test_tampered_message_fails_verification(self):
        pk, sk = crypto_utils.generate_sig_keypair()
        msg = b"Original message"
        sig = crypto_utils.sign(msg, sk)
        assert crypto_utils.verify(b"Tampered message", sig, pk) is False

    def test_algorithm_name_resolved(self):
        assert crypto_utils.SIG_ALG in ("Dilithium3", "ML-DSA-65")


# ── AES-256-GCM ─────────────────────────────────────────────────────────────

class TestAES:
    def test_encrypt_decrypt_roundtrip(self):
        key = os.urandom(32)
        plaintext = b"Sensitive email content"
        ct, nonce, tag = crypto_utils.aes_gcm_encrypt(plaintext, key)
        result = crypto_utils.aes_gcm_decrypt(ct, key, nonce, tag)
        assert result == plaintext

    def test_wrong_key_fails(self):
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        ct, nonce, tag = crypto_utils.aes_gcm_encrypt(b"data", key1)
        with pytest.raises(ValueError):
            crypto_utils.aes_gcm_decrypt(ct, key2, nonce, tag)

    def test_tampered_ciphertext_fails(self):
        key = os.urandom(32)
        ct, nonce, tag = crypto_utils.aes_gcm_encrypt(b"data", key)
        tampered = bytearray(ct)
        tampered[0] ^= 0xFF
        with pytest.raises(ValueError):
            crypto_utils.aes_gcm_decrypt(bytes(tampered), key, nonce, tag)

    def test_bad_key_length_raises(self):
        with pytest.raises(ValueError, match="32-byte key"):
            crypto_utils.aes_gcm_encrypt(b"x", os.urandom(16))
        with pytest.raises(ValueError, match="32-byte key"):
            crypto_utils.aes_gcm_decrypt(b"x", os.urandom(16), os.urandom(12), os.urandom(16))

    def test_nonce_is_12_bytes(self):
        key = os.urandom(32)
        _, nonce, _ = crypto_utils.aes_gcm_encrypt(b"data", key)
        assert len(nonce) == 12

    def test_tag_is_16_bytes(self):
        key = os.urandom(32)
        _, _, tag = crypto_utils.aes_gcm_encrypt(b"data", key)
        assert len(tag) == 16


# ── Payload Encoding ─────────────────────────────────────────────────────────

class TestPayload:
    def test_build_and_split_roundtrip(self):
        sig = os.urandom(128)
        msg = b"Test message content"
        payload = crypto_utils.build_payload(sig, msg)
        sig_out, msg_out = crypto_utils.split_payload(payload)
        assert sig_out == sig
        assert msg_out == msg

    def test_empty_message(self):
        sig = os.urandom(64)
        payload = crypto_utils.build_payload(sig, b"")
        sig_out, msg_out = crypto_utils.split_payload(payload)
        assert sig_out == sig
        assert msg_out == b""

    def test_too_short_payload_raises(self):
        with pytest.raises(ValueError, match="too short"):
            crypto_utils.split_payload(b"\x00")

    def test_bad_length_prefix_raises(self):
        with pytest.raises(ValueError, match="exceeds"):
            crypto_utils.split_payload(b"\xff\xff\xff\xff" + b"short")


# ── Key Fingerprints ─────────────────────────────────────────────────────────

class TestFingerprints:
    def test_fingerprint_format(self):
        key = os.urandom(100)
        fp = crypto_utils.key_fingerprint(key)
        parts = fp.split(" ")
        assert len(parts) == 16  # 64 hex chars / 4 = 16 groups
        assert all(len(p) == 4 for p in parts)

    def test_short_fingerprint_length(self):
        fp = crypto_utils.key_fingerprint_short(os.urandom(100))
        assert len(fp) == 16

    def test_deterministic(self):
        key = os.urandom(50)
        assert crypto_utils.key_fingerprint(key) == crypto_utils.key_fingerprint(key)

    def test_different_keys_different_fingerprints(self):
        k1, k2 = os.urandom(50), os.urandom(50)
        assert crypto_utils.key_fingerprint(k1) != crypto_utils.key_fingerprint(k2)


# ── Password KDF ─────────────────────────────────────────────────────────────

class TestPasswordKDF:
    def test_derive_with_auto_salt(self):
        key, salt = crypto_utils.derive_key_from_password("mypassword")
        assert len(key) == 32
        assert len(salt) == 16

    def test_same_password_and_salt_gives_same_key(self):
        key1, salt = crypto_utils.derive_key_from_password("secret")
        key2, _ = crypto_utils.derive_key_from_password("secret", salt)
        assert key1 == key2

    def test_different_password_gives_different_key(self):
        _, salt = crypto_utils.derive_key_from_password("alpha")
        key_a, _ = crypto_utils.derive_key_from_password("alpha", salt)
        key_b, _ = crypto_utils.derive_key_from_password("bravo", salt)
        assert key_a != key_b


# ── RSA Functions ────────────────────────────────────────────────────────────

class TestRSA:
    def test_rsa_keygen(self):
        pk, sk = crypto_utils.generate_rsa_keypair()
        assert pk.startswith(b"-----BEGIN PUBLIC KEY-----")
        assert sk.startswith(b"-----BEGIN RSA PRIVATE KEY-----")

    def test_rsa_encrypt_decrypt_roundtrip(self):
        pk, sk = crypto_utils.generate_rsa_keypair()
        plaintext = b"Short message for RSA"
        ct = crypto_utils.rsa_encrypt(plaintext, pk)
        result = crypto_utils.rsa_decrypt(ct, sk)
        assert result == plaintext

    def test_rsa_wrong_key_fails(self):
        pk1, _ = crypto_utils.generate_rsa_keypair()
        _, sk2 = crypto_utils.generate_rsa_keypair()
        ct = crypto_utils.rsa_encrypt(b"data", pk1)
        with pytest.raises(ValueError):
            crypto_utils.rsa_decrypt(ct, sk2)


# ── Hybrid Encryption (RSA + Kyber) ─────────────────────────────────────────

class TestHybridEncryption:
    def test_hybrid_encapsulate_decapsulate(self):
        kyber_pk, kyber_sk = crypto_utils.generate_kem_keypair()
        rsa_pk, rsa_sk = crypto_utils.generate_rsa_keypair()

        rsa_ct, kyber_encap, combined_ss = crypto_utils.hybrid_encapsulate(kyber_pk, rsa_pk)
        assert len(combined_ss) == 32

        recovered_ss = crypto_utils.hybrid_decapsulate(rsa_ct, kyber_encap, rsa_sk, kyber_sk)
        assert recovered_ss == combined_ss

    def test_hybrid_wrong_rsa_key_fails(self):
        kyber_pk, kyber_sk = crypto_utils.generate_kem_keypair()
        rsa_pk, _ = crypto_utils.generate_rsa_keypair()
        _, rsa_sk_wrong = crypto_utils.generate_rsa_keypair()

        rsa_ct, kyber_encap, _ = crypto_utils.hybrid_encapsulate(kyber_pk, rsa_pk)
        with pytest.raises(ValueError):
            crypto_utils.hybrid_decapsulate(rsa_ct, kyber_encap, rsa_sk_wrong, kyber_sk)

    def test_hybrid_wrong_kyber_key_gives_different_secret(self):
        kyber_pk, kyber_sk = crypto_utils.generate_kem_keypair()
        _, kyber_sk_wrong = crypto_utils.generate_kem_keypair()
        rsa_pk, rsa_sk = crypto_utils.generate_rsa_keypair()

        rsa_ct, kyber_encap, combined_ss = crypto_utils.hybrid_encapsulate(kyber_pk, rsa_pk)
        wrong_ss = crypto_utils.hybrid_decapsulate(rsa_ct, kyber_encap, rsa_sk, kyber_sk_wrong)
        assert wrong_ss != combined_ss

    def test_hybrid_full_send_receive_pipeline(self):
        """Full hybrid pipeline: sign, hybrid-encap, encrypt, decrypt, verify."""
        sig_pk, sig_sk = crypto_utils.generate_sig_keypair()
        kyber_pk, kyber_sk = crypto_utils.generate_kem_keypair()
        rsa_pk, rsa_sk = crypto_utils.generate_rsa_keypair()

        plaintext = b"Subject: Hybrid Test\n\nHybrid encrypted body"
        signature = crypto_utils.sign(plaintext, sig_sk)
        payload = crypto_utils.build_payload(signature, plaintext)

        rsa_ct, kyber_encap, combined_ss = crypto_utils.hybrid_encapsulate(kyber_pk, rsa_pk)
        ct, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, combined_ss)

        recovered_ss = crypto_utils.hybrid_decapsulate(rsa_ct, kyber_encap, rsa_sk, kyber_sk)
        assert recovered_ss == combined_ss
        decrypted = crypto_utils.aes_gcm_decrypt(ct, recovered_ss, nonce, tag)
        sig_out, msg_out = crypto_utils.split_payload(decrypted)
        assert msg_out == plaintext
        assert crypto_utils.verify(msg_out, sig_out, sig_pk) is True


# ── Full Pipeline (Signed KEM-DEM) ──────────────────────────────────────────

class TestFullPipeline:
    def test_send_receive_roundtrip(self):
        sender_sig_pk, sender_sig_sk = crypto_utils.generate_sig_keypair()
        recv_kem_pk, recv_kem_sk = crypto_utils.generate_kem_keypair()

        plaintext = b"Subject: Hello\n\nBody text"
        signature = crypto_utils.sign(plaintext, sender_sig_sk)
        payload = crypto_utils.build_payload(signature, plaintext)
        encap, shared_secret = crypto_utils.kem_encapsulate(recv_kem_pk)
        ct, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, shared_secret)

        ss2 = crypto_utils.kem_decapsulate(encap, recv_kem_sk)
        assert ss2 == shared_secret
        decrypted_payload = crypto_utils.aes_gcm_decrypt(ct, ss2, nonce, tag)
        sig_out, msg_out = crypto_utils.split_payload(decrypted_payload)
        assert msg_out == plaintext
        assert crypto_utils.verify(msg_out, sig_out, sender_sig_pk) is True

    def test_tampered_ciphertext_detected(self):
        _, sender_sig_sk = crypto_utils.generate_sig_keypair()
        recv_kem_pk, recv_kem_sk = crypto_utils.generate_kem_keypair()

        plaintext = b"Confidential"
        sig = crypto_utils.sign(plaintext, sender_sig_sk)
        payload = crypto_utils.build_payload(sig, plaintext)
        encap, ss = crypto_utils.kem_encapsulate(recv_kem_pk)
        ct, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, ss)

        tampered_ct = bytearray(ct)
        tampered_ct[0] ^= 0xFF
        ss2 = crypto_utils.kem_decapsulate(encap, recv_kem_sk)
        with pytest.raises(ValueError):
            crypto_utils.aes_gcm_decrypt(bytes(tampered_ct), ss2, nonce, tag)

    def test_forged_signature_detected(self):
        sender_sig_pk, sender_sig_sk = crypto_utils.generate_sig_keypair()
        _, forger_sig_sk = crypto_utils.generate_sig_keypair()
        recv_kem_pk, recv_kem_sk = crypto_utils.generate_kem_keypair()

        plaintext = b"I am legitimate"
        forged_sig = crypto_utils.sign(plaintext, forger_sig_sk)
        payload = crypto_utils.build_payload(forged_sig, plaintext)
        encap, ss = crypto_utils.kem_encapsulate(recv_kem_pk)
        ct, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, ss)

        ss2 = crypto_utils.kem_decapsulate(encap, recv_kem_sk)
        decrypted_payload = crypto_utils.aes_gcm_decrypt(ct, ss2, nonce, tag)
        sig_out, msg_out = crypto_utils.split_payload(decrypted_payload)
        assert crypto_utils.verify(msg_out, sig_out, sender_sig_pk) is False


# ── Benchmarks ───────────────────────────────────────────────────────────────

class TestBenchmarks:
    def test_benchmarks_return_all_operations(self):
        results = crypto_utils.run_benchmarks(iterations=1)
        assert len(results) == 8
        ops = [r["operation"] for r in results]
        assert any("Keygen" in o and "Kyber" in o for o in ops)
        assert any("Encapsulate" in o for o in ops)
        assert any("Decapsulate" in o for o in ops)
        assert any("Sign" in o for o in ops)
        assert any("Verify" in o for o in ops)
        assert any("Encrypt" in o for o in ops)
        assert any("Decrypt" in o for o in ops)

    def test_benchmark_has_required_fields(self):
        results = crypto_utils.run_benchmarks(iterations=1)
        for r in results:
            assert "operation" in r
            assert "avg_ms" in r
            assert "size_bytes" in r
            assert isinstance(r["avg_ms"], (int, float))
