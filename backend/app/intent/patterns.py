"""Scam-intent patterns — English + Hindi (Devanagari) + romanized/code-mixed.

This is the seed of our India-first differentiator: real Indian phone scams
are code-mixed ("OTP batao", "turant paise bhejo"), which English-only tools
miss. Extend these lists with more languages (Kannada, Tamil, ...) later.
"""

INTENT_PATTERNS: dict[str, list[str]] = {
    "otp_request": [
        r"\botp\b",
        r"one[\s-]?time\s*password",
        r"verification\s*code",
        r"\bpin\b",
        r"ओटीपी",
        r"otp\s*(bata|batao|btao|do|send)",
        r"code\s*(bata|batao|do)",
    ],
    "money_request": [
        r"transfer",
        r"send\s*money",
        r"\bupi\b",
        r"account\s*number",
        r"bank\s*details",
        r"\bpaise?\b",
        r"पैसे",
        r"रुपये",
        r"paise?\s*(bhej|transfer|send)",
        r"(g[\s-]?pay|phonepe|paytm)",
        # regional Indian languages (romanized): money
        r"\bpanam\b",       # Tamil / Malayalam
        r"\bdabbulu\b",     # Telugu
        r"\bhana\b",        # Kannada
        r"\btaka\b",        # Bengali
        r"\brupaye?\b",
        r"\brupiya\b",      # Gujarati / Urdu
        r"\brupaya\b",      # Urdu
        r"\bkaasu\b",       # Tamil / Malayalam (colloquial)
    ],
    "urgency": [
        r"urgent",
        r"immediately",
        r"right\s*now",
        r"emergency",
        r"\bhurry\b",
        r"turant",
        r"तुरंत",
        r"जल्दी",
        r"\bjaldi\b",
        r"\babhi\b",
        # regional Indian languages (romanized): urgency / "quickly / now"
        r"\budane\b",       # Tamil
        r"\bventane\b",     # Telugu
        r"\bbegane\b",      # Kannada
        r"\bekhoni\b",      # Bengali
        r"\blavkar\b",      # Marathi
        r"\bfauran\b",      # Urdu
        r"\bpettennu\b",    # Malayalam
        r"\bchhet?i\b",     # Punjabi
    ],
    "authority_claim": [
        r"this\s*is\s*your\s*(bank|manager|officer)",
        r"\bpolice\b",
        r"income\s*tax",
        r"\bcbi\b",
        r"customs",
        r"bank\s*se\s*(bol|baat)",
        r"अधिकारी",
    ],
    "secrecy": [
        r"don'?t\s*tell",
        r"keep\s*(this\s*)?secret",
        r"confidential",
        r"kisi\s*ko\s*mat",
        r"किसी\s*को\s*मत",
        r"secret\s*rakh",
    ],
}
