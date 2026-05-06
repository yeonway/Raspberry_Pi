import base64
import getpass
import hashlib
import secrets


ITERATIONS = 260000
SALT_BYTES = 16


def make_hash(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )

    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("utf-8")

    return f"pbkdf2_sha256${ITERATIONS}${salt_b64}${digest_b64}"


def main():
    password = getpass.getpass("Dashboard password: ")
    password2 = getpass.getpass("Confirm password: ")

    if not password:
        print("ERROR: empty password is not allowed")
        return

    if password != password2:
        print("ERROR: password does not match")
        return

    print("\nDASHBOARD_PASSWORD_HASH=")
    print(make_hash(password))


if __name__ == "__main__":
    main()
