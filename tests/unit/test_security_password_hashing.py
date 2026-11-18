from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.security import hash_password, verify_password


def test_hash_password_creates_a_verifiable_bcrypt_hash():
    hashed_password = hash_password("correct-horse-battery-staple")

    assert hashed_password.startswith(("$2a$", "$2b$"))
    assert verify_password("correct-horse-battery-staple", hashed_password)
    assert not verify_password("incorrect-password", hashed_password)


def test_verify_password_accepts_existing_bcrypt_hashes():
    # Passlib stored standard bcrypt hashes; pwdlib must continue to verify them.
    legacy_hash = BcryptHasher(rounds=4).hash("existing-admin-password")

    assert verify_password("existing-admin-password", legacy_hash)
    assert not verify_password("wrong-password", legacy_hash)
