"""
Combined certificate forgery detection.

Certificate-specific detection:

C1:
    Student name + signatures + seal

C2:
    Student name + signatures + seal

C3:
    Student name + signatures + seal

C4:
    Student name + fixed signatures + seal

C5:
    Student name region + signatures + seal

C6:
    Student name region + signatures + seal

C7:
    Student name region + signatures + seal

C8:
    ONLY:
        - Seal
        - Register number

    IMPORTANT:
        - Student name is NOT checked.
        - Signatures are NOT checked.
        - ELA alone does NOT declare C8 forged.
        - If only seal/register number is changed,
          the result identifies that component.

C9:
    Student name + signatures + seal + register number

Exact SHA-256 mismatch alone does NOT decide forgery.
Structured comparison is the primary decision when a
trusted reference image is available. If structured comparison
succeeds and all configured regions match, the certificate is
considered genuine even when the uploaded file has a different
byte-level hash.
"""

import io
import os
import json
import re
from difflib import SequenceMatcher

import cv2
import numpy as np

from PIL import Image, ImageChops

from config import settings

try:
    import pytesseract
except ImportError:
    pytesseract = None


# =========================================================
# CNN MODEL
# =========================================================

_CNN_MODEL = None


# =========================================================
# CERTIFICATE-SPECIFIC STUDENT NAME REGIONS
# =========================================================

NAME_REGIONS = {

    "c1.jpeg": {
        "expected_name": "KHOT KALPESH MOHAN",
        "x": 165,
        "y": 160,
        "width": 125,
        "height": 30,
        "threshold": 0.45
    },

    "c2.jpeg": {
        "expected_name": "Mahindre Komal Surendra",
        "x": 154,
        "y": 195,
        "width": 173,
        "height": 22,
        "threshold": 0.45
    },

    "c3.jpeg": {
        "expected_name": "HEMANTH RAJ DEVARAJ",
        "x": 148,
        "y": 175,
        "width": 195,
        "height": 22,
        "threshold": 0.45
    },

    "c4.jpeg": {
        "expected_name": "Rekulabandha Pavan Kalyan Srinivasa Rao",
        "x": 75,
        "y": 227,
        "width": 335,
        "height": 25,
        "threshold": 0.45
    },

    "c5.jpeg": {
        "expected_name": None,
        "x": 370,
        "y": 275,
        "width": 460,
        "height": 90,
        "threshold": 0.45
    },

    "c6.jpeg": {
        "expected_name": None,
        "x": 105,
        "y": 570,
        "width": 250,
        "height": 50,
        "threshold": 0.45
    },

    "c7.jpeg": {
        "expected_name": None,
        "x": 150,
        "y": 190,
        "width": 250,
        "height": 55,
        "threshold": 0.45
    },

    # =====================================================
    # C8
    #
    # Name is intentionally NOT checked.
    # =====================================================

    "c8.jpeg": {
        "expected_name": None,
        "x": 150,
        "y": 190,
        "width": 250,
        "height": 55,
        "threshold": 0.45
    },

    "c9.jpeg": {
        "expected_name": None,
        "x": 150,
        "y": 190,
        "width": 250,
        "height": 55,
        "threshold": 0.45
    }
}


# =========================================================
# CERTIFICATE-SPECIFIC CHECK CONFIGURATION
# =========================================================

CERTIFICATE_CHECKS = {

    "c1.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": False
    },

    "c2.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": False
    },

    "c3.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": False
    },

    "c4.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": False
    },

    "c5.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": False
    },

    "c6.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": False
    },

    "c7.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": False
    },

    # =====================================================
    # C8 IMPORTANT
    #
    # ONLY SEAL + REGISTER NUMBER
    # =====================================================

    "c8.jpeg": {
        "name": False,
        "signature": False,
        "seal": True,
        "register_number": True
    },

    "c9.jpeg": {
        "name": True,
        "signature": True,
        "seal": True,
        "register_number": True
    }
}


