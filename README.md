# CAPTCHApocalypse

Notes and Python code from the TryHackMe CAPTCHApocalypse room. This repository is a snapshot of the room solution, not a reusable login tool or an installable package. The write-up line inside `captcha.py` is part of that snapshot and is intentionally left in place.

The script shows the approach used in the room: fetch a CSRF token and CAPTCHA, read the image with Tesseract OCR, encrypt the login payload with the room's RSA public key, and inspect the encrypted response. The target URL and keys in the file are placeholders. The script is not meant to run unchanged against another service.

The interesting part of the exercise is how the application's CAPTCHA, session state, and client-side key handling fit together. The exact requests and byte formats are specific to this room.
