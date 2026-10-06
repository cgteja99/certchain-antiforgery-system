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

import cv2
import numpy as np

from PIL import Image, ImageChops

from config import settings


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
        "register_number": True
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
            "register_number": True
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
# NAME COMPARISON
# =========================================================



def _compare_name(reference_path, aligned_image):

    from detection.name_region_comparator import compare_name_region

    temp_path = os.path.join(
        os.path.dirname(__file__),
        "reference_data",
        "certificates",
        "_api_aligned_name_temp.png"
    )

    cv2.imwrite(temp_path, aligned_image)

    try:
        reference_filename = os.path.basename(reference_path).lower()

        # Keep the existing C1-C9 fixed-region behavior unchanged.
        config = NAME_REGIONS.get(reference_filename)

        if config:
            expected_name = config.get("expected_name")

            result = compare_name_region(
                reference_path,
                temp_path,
                x=config["x"],
                y=config["y"],
                width=config["width"],
                height=config["height"],
                expected_name=expected_name,
                threshold=config.get("threshold", 0.45)
            )

            result["name_region"] = {
                "x": config["x"],
                "y": config["y"],
                "width": config["width"],
                "height": config["height"]
            }

            if expected_name is None:
                if (
                    result.get("similarity", 0.0) >= 0.90
                    and result.get("ink_difference", 1.0) <= 0.10
                    and result.get("edge_difference", 1.0) <= 0.10
                ):
                    result["status"] = "MATCH"
                    result["tamper_score"] = 0.0
                else:
                    result["status"] = "TAMPERED"

            return result

        # Dynamic certificate: obtain the trusted name from metadata.
        certificate_info = _get_certificate_info(reference_path)

        expected_name = None
        if certificate_info:
            expected_name = certificate_info.get("student_name")

        if not expected_name:
            return {
                "status": "ERROR",
                "error": "Student name is not available in trusted metadata."
            }

        # Automatically locate the trusted name with OCR.
        try:
            import re
            import pytesseract
            from pytesseract import Output
            from difflib import SequenceMatcher

            def norm(value):
                value = str(value or "").upper()
                value = re.sub(r"[^A-Z0-9 ]+", " ", value)
                return " ".join(value.split())

            expected = norm(expected_name)
            expected_tokens = expected.split()

            reference_image = cv2.imread(reference_path)

            if reference_image is None:
                raise ValueError(
                    "Trusted reference image could not be loaded."
                )

            gray = cv2.cvtColor(
                reference_image,
                cv2.COLOR_BGR2GRAY
            )

            _, otsu = cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            best = None

            for image in (
                reference_image,
                gray,
                otsu
            ):
                data = pytesseract.image_to_data(
                    image,
                    config="--oem 3 --psm 11",
                    output_type=Output.DICT
                )

                words = []

                for i, raw_word in enumerate(
                    data.get("text", [])
                ):
                    word = norm(raw_word)

                    if not word:
                        continue

                    try:
                        x = int(data["left"][i])
                        y = int(data["top"][i])
                        w = int(data["width"][i])
                        h = int(data["height"][i])
                    except Exception:
                        continue

                    words.append({
                        "text": word,
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h
                    })

                for i in range(len(words)):
                    max_count = min(
                        len(expected_tokens) + 2,
                        len(words) - i
                    )

                    for count in range(
                        1,
                        max_count + 1
                    ):
                        group = words[i:i + count]

                        if (
                            max(item["y"] for item in group)
                            - min(item["y"] for item in group)
                        ) > 45:
                            continue

                        group_text = " ".join(
                            item["text"]
                            for item in group
                        )

                        similarity = SequenceMatcher(
                            None,
                            expected,
                            group_text
                        ).ratio()

                        token_hits = sum(
                            1
                            for token in expected_tokens
                            if token in group_text
                        )

                        token_score = (
                            token_hits /
                            max(1, len(expected_tokens))
                        )

                        score = (
                            similarity * 0.65
                            + token_score * 0.35
                        )

                        if (
                            best is None
                            or score > best["score"]
                        ):
                            best = {
                                "score": score,
                                "words": group
                            }

            if best is None or best["score"] < 0.55:
                raise ValueError(
                    "OCR could not automatically locate "
                    "the trusted student name."
                )

            group = best["words"]

            x1 = min(item["x"] for item in group)
            y1 = min(item["y"] for item in group)
            x2 = max(
                item["x"] + item["w"]
                for item in group
            )
            y2 = max(
                item["y"] + item["h"]
                for item in group
            )

            margin_x = max(
                8,
                int((x2 - x1) * 0.12)
            )

            margin_y = max(
                6,
                int((y2 - y1) * 0.30)
            )

            image_h, image_w = reference_image.shape[:2]

            x1 = max(
                0,
                x1 - margin_x
            )
            y1 = max(
                0,
                y1 - margin_y
            )
            x2 = min(
                image_w,
                x2 + margin_x
            )
            y2 = min(
                image_h,
                y2 + margin_y
            )

            region = {
                "x": int(x1),
                "y": int(y1),
                "width": int(max(1, x2 - x1)),
                "height": int(max(1, y2 - y1))
            }

            result = compare_name_region(
                reference_path,
                temp_path,
                x=region["x"],
                y=region["y"],
                width=region["width"],
                height=region["height"],
                expected_name=expected_name,
                threshold=0.45
            )

            result["name_region"] = region
            result["expected_name"] = expected_name
            result["detection_method"] = (
                "OCR automatic name discovery"
            )
            result["detector_score"] = round(
                float(best["score"]),
                4
            )

            result["decision_reason"] = (
                "Student name region was automatically "
                "located from the trusted reference using OCR "
                "and compared with the uploaded certificate."
            )

            return result

        except Exception as auto_error:
            return {
                "status": "ERROR",
                "error": str(auto_error),
                "expected_name": expected_name,
                "detection_method": (
                    "OCR automatic name discovery"
                )
            }

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
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
    aligned_image,
    certificate_id=None
):
    """
    Compare register number.

    Project convention:
        Certificate ID == Register Number

    Existing C3/C8/C9 coordinate checks are preserved.
    Dynamic certificates use certificate_id from trusted metadata
    and OCR to locate it automatically in the trusted reference.
    """

    from detection.register_number_comparator import (
        compare_register_number
    )

    temp_path = os.path.join(
        os.path.dirname(__file__),
        "reference_data",
        "certificates",
        "_api_aligned_register_temp.png"
    )

    cv2.imwrite(temp_path, aligned_image)

    try:
        reference_filename = os.path.basename(
            reference_path
        ).lower()

        # C3 -- existing check preserved
        if reference_filename == "c3.jpeg":
            result = compare_register_number(
                reference_path, temp_path,
                x=170, y=425, width=215, height=30
            )
            result["region"] = "Register Number"
            result["detected_region"] = {
                "x": 170, "y": 425, "width": 215, "height": 30
            }
            return result

        # C8 -- existing check preserved
        if reference_filename == "c8.jpeg":
            result = compare_register_number(
                reference_path, temp_path,
                x=130, y=80, width=280, height=70
            )
            result["region"] = "Register Number"
            result["detected_region"] = {
                "x": 130, "y": 80, "width": 280, "height": 70
            }
            return result

        # C9 -- existing check preserved
        if reference_filename == "c9.jpeg":
            result = compare_register_number(
                reference_path, temp_path,
                x=735, y=1265, width=190, height=45
            )
            result["region"] = "Register Number"
            result["detected_region"] = {
                "x": 170, "y": 425, "width": 215, "height": 30
            }
            return result

        # Dynamic certificates:
        # project convention is Certificate ID == Register Number.
        try:
            info = _get_certificate_info(reference_path)
        except Exception:
            info = None

        expected_register = certificate_id
        
        if not expected_register:
            return {
                "status": "NOT_CHECKED",
                "reason":
                    "Register number could not be determined "
                    "from trusted certificate metadata."
            }

        expected_register = str(expected_register).strip()

        try:
            import re
            import pytesseract
            from difflib import SequenceMatcher

            reference_image = cv2.imread(reference_path)
            if reference_image is None:
                raise ValueError(
                    "Trusted reference image could not be read."
                )

            gray = cv2.cvtColor(
                reference_image, cv2.COLOR_BGR2GRAY
            )

            _, binary = cv2.threshold(
                gray, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            candidates = []

            for image in (reference_image, gray, binary):
                for config in (
                    "--oem 3 --psm 11",
                    "--oem 3 --psm 6"
                ):
                    data = pytesseract.image_to_data(
                        image,
                        config=config,
                        output_type=pytesseract.Output.DICT
                    )

                    for i, raw_word in enumerate(
                        data.get("text", [])
                    ):
                        word = str(raw_word).strip()
                        if not word:
                            continue

                        try:
                            confidence = float(data["conf"][i])
                        except Exception:
                            confidence = 0.0

                        try:
                            x = int(data["left"][i])
                            y = int(data["top"][i])
                            w = int(data["width"][i])
                            h = int(data["height"][i])
                        except Exception:
                            continue

                        candidates.append({
                            "text": word,
                            "confidence": confidence,
                            "x": x, "y": y, "w": w, "h": h
                        })

            def normalize(value):
                return re.sub(
                    r"[^A-Za-z0-9]",
                    "",
                    str(value)
                ).upper()

            expected_norm = normalize(expected_register)
            best = None
            best_score = 0.0

            for item in candidates:
                word_norm = normalize(item["text"])
                if not word_norm:
                    continue

                ratio = SequenceMatcher(
                    None, expected_norm, word_norm
                ).ratio()

                if (
                    expected_norm in word_norm
                    or word_norm in expected_norm
                ):
                    ratio = max(ratio, 0.90)

                score = ratio + (
                    max(0.0, min(item["confidence"], 100.0))
                    / 1000.0
                )

                if score > best_score:
                    best_score = score
                    best = item

            ordered = sorted(
                candidates,
                key=lambda item: (item["y"], item["x"])
            )

            for i, first in enumerate(ordered):
                group = [first]

                for nxt in ordered[i + 1:]:
                    if abs(nxt["y"] - first["y"]) <= max(
                        20, int(first["h"] * 0.8)
                    ):
                        if nxt["x"] <= first["x"] + first["w"] + 100:
                            group.append(nxt)

                    if len(group) >= 5:
                        break

                if len(group) <= 1:
                    continue

                group = sorted(group, key=lambda item: item["x"])
                combined = "".join(
                    normalize(item["text"]) for item in group
                )

                ratio = SequenceMatcher(
                    None, expected_norm, combined
                ).ratio()

                if (
                    expected_norm in combined
                    or combined in expected_norm
                ):
                    ratio = max(ratio, 0.90)

                if ratio > best_score:
                    best_score = ratio
                    best = {
                        "x": min(item["x"] for item in group),
                        "y": min(item["y"] for item in group),
                        "w": (
                            max(item["x"] + item["w"] for item in group)
                            - min(item["x"] for item in group)
                        ),
                        "h": (
                            max(item["y"] + item["h"] for item in group)
                            - min(item["y"] for item in group)
                        ),
                        "text": combined,
                        "confidence": max(
                            item["confidence"] for item in group
                        )
                    }

            if best is None or best_score < 0.72:
                return {
                    "status": "NOT_CHECKED",
                    "reason":
                        "Automatic OCR could not reliably locate "
                        "the register number.",
                    "expected_register_number": expected_register,
                    "detection_method":
                        "OCR automatic register-number discovery",
                    "detector_score": round(float(best_score), 4)
                }

            margin_x = max(12, int(best["w"] * 0.25))
            margin_y = max(8, int(best["h"] * 0.35))

            image_height, image_width = reference_image.shape[:2]

            x = max(0, best["x"] - margin_x)
            y = max(0, best["y"] - margin_y)
            right = min(
                image_width,
                best["x"] + best["w"] + margin_x
            )
            bottom = min(
                image_height,
                best["y"] + best["h"] + margin_y
            )

            width = max(1, right - x)
            height = max(1, bottom - y)

            result = compare_register_number(
                reference_path, temp_path,
                x=x, y=y, width=width, height=height
            )

            result["region"] = "Register Number"
            result["detected_region"] = {
                "x": x, "y": y,
                "width": width, "height": height
            }
            result["expected_register_number"] = expected_register
            result["detection_method"] = (
                "OCR automatic register-number discovery"
            )
            result["detector_score"] = round(
                float(best_score), 4
            )
            result["ocr_candidate"] = best.get("text", "")

            return result

        except Exception as exc:
            return {
                "status": "ERROR",
                "reason":
                    "Automatic register-number detection failed: "
                    + str(exc)
            }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# =========================================================
# STRUCTURED TAMPER ANALYSIS
# =========================================================

def _status_is_tampered(result):
    return isinstance(result, dict) and result.get("status") == "TAMPERED"


def _analyze_structured_tampering(
    name_result,
    signature_result,
    seal_result,
    register_number_result
):
    """Combine the configured field-level comparisons only.

    IMPORTANT: this function has no dependency on image/CNN variables.
    That prevents the old NameError/analysis_error path.
    """
    components = []
    tampered_signature_numbers = []

    if _status_is_tampered(name_result):
        components.append("student_name")

    if isinstance(signature_result, dict):
        if _status_is_tampered(signature_result):
            components.append("signature")

        signatures = signature_result.get("signatures", [])
        if isinstance(signatures, list):
            for index, result in enumerate(signatures, 1):
                if _status_is_tampered(result):
                    tampered_signature_numbers.append(index)
            if tampered_signature_numbers and "signature" not in components:
                components.append("signature")

    if _status_is_tampered(seal_result):
        components.append("seal")

    if _status_is_tampered(register_number_result):
        components.append("register_number")

    # Remove duplicates while preserving order.
    components = list(dict.fromkeys(components))

    tampered = bool(components)

    if not tampered:
        reason = (
            "All configured certificate regions matched the trusted reference."
        )
    else:
        labels = []
        if "student_name" in components:
            labels.append("student name")
        if "signature" in components:
            if tampered_signature_numbers:
                labels.append(
                    "signature(s) " + ", ".join(
                        str(n) for n in tampered_signature_numbers
                    )
                )
            else:
                labels.append("signature")
        if "seal" in components:
            labels.append("seal")
        if "register_number" in components:
            labels.append("register number")

        reason = "Possible tampering detected in: " + ", ".join(labels) + "."

    return {
        "tampered": tampered,
        "components": components,
        "tampered_signature_numbers": tampered_signature_numbers,
        "reason": reason,
    }


def _result_score(result, default=0.0):
    """Safely read a detector tamper score."""
    if not isinstance(result, dict):
        return float(default)
    try:
        value = float(result.get("tamper_score", default))
        return max(0.0, min(1.0, value))
    except (TypeError, ValueError):
        return float(default)


def _calculate_structured_score(
    name_result,
    signature_result,
    seal_result,
    register_number_result
):
    """Return the strongest configured structured tamper score."""
    scores = []

    if _status_is_tampered(name_result):
        scores.append(_result_score(name_result, 0.75))

    if isinstance(signature_result, dict):
        if _status_is_tampered(signature_result):
            scores.append(_result_score(signature_result, 0.75))
        signatures = signature_result.get("signatures", [])
        if isinstance(signatures, list):
            for result in signatures:
                if _status_is_tampered(result):
                    scores.append(_result_score(result, 0.75))

    if _status_is_tampered(seal_result):
        scores.append(_result_score(seal_result, 0.75))

    if _status_is_tampered(register_number_result):
        scores.append(_result_score(register_number_result, 0.75))

    return max(scores) if scores else 0.0


# =========================================================
# MAIN ANALYSIS
# =========================================================

def analyze_image(
    file_bytes: bytes,
    reference_path: str | None = None,
    certificate_id: str | None = None
) -> dict:
    """Run ELA/CNN plus reference-guided structured verification.

    The reference certificate is authoritative for field-level tampering.
    Certificate-specific checks are controlled by CERTIFICATE_CHECKS.
    """
    try:
        pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        pil_image.load()
    except Exception as e:
        return {
            "verdict": "invalid_image",
            "forgery_score": 1.0,
            "heuristic_score": 0.0,
            "image_score": 0.0,
            "structured_score": 0.0,
            "cnn_score": None,
            "features": {},
            "threshold": getattr(settings, "FORGERY_SCORE_THRESHOLD", 0.5),
            "reference_used": reference_path,
            "certificate_checks": _get_certificate_checks(reference_path),
            "alignment": None,
            "student_name": None,
            "signature": None,
            "seal": None,
            "register_number": None,
            "structured_tampering": False,
            "structured_comparison_available": False,
            "tampered_components": [],
            "tampered_signature_numbers": [],
            "verification_reason": "The uploaded file could not be read as an image.",
            "error": str(e),
        }

    # ---------------------------------------------------------
    # ELA / IMAGE SCORE
    # ---------------------------------------------------------
    try:
        ela = _ela_image(
            pil_image,
            quality=getattr(settings, "ELA_QUALITY", 90)
        )
        features = _extract_features(ela)
        heuristic_score = _score_from_features(features)
    except Exception as e:
        features = {}
        heuristic_score = 0.0
        ela_error = str(e)
    else:
        ela_error = None

    cnn_score = predict_with_cnn(pil_image)
    if cnn_score is not None:
        image_score = 0.5 * heuristic_score + 0.5 * float(cnn_score)
    else:
        image_score = heuristic_score

    image_score = max(0.0, min(1.0, float(image_score)))

    reference_filename = (
        os.path.basename(reference_path).lower()
        if reference_path
        else ""
    )
    checks = _get_certificate_checks(reference_path)

    name_result = {"status": "NOT_CHECKED"}
    signature_result = {"status": "NOT_CHECKED"}
    seal_result = {"status": "NOT_CHECKED"}
    register_number_result = {"status": "NOT_CHECKED"}
    alignment_result = None

    structured_comparison_available = False

    # ---------------------------------------------------------
    # REFERENCE-GUIDED ANALYSIS
    # ---------------------------------------------------------
    if reference_path:
        try:
            reference, aligned = _align_images(reference_path, file_bytes)
            structured_comparison_available = True
            alignment_result = {
                "status": "SUCCESS",
                "reference_size": list(reference.shape),
                "aligned_size": list(aligned.shape),
            }

            if checks.get("name", False):
                try:
                    name_result = _compare_name(reference_path, aligned)
                except Exception as e:
                    name_result = {"status": "ERROR", "error": str(e)}
            else:
                name_result = {
                    "status": "NOT_CHECKED",
                    "reason": "Student name comparison is disabled for this certificate.",
                }

            if checks.get("signature", False):
                try:
                    signature_result = _compare_signatures_automatic(
                        reference_path,
                        aligned
                    )
                except Exception as e:
                    signature_result = {"status": "ERROR", "error": str(e)}
            else:
                signature_result = {
                    "status": "NOT_CHECKED",
                    "reason": "Signature comparison is disabled for this certificate.",
                }

            if checks.get("seal", False):
                try:
                    seal_result = _compare_seal(reference_path, aligned)
                except Exception as e:
                    seal_result = {"status": "ERROR", "error": str(e)}
            else:
                seal_result = {"status": "NOT_CHECKED"}

            if checks.get("register_number", False):
                try:
                    register_number_result = _compare_register_number(
                        reference_path,
                        aligned,
                        certificate_id
                    )
                except Exception as e:
                    register_number_result = {"status": "ERROR", "error": str(e)}
            else:
                register_number_result = {
                    "status": "NOT_CHECKED",
                    "reason": "Register number comparison is disabled for this certificate.",
                }

        except Exception as e:
            alignment_result = {
                "status": "ERROR",
                "error": str(e),
            }
            # Alignment failure means the structured comparison did NOT succeed.
            structured_comparison_available = False

    # ---------------------------------------------------------
    # STRUCTURED RESULT
    # ---------------------------------------------------------
    structured_analysis = _analyze_structured_tampering(
        name_result,
        signature_result,
        seal_result,
        register_number_result
    )
    structured_tampered = structured_analysis["tampered"]
    structured_score = _calculate_structured_score(
        name_result,
        signature_result,
        seal_result,
        register_number_result
    )

    # Any detector error is reported explicitly, but an ERROR is never
    # silently treated as a tampered field.
    detector_errors = []
    for label, result in (
        ("student_name", name_result),
        ("signature", signature_result),
        ("seal", seal_result),
        ("register_number", register_number_result),
    ):
        if isinstance(result, dict) and result.get("status") == "ERROR":
            detector_errors.append(label)

    # ---------------------------------------------------------
    # FINAL DECISION
    # ---------------------------------------------------------
    # With a trusted reference, configured structured comparison has priority.
    # C8 is deliberately immune to ELA/CNN noise: only seal/register decide it.
    if structured_comparison_available:
        if structured_tampered:
            verdict = "likely_forged"
            final_score = structured_score
        elif reference_filename == "c8.jpeg":
            verdict = "likely_genuine"
            final_score = 0.0
        elif detector_errors:
            verdict = "analysis_inconclusive"
            final_score = image_score
        else:
            # All configured fields matched. Do not call it forged just because
            # JPEG metadata/compression changed the ELA score.
            verdict = "likely_genuine"
            final_score = 0.0
    else:
        # No usable reference: image analysis is the fallback only.
        threshold = float(getattr(settings, "FORGERY_SCORE_THRESHOLD", 0.5))
        verdict = (
            "likely_forged"
            if image_score >= threshold
            else "analysis_inconclusive"
        )
        final_score = image_score

    final_score = max(0.0, min(1.0, float(final_score)))

    # ---------------------------------------------------------
    # HUMAN-READABLE REASON
    # ---------------------------------------------------------
    if structured_tampered:
        if reference_filename == "c4.jpeg" and structured_analysis["tampered_signature_numbers"]:
            signature_text = ", ".join(
                f"Signature {n}"
                for n in structured_analysis["tampered_signature_numbers"]
            )
            verification_reason = (
                f"Certificate is likely forged because {signature_text} "
                "does not match the trusted reference."
            )
        else:
            verification_reason = structured_analysis["reason"]
    elif structured_comparison_available and detector_errors:
        verification_reason = (
            "Reference alignment succeeded, but one or more configured "
            "detectors could not complete: " + ", ".join(detector_errors) + "."
        )
    elif structured_comparison_available and reference_filename == "c8.jpeg":
        verification_reason = (
            "C8 certificate verified against the trusted reference. "
            "Seal and register number match. Student name and signatures "
            "are intentionally not checked for C8."
        )
    elif structured_comparison_available:
        verification_reason = (
            "All configured monitored certificate regions match the trusted "
            "reference. No structured tampering was detected."
        )
    else:
        verification_reason = (
            "Trusted reference comparison could not be completed. "
            "The result is based on image analysis only."
        )

    if ela_error:
        verification_reason += f" ELA analysis warning: {ela_error}"

    return {
        "verdict": verdict,
        "forgery_score": round(final_score, 4),
        "heuristic_score": round(float(heuristic_score), 4),
        "image_score": round(float(image_score), 4),
        "structured_score": round(float(structured_score), 4),
        "cnn_score": cnn_score,
        "features": {
            k: round(float(v), 4)
            for k, v in features.items()
            if isinstance(v, (int, float))
        },
        "threshold": getattr(settings, "FORGERY_SCORE_THRESHOLD", 0.5),
        "reference_used": reference_path,
        "certificate_checks": checks,
        "alignment": alignment_result,
        "student_name": name_result,
        "signature": signature_result,
        "seal": seal_result,
        "register_number": register_number_result,
        "structured_tampering": structured_tampered,
        "structured_comparison_available": structured_comparison_available,
        "tampered_components": structured_analysis["components"],
        "tampered_signature_numbers": structured_analysis["tampered_signature_numbers"],
        "verification_reason": verification_reason,
        "detector_errors": detector_errors,
    }