# =========================================================
# GET CERTIFICATE CHECK CONFIG
# =========================================================

def _get_certificate_checks(reference_path):

    if not reference_path:

        return {
            "name": True,
            "signature": True,
            "seal": True,
            "register_number": False
        }

    filename = os.path.basename(
        reference_path
    ).lower()

    return CERTIFICATE_CHECKS.get(
        filename,
        {
            "name": True,
            "signature": True,
            "seal": True,
            "register_number": False
        }
    )


# =========================================================
# GET EXPECTED CERTIFICATE INFORMATION
# =========================================================

def _get_certificate_info(reference_path):

    if not reference_path:
        return {}

    config_path = os.path.join(
        os.path.dirname(__file__),
        "reference_data",
        "certificates",
        "certificate_references.json"
    )

    if not os.path.exists(config_path):
        return {}

    try:

        with open(
            config_path,
            "r",
            encoding="utf-8"
        ) as f:

            references = json.load(f)

    except Exception:

        return {}

    reference_filename = os.path.basename(
        reference_path
    ).lower()

    for certificate_id, certificate in references.items():

        image_name = str(
            certificate.get(
                "reference_image",
                ""
            )
        ).lower()

        if image_name == reference_filename:

            result = dict(certificate)

            result["certificate_id"] = (
                certificate_id
            )

            return result

    return {}


# =========================================================
# GET NAME REGION
# =========================================================

def _get_name_region(reference_path):

    reference_filename = os.path.basename(
        reference_path
    ).lower()

    region = NAME_REGIONS.get(
        reference_filename
    )

    if region:
        return dict(region)

    return {
        "x": 150,
        "y": 190,
        "width": 220,
        "height": 50,
        "threshold": 0.45,
        "expected_name": None
    }


# =========================================================
# ELA
# =========================================================

def _ela_image(
    pil_image: Image.Image,
    quality: int = 90
) -> Image.Image:

    pil_image = pil_image.convert("RGB")

    buffer = io.BytesIO()

    pil_image.save(
        buffer,
        "JPEG",
        quality=quality
    )

    buffer.seek(0)

    resaved = Image.open(
        buffer
    )

    ela = ImageChops.difference(
        pil_image,
        resaved
    )

    extrema = ela.getextrema()

    max_diff = max(
        [ex[1] for ex in extrema]
    ) or 1

    scale = 255.0 / max_diff

    ela = Image.eval(
        ela,
        lambda px: min(
            255,
            int(px * scale)
        )
    )

    return ela


# =========================================================
# ELA FEATURES
# =========================================================

def _extract_features(
    ela_image: Image.Image
) -> dict:

    arr = np.array(
        ela_image.convert("L")
    ).astype(np.float32)

    mean_val = float(
        arr.mean()
    )

    std_val = float(
        arr.std()
    )

    max_val = float(
        arr.max()
    )

    high_error_ratio = (
        float(
            (arr > 40).sum()
        )
        / arr.size
    )

    edges = cv2.Canny(
        arr.astype(np.uint8),
        50,
        150
    )

    edge_density = (
        float(
            (edges > 0).sum()
        )
        / edges.size
    )

    return {

        "mean": mean_val,

        "std": std_val,

        "max": max_val,

        "high_error_ratio":
            high_error_ratio,

        "edge_density":
            edge_density
    }


# =========================================================
# ELA SCORE
# =========================================================

def _score_from_features(
    features: dict
) -> float:

    score = (

        0.35 * min(
            features["high_error_ratio"] * 8,
            1.0
        )

        + 0.25 * min(
            features["edge_density"] * 5,
            1.0
        )

        + 0.20 * min(
            features["std"] / 60.0,
            1.0
        )

        + 0.20 * min(
            features["max"] / 255.0,
            1.0
        )
    )

    return float(
        min(
            max(
                score,
                0.0
            ),
            1.0
        )
    )


