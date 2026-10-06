# =========================================================
# CERTIFICATE VERIFIER
# =========================================================

def compare_features(reference, submitted):
    """
    Compare reference certificate features
    with submitted certificate features.

    Returns similarity scores and final decision.
    """

    if not reference or not submitted:
        return {
            "signature_score": 0.0,
            "seal_score": 0.0,
            "overall_score": 0.0,
            "decision": "SUSPICIOUS"
        }

    # -----------------------------------------------------
    # SIGNATURE COMPARISON
    # -----------------------------------------------------

    ref_sig = reference.get("signature")
    sub_sig = submitted.get("signature")

    if ref_sig and sub_sig:

        signature_score = compare_signature(
            ref_sig,
            sub_sig
        )

    else:
        signature_score = 0.0

    # -----------------------------------------------------
    # SEAL COMPARISON
    # -----------------------------------------------------

    ref_seal = reference.get("seal")
    sub_seal = submitted.get("seal")

    if ref_seal and sub_seal:

        seal_score = compare_seal(
            ref_seal,
            sub_seal
        )

    else:
        seal_score = 0.0

    # -----------------------------------------------------
    # OVERALL SCORE
    # -----------------------------------------------------

    overall_score = (
        signature_score * 0.60
        + seal_score * 0.40
    )

    # -----------------------------------------------------
    # DECISION
    # -----------------------------------------------------

    if overall_score >= 0.70:
        decision = "GENUINE"

    elif overall_score >= 0.50:
        decision = "REVIEW"

    else:
        decision = "SUSPICIOUS"

    return {
        "signature_score": round(
            signature_score,
            4
        ),

        "seal_score": round(
            seal_score,
            4
        ),

        "overall_score": round(
            overall_score,
            4
        ),

        "decision": decision
    }


# =========================================================
# SIGNATURE COMPARISON
# =========================================================

def compare_signature(reference, submitted):

    scores = []

    # -----------------------------------------------------
    # ASPECT RATIO
    # -----------------------------------------------------

    ref_ratio = reference.get(
        "aspect_ratio",
        0
    )

    sub_ratio = submitted.get(
        "aspect_ratio",
        0
    )

    if ref_ratio > 0 and sub_ratio > 0:

        ratio_difference = abs(
            ref_ratio - sub_ratio
        )

        ratio_score = max(
            0.0,
            1.0 - (
                ratio_difference
                / ref_ratio
            )
        )

        scores.append(ratio_score)

    # -----------------------------------------------------
    # INK RATIO
    # -----------------------------------------------------

    ref_ink = reference.get(
        "ink_ratio",
        0
    )

    sub_ink = submitted.get(
        "ink_ratio",
        0
    )

    if ref_ink > 0 and sub_ink > 0:

        ink_difference = abs(
            ref_ink - sub_ink
        )

        ink_score = max(
            0.0,
            1.0 - (
                ink_difference
                / ref_ink
            )
        )

        scores.append(ink_score)

    # -----------------------------------------------------
    # EDGE RATIO
    # -----------------------------------------------------

    ref_edge = reference.get(
        "edge_ratio",
        0
    )

    sub_edge = submitted.get(
        "edge_ratio",
        0
    )

    if ref_edge > 0 and sub_edge > 0:

        edge_difference = abs(
            ref_edge - sub_edge
        )

        edge_score = max(
            0.0,
            1.0 - (
                edge_difference
                / ref_edge
            )
        )

        scores.append(edge_score)

    # -----------------------------------------------------
    # CONTOUR COUNT
    # -----------------------------------------------------

    ref_contours = reference.get(
        "contour_count",
        0
    )

    sub_contours = submitted.get(
        "contour_count",
        0
    )

    if ref_contours > 0:

        contour_difference = abs(
            ref_contours - sub_contours
        )

        contour_score = max(
            0.0,
            1.0 - (
                contour_difference
                / ref_contours
            )
        )

        scores.append(contour_score)

    # -----------------------------------------------------
    # FINAL SIGNATURE SCORE
    # -----------------------------------------------------

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


# =========================================================
# SEAL COMPARISON
# =========================================================

def compare_seal(reference, submitted):

    scores = []

    # -----------------------------------------------------
    # ASPECT RATIO
    # -----------------------------------------------------

    ref_ratio = reference.get(
        "aspect_ratio",
        0
    )

    sub_ratio = submitted.get(
        "aspect_ratio",
        0
    )

    if ref_ratio > 0 and sub_ratio > 0:

        difference = abs(
            ref_ratio - sub_ratio
        )

        score = max(
            0.0,
            1.0 - difference
        )

        scores.append(score)

    # -----------------------------------------------------
    # BLUE RATIO
    # -----------------------------------------------------

    ref_blue = reference.get(
        "blue_ratio",
        0
    )

    sub_blue = submitted.get(
        "blue_ratio",
        0
    )

    if ref_blue > 0 and sub_blue > 0:

        difference = abs(
            ref_blue - sub_blue
        )

        score = max(
            0.0,
            1.0 - (
                difference
                / ref_blue
            )
        )

        scores.append(score)

    # -----------------------------------------------------
    # CIRCULARITY
    # -----------------------------------------------------

    ref_circularity = reference.get(
        "circularity",
        0
    )

    sub_circularity = submitted.get(
        "circularity",
        0
    )

    if ref_circularity > 0:

        difference = abs(
            ref_circularity
            - sub_circularity
        )

        score = max(
            0.0,
            1.0 - (
                difference
                / ref_circularity
            )
        )

        scores.append(score)

    # -----------------------------------------------------
    # FINAL SEAL SCORE
    # -----------------------------------------------------

    if not scores:
        return 0.0

    return sum(scores) / len(scores)