# CAPTCHApocalypse

This is a small lab script I wrote while looking at a login flow that combined
CAPTCHA images with RSA-encrypted requests. It fetches the challenge image,
uses Tesseract for OCR, and reproduces the request format expected by the lab.

It is not a general CAPTCHA solver. The endpoint names and response format are
specific to the exercise I used it for. Run it only against a system you own or
have permission to test.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Tesseract also needs to be installed on the host system. Put the lab keys in
`keys/server-public.pem` and `keys/client-private.pem`; the `keys/` directory is
ignored by Git.

Set the target URL before running:

```bash
export CAPTCHA_BASE_URL="http://127.0.0.1"
python captcha.py
```

The wordlist defaults to `top100.txt`. Paths and the username can be changed
with `CAPTCHA_PASSWORD_FILE`, `CAPTCHA_SERVER_PUBLIC_KEY`,
`CAPTCHA_CLIENT_PRIVATE_KEY`, and `CAPTCHA_USERNAME`.