# =========================================================
# CNN
# =========================================================

def load_cnn_model(
    model_path: str = "models/forgery_cnn.h5"
):

    global _CNN_MODEL

    if not os.path.exists(
        model_path
    ):

        _CNN_MODEL = None

        return None

    try:

        from tensorflow.keras.models import (
            load_model
        )

        _CNN_MODEL = load_model(
            model_path
        )

        return _CNN_MODEL

    except ImportError:

        _CNN_MODEL = None

        return None

    except Exception:

        _CNN_MODEL = None

        return None


def predict_with_cnn(
    pil_image: Image.Image
):

    if _CNN_MODEL is None:

        return None

    try:

        img = (
            pil_image
            .convert("RGB")
            .resize((224, 224))
        )

        arr = (
            np.array(img)
            .astype(np.float32)
            / 255.0
        )

        arr = np.expand_dims(
            arr,
            axis=0
        )

        prob = float(
            _CNN_MODEL.predict(
                arr,
                verbose=0
            )[0][0]
        )

        return prob

    except Exception:

        return None


# =========================================================
# IMAGE ALIGNMENT
# =========================================================

def _align_images(
    reference_path,
    uploaded_bytes
):

    reference = cv2.imread(
        reference_path
    )

    uploaded_array = np.frombuffer(
        uploaded_bytes,
        dtype=np.uint8
    )

    uploaded = cv2.imdecode(
        uploaded_array,
        cv2.IMREAD_COLOR
    )

    if reference is None:

        raise FileNotFoundError(
            reference_path
        )

    if uploaded is None:

        raise ValueError(
            "Could not decode uploaded certificate image."
        )

    reference_gray = cv2.cvtColor(
        reference,
        cv2.COLOR_BGR2GRAY
    )

    uploaded_gray = cv2.cvtColor(
        uploaded,
        cv2.COLOR_BGR2GRAY
    )

    orb = cv2.ORB_create(
        nfeatures=5000
    )

    keypoints1, descriptors1 = (
        orb.detectAndCompute(
            reference_gray,
            None
        )
    )

    keypoints2, descriptors2 = (
        orb.detectAndCompute(
            uploaded_gray,
            None
        )
    )

    if (
        descriptors1 is None
        or descriptors2 is None
    ):

        raise ValueError(
            "Not enough image features."
        )

    matcher = cv2.BFMatcher(
        cv2.NORM_HAMMING,
        crossCheck=True
    )

    matches = matcher.match(
        descriptors1,
        descriptors2
    )

    matches = sorted(
        matches,
        key=lambda m: m.distance
    )

    good_matches = matches[:100]

    if len(good_matches) < 10:

        raise ValueError(
            "Not enough matching certificate features."
        )

    reference_points = np.float32([
        keypoints1[m.queryIdx].pt
        for m in good_matches
    ]).reshape(
        -1,
        1,
        2
    )

    uploaded_points = np.float32([
        keypoints2[m.trainIdx].pt
        for m in good_matches
    ]).reshape(
        -1,
        1,
        2
    )

    matrix, mask = cv2.findHomography(
        uploaded_points,
        reference_points,
        cv2.RANSAC,
        5.0
    )

    if matrix is None:

        raise ValueError(
            "Could not align certificate."
        )

    height, width = reference.shape[:2]

    aligned = cv2.warpPerspective(
        uploaded,
        matrix,
        (width, height)
    )

    return reference, aligned


# =========================================================
# AUTOMATIC NAME-REGION DISCOVERY
# =========================================================

