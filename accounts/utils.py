import re


def normalize_phone(raw):
    """Turn 0712345678, +254712345678 or 254712345678 into 254712345678.

    M-Pesa (Daraja) expects the 254... format, so we store every phone
    number this way from day one.
    """
    digits = re.sub(r"\D", "", raw or "")

    if len(digits) == 10 and digits.startswith("0"):
        digits = "254" + digits[1:]
    elif len(digits) == 9 and digits[0] in "17":
        digits = "254" + digits

    if not re.fullmatch(r"254[17]\d{8}", digits):
        raise ValueError("Enter a valid Kenyan phone number, like 0712345678.")
    return digits
