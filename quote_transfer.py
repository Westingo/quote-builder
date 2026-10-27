"""Versioned, local-only transfer of editable Quote Builder data."""
import json
import quote_format
import formatting_profiles

FORMAT = "metro-quote-builder"
MAX_BYTES = 5 * 1024 * 1024


def validate_job(job):
    def check(value, kind, path):
        if not isinstance(value, kind):
            raise ValueError(f"Invalid quote: {path} has the wrong type.")

    def row(value, path):
        check(value, dict, path)
        if not any(k in value for k in ("text", "code", "amount_note")):
            raise ValueError(f"Invalid quote: {path} needs text or a code.")
        for key, val in value.items():
            if key == "format":
                quote_format.validate(val)
            elif key == "qty":
                if val is not None:
                    check(val, (str, int, float), path + "." + key)
            elif key in ("sub", "atqty", "leftnote", "deduct", "cost_per_gate"):
                check(val, bool, path + "." + key)
            elif key == "fills":
                strings(val, path + ".fills")
            else:
                check(val, str, path + "." + key)

    def strings(values, path):
        check(values, list, path)
        for value in values:
            check(value, str, path)

    check(job, dict, "job")
    formatting_profiles.validate(job.get("formatting_profile", "standard"))
    check(job.get("proposal"), dict, "proposal")
    for key, value in job["proposal"].items():
        if key == "tariff_notes":
            if value is not None:
                strings(value, "proposal.tariff_notes")
        else:
            check(value, str, "proposal field")
    if not job["proposal"].get("for", "").strip():
        raise ValueError("Customer (For:) is required.")
    strings(job.get("gate_summary", []), "gate_summary")
    if "summary_text" in job:
        check(job["summary_text"], str, "summary_text")
    for key in ("gates", "options", "notes", "warranties", "exclusions"):
        check(job.get(key, []), list, key)
    all_options = list(job.get("options", []))
    for gate in job.get("gates", []):
        check(gate, dict, "gate")
        quote_format.validate(gate.get("format", {}))
        check(gate.get("title", ""), str, "gate title")
        check(gate.get("lines", []), list, "gate lines")
        check(gate.get("options", []), list, "location options")
        all_options.extend(gate.get("options", []))
        for line in gate.get("lines", []):
            row(line, "gate line")
    for option in all_options:
        check(option, dict, "option")
        quote_format.validate(option.get("format", {}))
        for key in ("title", "text", "note", "kind"):
            if key in option:
                check(option[key], str, "option " + key)
        if "amount" in option:
            check(option["amount"], str, "option amount")
        for key in ("deduct", "cost_per_gate"):
            if key in option:
                check(option[key], bool, "option " + key)
        if "lines" in option:
            check(option["lines"], list, "option lines")
            for line in option["lines"]:
                row(line, "option line")
        if option.get("kind") == "block":
            strings(option.get("bullets"), "option bullets")
            check(option.get("priced"), list, "option prices")
            for price in option.get("priced", []):
                check(price, dict, "option price")
                check(price.get("label", ""), str, "price label")
                check(price.get("amount", ""), str, "price amount")
    for key in ("notes", "warranties", "exclusions"):
        for value in job.get(key, []):
            if not isinstance(value, str):
                row(value, key)
    if "options_title" in job:
        check(job["options_title"], str, "options_title")
    if job.get("total") is not None:
        check(job["total"], (str, int, float), "total")
    return {k: v for k, v in job.items() if k != "slug"}


def export_quote(job):
    job = validate_job(job)
    version = 2 if any(g.get("options") for g in job.get("gates", [])) else 1
    if job.get("formatting_profile", "standard") != "standard":
        version = 3
    payload = {"format": FORMAT, "version": version, "job": job}
    data = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("Quote file exceeds the 5 MB limit.")
    return data


def import_quote(data):
    if len(data) > MAX_BYTES:
        raise ValueError("Quote file exceeds the 5 MB limit.")
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Choose a .metroquote file created with Export quote.") from exc
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise ValueError("Choose a .metroquote file created with Export quote.")
    if type(payload.get("version")) is not int or payload["version"] not in (1, 2, 3):
        raise ValueError("This quote uses a newer format. Update Quote Builder and try again.")
    job = validate_job(payload.get("job"))
    # Also reject non-finite numbers accepted by Python's JSON reader.
    export_quote(job)
    return job