def _normalize_name_text(text):
    if not text:
        return ""
    text = str(text).upper()
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _find_name_region_automatically(reference_path, expected_name):
    """Locate the trusted student's name using OCR bounding boxes.

    This is used only for certificate templates that do not have a
    hard-coded NAME_REGIONS entry. Existing C1-C9 coordinates remain
    unchanged.
    """
    if pytesseract is None or not expected_name:
        return None

    image = cv2.imread(reference_path)
    if image is None:
        return None

    target = _normalize_name_text(expected_name)
    target_tokens = target.split()
    if not target_tokens:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variants = [
        gray,
        cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1],
    ]

    best = None

    for variant in variants:
        try:
            data = pytesseract.image_to_data(
                variant,
                config="--oem 3 --psm 11",
                output_type=pytesseract.Output.DICT,
            )
        except Exception:
            continue

        words = []
        count = len(data.get("text", []))
        for i in range(count):
            raw = _normalize_name_text(data["text"][i])
            if not raw:
                continue
            try:
                conf = float(data.get("conf", [0] * count)[i])
            except (TypeError, ValueError):
                conf = 0.0
            if conf < 15:
                continue
            words.append({
                "text": raw,
                "x": int(data["left"][i]),
                "y": int(data["top"][i]),
                "w": int(data["width"][i]),
                "h": int(data["height"][i]),
                "conf": conf,
                "block": data.get("block_num", [0] * count)[i],
                "line": data.get("line_num", [0] * count)[i],
            })

        if not words:
            continue

        # Try consecutive OCR words first.
        for i in range(len(words)):
            for span in range(1, min(len(target_tokens) + 3, 7)):
                group = words[i:i + span]
                if not group:
                    continue

                # Prefer words on the same OCR line/block.
                if len({(w["block"], w["line"]) for w in group}) > 1:
                    continue

                text = " ".join(w["text"] for w in group)
                similarity = SequenceMatcher(None, text, target).ratio()
                token_hits = sum(
                    1 for token in target_tokens
                    if any(
                        SequenceMatcher(None, token, w["text"]).ratio() >= 0.72
                        for w in group
                    )
                )
                token_score = token_hits / max(1, len(target_tokens))
                score = 0.65 * similarity + 0.35 * token_score

                if best is None or score > best["score"]:
                    x1 = min(w["x"] for w in group)
                    y1 = min(w["y"] for w in group)
                    x2 = max(w["x"] + w["w"] for w in group)
                    y2 = max(w["y"] + w["h"] for w in group)
                    best = {
                        "score": score,
                        "x": x1,
                        "y": y1,
                        "width": x2 - x1,
                        "height": y2 - y1,
                    }

    if best is None or best["score"] < 0.62:
        return None

    # Add a small margin so anti-aliased characters are fully included.
    image_h, image_w = image.shape[:2]
    margin_x = max(8, int(best["width"] * 0.12))
    margin_y = max(6, int(best["height"] * 0.45))
    x1 = max(0, best["x"] - margin_x)
    y1 = max(0, best["y"] - margin_y)
    x2 = min(image_w, best["x"] + best["width"] + margin_x)
    y2 = min(image_h, best["y"] + best["height"] + margin_y)

    return {
        "x": x1,
        "y": y1,
        "width": max(1, x2 - x1),
        "height": max(1, y2 - y1),
        "threshold": 0.45,
        "detection_method": "OCR automatic name discovery",
        "detector_score": round(float(best["score"]), 4),
    }


# =========================================================
# NAME COMPARISON
# =========================================================

