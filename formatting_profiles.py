"""Explicit, per-quote layout selection; existing quotes remain standard."""
PROFILES = {"standard", "john"}


def validate(profile):
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError("Unknown formatting profile. Choose Metro standard or John.")
    return profile


def apply(document, profile):
    if validate(profile) == "john":
        import john_formatting
        john_formatting.apply(document)
