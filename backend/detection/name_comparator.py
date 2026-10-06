# =========================================================
# NAME COMPARISON
# =========================================================

def normalize_name(name):

    if not name:
        return ""

    return " ".join(
        name.upper().split()
    )


def compare_names(reference_name, submitted_name):

    if not reference_name:
        return {
            "score": 0.0,
            "match": False,
            "reason": "Reference name not detected"
        }

    if not submitted_name:
        return {
            "score": 0.0,
            "match": False,
            "reason": "Submitted name not detected"
        }

    reference = normalize_name(
        reference_name
    )

    submitted = normalize_name(
        submitted_name
    )

    # -----------------------------------------------------
    # EXACT MATCH
    # -----------------------------------------------------

    if reference == submitted:

        return {
            "score": 1.0,
            "match": True,
            "reason": "Names match"
        }

    # -----------------------------------------------------
    # DIFFERENT NAME
    # -----------------------------------------------------

    return {
        "score": 0.0,
        "match": False,
        "reason": "Names are different"
    }