def _compare_name(
    reference_path,
    aligned_image
):
    from detection.name_region_comparator import (
        compare_name_region
    )

    temp_path = os.path.join(
        os.path.dirname(__file__),
        "reference_data",
        "certificates",
        "_api_aligned_name_temp.png"
    )

    cv2.imwrite(
        temp_path,
        aligned_image
    )

    try:
        reference_filename = os.path.basename(
            reference_path
        ).lower()

        config = NAME_REGIONS.get(
            reference_filename
        )

        # Existing C1-C9 behavior: use the proven fixed regions.
        if config:
            result = compare_name_region(
                reference_path,
                temp_path,
                x=config["x"],
                y=config["y"],
                width=config["width"],
                height=config["height"],
                expected_name=config.get("expected_name"),
                threshold=config.get("threshold", 0.45)
            )
            result["name_region"] = {
                "x": config["x"],
                "y": config["y"],
                "width": config["width"],
                "height": config["height"],
                "detection_method": "certificate-specific configured region"
            }
            return result

        # New/dynamic certificates: recover expected name from the
        # trusted reference metadata saved during issuance.
        certificate_info = _get_certificate_info(
            reference_path
        )
        expected_name = None
        if certificate_info:
            expected_name = certificate_info.get(
                "student_name"
            )

        auto_region = _find_name_region_automatically(
            reference_path,
            expected_name
        )

        if auto_region:
            result = compare_name_region(
                reference_path,
                temp_path,
                x=auto_region["x"],
                y=auto_region["y"],
                width=auto_region["width"],
                height=auto_region["height"],
                expected_name=expected_name,
                threshold=auto_region.get("threshold", 0.45)
            )
            result["name_region"] = auto_region
            result["decision_reason"] = (
                "Student name region was located automatically from "
                "the trusted reference using OCR."
            )
            return result

        # Safe fallback for an unusual template where OCR cannot locate
        # the expected name. Keep the existing generic behavior rather
        # than making a stronger claim without evidence.
        result = compare_name_region(
            reference_path,
            temp_path,
            x=150,
            y=190,
            width=220,
            height=50,
            expected_name=expected_name,
            threshold=0.45
        )
        result["name_region"] = {
            "x": 150,
            "y": 190,
            "width": 220,
            "height": 50,
            "detection_method": "generic fallback"
        }
        result["ocr_warning"] = (
            "Automatic name-region discovery could not locate the "
            "expected name; generic fallback region was used."
        )
        return result

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# =========================================================
# SIGNATURE COMPARISON
# =========================================================

def _compare_signatures_automatic(
    reference_path,
    aligned_image
):

    from detection.signature_detector import (
        compare_signature_region
    )

    reference_filename = os.path.basename(
        reference_path
    ).lower()

    temp_path = os.path.join(
        os.path.dirname(__file__),
        "reference_data",
        "certificates",
        "_api_auto_signature_temp.png"
    )

    cv2.imwrite(
        temp_path,
        aligned_image
    )

    try:

        # =================================================
        # C4 FIXED SIGNATURE REGIONS
        # =================================================

        if reference_filename == "c4.jpeg":

            signature_regions = [

                {
                    "x": 90,
                    "y": 495,
                    "width": 110,
                    "height": 55
                },

                {
                    "x": 315,
                    "y": 495,
                    "width": 95,
                    "height": 55
                }
            ]

        else:

            from detection.signature_region_detector import (
                detect_signatures
            )

            reference = cv2.imread(
                reference_path
            )

            if reference is None:

                raise FileNotFoundError(
                    reference_path
                )

            signature_regions = detect_signatures(
                reference
            )

        if not signature_regions:

            return {

                "status":
                    "NO_SIGNATURES_DETECTED",

                "count":
                    0,

                "tampered_count":
                    0,

                "tampered_signatures":
                    [],

                "signatures":
                    []
            }

        results = []

        for index, region in enumerate(
            signature_regions,
            1
        ):

            result = compare_signature_region(

                reference_path,

                temp_path,

                region,

                f"Signature {index}"
            )

            result["region"] = {

                "x": region["x"],

                "y": region["y"],

                "width": region["width"],

                "height": region["height"]
            }

            results.append(
                result
            )

        tampered_signatures = []

        for index, result in enumerate(
            results,
            1
        ):

            if (
                result.get("status")
                == "TAMPERED"
            ):

                tampered_signatures.append(
                    index
                )

        status = (
            "TAMPERED"
            if tampered_signatures
            else "MATCH"
        )

        return {

            "status":
                status,

            "count":
                len(results),

            "tampered_count":
                len(tampered_signatures),

            "tampered_signatures":
                tampered_signatures,

            "signatures":
                results
        }

    finally:

        if os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )


# =========================================================
# SEAL COMPARISON
# =========================================================

def _compare_seal(
    reference_path,
    aligned_image
):

    from detection.seal_detector import (
        compare_seal
    )

    from detection.region_detector import (
        detect_seal_candidates
    )

    temp_path = os.path.join(
        os.path.dirname(__file__),
        "reference_data",
        "certificates",
        "_api_aligned_seal_temp.png"
    )

    cv2.imwrite(
        temp_path,
        aligned_image
    )

    try:

        reference_image = cv2.imread(
            reference_path
        )

        if reference_image is None:

            raise FileNotFoundError(
                reference_path
            )

        candidates = (
            detect_seal_candidates(
                reference_image
            )
        )

        if not candidates:

            return {

                "status":
                    "ERROR",

                "error":
                    "Automatic seal detection "
                    "could not find a trusted seal."
            }

        seal = candidates[0]

        x = seal["x"]
        y = seal["y"]
        width = seal["width"]
        height = seal["height"]

        result = compare_seal(

            reference_path,

            temp_path,

            x=x,
            y=y,
            width=width,
            height=height
        )

        result["region"] = (
            "Automatic Seal"
        )

        result["detected_region"] = {

            "x": x,

            "y": y,

            "width": width,

            "height": height
        }

        result["detector_score"] = (
            seal.get("score")
        )

        return result

    finally:

        if os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )


# =========================================================
# REGISTER NUMBER COMPARISON
# =========================================================

# =========================================================
# REGISTER NUMBER COMPARISON
# =========================================================

def _compare_register_number(
    reference_path,
    aligned_image
):

    from detection.register_number_comparator import (
        compare_register_number
    )

    temp_path = os.path.join(
        os.path.dirname(__file__),
        "reference_data",
        "certificates",
        "_api_aligned_register_temp.png"
    )

    cv2.imwrite(
        temp_path,
        aligned_image
    )

    try:

        reference_filename = os.path.basename(
            reference_path
        ).lower()

        # =================================================
        # C8 REGISTER NUMBER
        #
        # Location:
        # TOP-LEFT of certificate
        #
        # Trusted C8:
        # 204163090012
        #
        # T8:
        # 204163090011
        # =================================================

        if reference_filename == "c8.jpeg":

            result = compare_register_number(

                reference_path,

                temp_path,

                x=130,
                y=80,
                width=280,
                height=70
            )

            result["region"] = "Register Number"

            result["detected_region"] = {

                "x": 130,

                "y": 80,

                "width": 280,

                "height": 70
            }

            return result

        # =================================================
        # C9 REGISTER NUMBER
        # =================================================

        if reference_filename == "c9.jpeg":

            result = compare_register_number(

                reference_path,

                temp_path,

                x=735,
                y=1265,
                width=190,
                height=45
            )

            result["region"] = "Register Number"

            result["detected_region"] = {

                "x": 170,

                "y": 425,

                "width": 215,

                "height": 30
            }

            return result

        # =================================================
        # OTHER CERTIFICATES
        # =================================================

        return {

            "status": "NOT_CHECKED",

            "reason":
                "Register number comparison is not "
                "configured for this certificate."
        }

    finally:

        if os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )

# =========================================================
# STRUCTURED TAMPER ANALYSIS
# =========================================================

def _analyze_structured_tampering(
    name_result,
    signature_result,
    seal_result,
    register_number_result
):

    tampered_components = []

    tampered_signature_numbers = []

    # =====================================================
    # STUDENT NAME
    # =====================================================

    if isinstance(
        name_result,
        dict
    ):

        if (
            name_result.get(
                "status"
            )
            == "TAMPERED"
        ):

            tampered_components.append(
                "student_name"
            )

    # =====================================================
    # SIGNATURE
    # =====================================================

    if isinstance(
        signature_result,
        dict
    ):

        signatures = (
            signature_result.get(
                "signatures",
                []
            )
        )

        if isinstance(
            signatures,
            list
        ):

            for index, signature in enumerate(
                signatures,
                1
            ):

                if not isinstance(
                    signature,
                    dict
                ):

                    continue

                if (
                    signature.get(
                        "status"
                    )
                    == "TAMPERED"
                ):

                    tampered_signature_numbers.append(
                        index
                    )

        if tampered_signature_numbers:

            tampered_components.append(
                "signature"
            )

    # =====================================================
    # SEAL
    # =====================================================

    if isinstance(
        seal_result,
        dict
    ):

        if (
            seal_result.get(
                "status"
            )
            == "TAMPERED"
        ):

            tampered_components.append(
                "seal"
            )

    # =====================================================
    # REGISTER NUMBER
    # =====================================================

    if isinstance(
        register_number_result,
        dict
    ):

        if (
            register_number_result.get(
                "status"
            )
            == "TAMPERED"
        ):

            tampered_components.append(
                "register_number"
            )

    # =====================================================
    # FINAL STRUCTURED DECISION
    # =====================================================

    structured_tampered = (
        len(tampered_components) > 0
    )

    # =====================================================
    # HUMAN READABLE REASON
    # =====================================================

    if structured_comparison_available and structured_tampered:

        verification_reason = (
            structured_analysis[
                "reason"
            ]
        )

    elif structured_comparison_available:

        if reference_filename == "c8.jpeg":

            verification_reason = (
                "C8 certificate content verified against the trusted "
                "reference. Seal and register number match. Student "
                "name and signatures are not checked for C8. A different "
                "file hash does not by itself indicate forgery."
            )

        else:

            verification_reason = (
                "Certificate content and all configured monitored "
                "regions match the trusted reference. No structured "
                "tampering was detected. A different SHA-256 hash does "
                "not by itself indicate forgery."
            )

    else:

        verification_reason = (
            "Structured comparison could not be completed. "
            "The result is based on image analysis only."
        )

    # =====================================================
    # SPECIAL C4 MESSAGE
    # =====================================================

    if (
        reference_filename == "c4.jpeg"
        and structured_analysis[
            "tampered_signature_numbers"
        ]
    ):

        signature_numbers = (
            structured_analysis[
                "tampered_signature_numbers"
            ]
        )

        signature_text = ", ".join(
            [
                f"Signature {number}"
                for number in
                signature_numbers
            ]
        )

        verification_reason = (
            f"Certificate is likely forged because "
            f"{signature_text} does not match the "
            f"trusted reference. Student name and "
            f"other checked certificate elements "
            f"remain consistent."
        )

    # =====================================================
    # RESULT
    # =====================================================

    return {

        "verdict":
            verdict,

        "forgery_score":
            round(
                float(final_score),
                4
            ),

        "heuristic_score":
            round(
                float(heuristic_score),
                4
            ),

        "image_score":
            round(
                float(image_score),
                4
            ),

        "structured_score":
            round(
                float(structured_score),
                4
            ),

        "cnn_score":
            cnn_score,

        "features": {

            k:
                round(
                    float(v),
                    4
                )

            for k, v in features.items()
        },

        "threshold":
            settings.FORGERY_SCORE_THRESHOLD,

        "reference_used":
            reference_path,

        "certificate_checks":
            checks,

        "alignment":
            alignment_result,

        "student_name":
            name_result,

        "signature":
            signature_result,

        "seal":
            seal_result,

        "register_number":
            register_number_result,

        "structured_tampering":
            structured_tampered,

        "structured_comparison_available":
            structured_comparison_available,

        "tampered_components":
            structured_analysis[
                "components"
            ],

        "tampered_signature_numbers":
            structured_analysis[
                "tampered_signature_numbers"
            ],

        "verification_reason":
            verification_reason
    }