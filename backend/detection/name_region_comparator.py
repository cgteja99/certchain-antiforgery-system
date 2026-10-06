# ==========================================================
# NAME REGION COMPARATOR
# ==========================================================

import cv2
import numpy as np
import re
import os
from difflib import SequenceMatcher

try:
    import pytesseract

    # Windows Tesseract installation
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

except Exception:
    pytesseract = None

# ==========================================================
# TESSERACT CONFIGURATION
# ==========================================================

if pytesseract is not None:
    _TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for _path in _TESSERACT_PATHS:
        if os.path.isfile(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break


# ==========================================================
# TEXT NORMALIZATION
# ==========================================================

def _normalize_text(text):
    """
    Normalize OCR text for reliable comparison.
    """

    if not text:
        return ""

    text = str(text).upper()

    # Common OCR corrections
    text = text.replace("|", "I")
    text = text.replace("’", "'")
    text = text.replace("`", "'")

    # Keep only letters, numbers and spaces
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)

    # Remove repeated spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _clean_ocr_text(text):
    """
    Clean OCR output while preserving useful name text.
    """

    if not text:
        return ""

    text = _normalize_text(text)

    if not text:
        return ""

    words = text.split()

    cleaned = []

    for word in words:

        # Normal word
        if len(word) >= 2:
            cleaned.append(word)

        # Useful single-letter initial
        elif len(word) == 1 and word.isalpha():
            cleaned.append(word)

    return " ".join(cleaned)


def _text_similarity(text1, text2):
    """
    Return similarity between two normalized strings.
    """

    text1 = _normalize_text(text1)
    text2 = _normalize_text(text2)

    if not text1 or not text2:
        return 0.0

    return round(
        SequenceMatcher(
            None,
            text1,
            text2
        ).ratio(),
        4
    )


# ==========================================================
# OCR SINGLE IMAGE
# ==========================================================

# ==========================================================
# OCR IMAGE BUILDING
# ==========================================================

def _ocr_single(image, config):
    """Run one OCR attempt safely with multiple preprocessing variants."""
    if pytesseract is None or image is None or image.size == 0:
        return ""

    try:
        candidates = [image]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        candidates.append(gray)

        enlarged3 = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        enlarged5 = cv2.resize(gray, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)
        candidates.extend([enlarged3, enlarged5])

        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        candidates.append(cv2.filter2D(enlarged5, -1, kernel))

        _, otsu = cv2.threshold(enlarged5, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(otsu)

        adaptive = cv2.adaptiveThreshold(enlarged5, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
        candidates.append(adaptive)

        _, inverted = cv2.threshold(enlarged5, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        candidates.append(inverted)

        best_text = ""
        for candidate in candidates:
            try:
                result = pytesseract.image_to_string(candidate, config=config)
                result = _clean_ocr_text(result)
                if len(result) > len(best_text):
                    best_text = result
            except Exception:
                continue
        return best_text
    except Exception:
        return ""


# ==========================================================
# OCR NAME
# ==========================================================

def _ocr_name(image):
    """
    Reliable OCR for certificate name regions.

    Uses the enlarged name region with Tesseract PSM 7.
    This avoids selecting long garbage OCR results from
    heavily processed images.
    """

    if pytesseract is None:
        return ""

    if image is None or image.size == 0:
        return ""

    try:
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY
            )
        else:
            gray = image.copy()

        # Enlarge the name region
        enlarged = cv2.resize(
            gray,
            None,
            fx=5,
            fy=5,
            interpolation=cv2.INTER_CUBIC
        )

        # Single reliable OCR attempt
        text = _ocr_single(
            enlarged,
            "--psm 7"
        )

        return text

    except Exception:
        return ""
# ==========================================================
# OCR IMAGE BUILDER
# ==========================================================

def _build_ocr_images(image):
    """
    Create OCR-friendly versions of a certificate name region.

    Small certificate name regions are enlarged before OCR.
    Several preprocessing variants are returned so Tesseract
    has multiple chances to recognize the name.
    """

    if image is None or image.size == 0:
        return []

    images = []

    # ------------------------------------------------------
    # 1. ORIGINAL
    # ------------------------------------------------------

    images.append(image)

    # ------------------------------------------------------
    # 2. GRAYSCALE
    # ------------------------------------------------------

    if len(image.shape) == 3:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    else:

        gray = image.copy()

    images.append(gray)

    # ------------------------------------------------------
    # 3. 5X ENLARGED GRAYSCALE
    # ------------------------------------------------------

    enlarged = cv2.resize(
        gray,
        None,
        fx=5,
        fy=5,
        interpolation=cv2.INTER_CUBIC
    )

    images.append(enlarged)

    # ------------------------------------------------------
    # 4. SHARPENED
    # ------------------------------------------------------

    try:

        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])

        sharpened = cv2.filter2D(
            enlarged,
            -1,
            kernel
        )

        images.append(sharpened)

    except Exception:
        pass

    # ------------------------------------------------------
    # 5. OTSU
    # ------------------------------------------------------

    try:

        _, otsu = cv2.threshold(
            enlarged,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        images.append(otsu)

    except Exception:
        pass

    # ------------------------------------------------------
    # 6. ADAPTIVE THRESHOLD
    # ------------------------------------------------------

    try:

        adaptive = cv2.adaptiveThreshold(
            enlarged,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11
        )

        images.append(adaptive)

    except Exception:
        pass

    # ------------------------------------------------------
    # 7. INVERTED OTSU
    # ------------------------------------------------------

    try:

        _, inverted = cv2.threshold(
            enlarged,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        images.append(inverted)

    except Exception:
        pass

    # ------------------------------------------------------
    # 8. PADDED VERSIONS
    # ------------------------------------------------------

    padded_images = []

    for img in images:

        try:

            padded = cv2.copyMakeBorder(
                img,
                20,
                20,
                20,
                20,
                cv2.BORDER_CONSTANT,
                value=255
            )

            padded_images.append(padded)

        except Exception:
            pass

    images.extend(padded_images)

    return images

# ==========================================================
# OCR NAME USING EXPECTED NAME
# ==========================================================

def _ocr_name_with_expected(image, expected_name=None):
    """
    OCR name region and prefer the candidate closest to the
    expected certificate name.

    This is important because OCR may return several different
    interpretations for low-resolution certificate text.
    """

    if image is None or image.size == 0:
        return ""

    if pytesseract is None:
        return ""

    candidates = []

    images = _build_ocr_images(image)

    configs = [
        "--psm 6",
        "--psm 7",
        "--psm 8",
        "--psm 11",
        "--psm 13"
    ]

    # ------------------------------------------------------
    # Collect OCR candidates
    # ------------------------------------------------------

    for img in images:

        for config in configs:

            text = _ocr_single(
                img,
                config
            )

            if text:
                candidates.append(text)

    if not candidates:
        return ""

    # ------------------------------------------------------
    # Remove duplicates
    # ------------------------------------------------------

    unique = []

    for text in candidates:

        if text not in unique:
            unique.append(text)

    candidates = unique

    # ------------------------------------------------------
    # Remove short garbage
    # ------------------------------------------------------

    candidates = [
        text
        for text in candidates
        if len(text.replace(" ", "")) >= 4
    ]

    if not candidates:
        return ""

    # ------------------------------------------------------
    # If expected name is available, use similarity
    # ------------------------------------------------------

    expected_normalized = _normalize_text(
        expected_name
    )

    if expected_normalized:

        scored = []

        for text in candidates:

            similarity = _text_similarity(
                text,
                expected_normalized
            )

            # Candidate quality
            words = len(text.split())

            length_difference = abs(
                len(
                    text.replace(" ", "")
                )
                -
                len(
                    expected_normalized.replace(" ", "")
                )
            )

            score = (
                similarity * 100
                +
                min(words, 6) * 3
                -
                min(length_difference, 20) * 0.2
            )

            scored.append(
                (
                    score,
                    similarity,
                    text
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return scored[0][2]

    # ------------------------------------------------------
    # No expected name
    # ------------------------------------------------------

    return _ocr_name(image)


# ==========================================================
# SAFE CROP
# ==========================================================

def _crop_region(
    image,
    x,
    y,
    width,
    height
):
    """
    Safely crop a region from an image.
    """

    if image is None:
        return None

    h, w = image.shape[:2]

    x1 = max(
        0,
        int(x)
    )

    y1 = max(
        0,
        int(y)
    )

    x2 = min(
        w,
        x1 + int(width)
    )

    y2 = min(
        h,
        y1 + int(height)
    )

    if x2 <= x1 or y2 <= y1:
        return None

    return image[
        y1:y2,
        x1:x2
    ]


# ==========================================================
# VISUAL COMPARISON
# ==========================================================

def _compare_pixels(
    original_crop,
    uploaded_crop
):
    """
    Compare the original and uploaded name regions.
    """

    if (
        original_crop is None
        or uploaded_crop is None
    ):
        return 0.0, 1.0, 1.0

    # ------------------------------------------------------
    # Grayscale
    # ------------------------------------------------------

    if len(original_crop.shape) == 3:

        original_gray = cv2.cvtColor(
            original_crop,
            cv2.COLOR_BGR2GRAY
        )

    else:

        original_gray = original_crop.copy()

    if len(uploaded_crop.shape) == 3:

        uploaded_gray = cv2.cvtColor(
            uploaded_crop,
            cv2.COLOR_BGR2GRAY
        )

    else:

        uploaded_gray = uploaded_crop.copy()

    # ------------------------------------------------------
    # Same dimensions
    # ------------------------------------------------------

    h = min(
        original_gray.shape[0],
        uploaded_gray.shape[0]
    )

    w = min(
        original_gray.shape[1],
        uploaded_gray.shape[1]
    )

    if h <= 0 or w <= 0:
        return 0.0, 1.0, 1.0

    original_gray = cv2.resize(
        original_gray,
        (w, h),
        interpolation=cv2.INTER_AREA
    )

    uploaded_gray = cv2.resize(
        uploaded_gray,
        (w, h),
        interpolation=cv2.INTER_AREA
    )

    # ------------------------------------------------------
    # Normalize brightness
    # ------------------------------------------------------

    original_norm = cv2.normalize(
        original_gray,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    uploaded_norm = cv2.normalize(
        uploaded_gray,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    # ------------------------------------------------------
    # Pixel similarity
    # ------------------------------------------------------

    difference = cv2.absdiff(
        original_norm,
        uploaded_norm
    )

    similarity = 1.0 - (
        np.mean(difference) / 255.0
    )

    similarity = float(
        np.clip(
            similarity,
            0.0,
            1.0
        )
    )

    # ------------------------------------------------------
    # Ink difference
    # ------------------------------------------------------

    _, original_binary = cv2.threshold(
        original_norm,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    _, uploaded_binary = cv2.threshold(
        uploaded_norm,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    original_ink = (
        original_binary > 0
    ).astype(np.uint8)

    uploaded_ink = (
        uploaded_binary > 0
    ).astype(np.uint8)

    ink_difference = np.mean(
        np.abs(
            original_ink.astype(float)
            -
            uploaded_ink.astype(float)
        )
    )

    # ------------------------------------------------------
    # Edge difference
    # ------------------------------------------------------

    original_edges = cv2.Canny(
        original_norm,
        50,
        150
    )

    uploaded_edges = cv2.Canny(
        uploaded_norm,
        50,
        150
    )

    edge_difference = np.mean(
        np.abs(
            original_edges.astype(float)
            -
            uploaded_edges.astype(float)
        )
    ) / 255.0

    return (
        round(float(similarity), 4),
        round(float(ink_difference), 4),
        round(float(edge_difference), 4)
    )


# ==========================================================
# MAIN NAME COMPARISON
# ==========================================================

def compare_name_region(
    original_path,
    tampered_path,
    x=None,
    y=None,
    width=None,
    height=None,
    expected_name=None,
    threshold=0.45
):
    """
    Compare a certificate name region between a trusted
    reference and uploaded/tampered certificate.
    """

    # ------------------------------------------------------
    # LOAD IMAGES
    # ------------------------------------------------------

    original = cv2.imread(
        original_path
    )

    tampered = cv2.imread(
        tampered_path
    )

    if original is None:

        raise FileNotFoundError(
            f"Original image not found: {original_path}"
        )

    if tampered is None:

        raise FileNotFoundError(
            f"Tampered image not found: {tampered_path}"
        )

    # ------------------------------------------------------
    # REGION REQUIRED
    # ------------------------------------------------------

    if None in (
        x,
        y,
        width,
        height
    ):

        raise ValueError(
            "Name region coordinates are required."
        )

    # ------------------------------------------------------
    # CROP
    # ------------------------------------------------------

    original_crop = _crop_region(
        original,
        x,
        y,
        width,
        height
    )

    tampered_crop = _crop_region(
        tampered,
        x,
        y,
        width,
        height
    )

    if original_crop is None:

        raise ValueError(
            "Invalid name region in original certificate."
        )

    if tampered_crop is None:

        raise ValueError(
            "Invalid name region in uploaded certificate."
        )

    # ------------------------------------------------------
    # OCR
    # ------------------------------------------------------

    reference_text = _ocr_name(
    original_crop
    )

    uploaded_text = _ocr_name(
    tampered_crop
    )

    # ------------------------------------------------------
    # NORMALIZE
    # ------------------------------------------------------

    expected_normalized = _normalize_text(
        expected_name
    )

    reference_normalized = _normalize_text(
        reference_text
    )

    uploaded_normalized = _normalize_text(
        uploaded_text
    )

    # ------------------------------------------------------
    # TEXT SIMILARITY
    # ------------------------------------------------------

    text_similarity = _text_similarity(
        uploaded_normalized,
        expected_normalized
    )

    # ------------------------------------------------------
    # REFERENCE VS EXPECTED
    # ------------------------------------------------------

    reference_expected_similarity = _text_similarity(
        reference_normalized,
        expected_normalized
    )

    # ------------------------------------------------------
    # VISUAL COMPARISON
    # ------------------------------------------------------

    similarity, ink_difference, edge_difference = (
        _compare_pixels(
            original_crop,
            tampered_crop
        )
    )

    # ------------------------------------------------------
    # VISUAL TAMPER SCORE
    # ------------------------------------------------------

    visual_difference = (
        1.0 - similarity
    )

    visual_score = (
        0.55 * visual_difference
        +
        0.25 * ink_difference
        +
        0.20 * edge_difference
    )

    visual_score = round(
        float(visual_score),
        4
    )

    # ------------------------------------------------------
    # OCR RELIABILITY
    # ------------------------------------------------------

    reference_reliable = (
        len(reference_normalized) >= 4
    )

    uploaded_reliable = (
        len(uploaded_normalized) >= 4
    )

    # ------------------------------------------------------
    # EXPECTED NAME MATCH
    # ------------------------------------------------------

    expected_match_score = 0.0

    expected_match = False

    if (
        uploaded_normalized
        and expected_normalized
    ):

        expected_match_score = _text_similarity(
            uploaded_normalized,
            expected_normalized
        )

        expected_match = (
            expected_match_score >= 0.90
        )

    # ------------------------------------------------------
    # REFERENCE VALIDITY
    # ------------------------------------------------------

    reference_matches_expected = (
        reference_expected_similarity >= 0.70
    )

    # ------------------------------------------------------
    # FINAL DECISION
    # ------------------------------------------------------

    ocr_warning = None
    decision_reason = ""
    status = "MATCH"

    # ======================================================
    # CASE 1: UPLOADED OCR IS RELIABLE
    # ======================================================

    if uploaded_reliable:

        # --------------------------------------------------
        # Uploaded name does not match expected name
        # --------------------------------------------------

        if not expected_match:

            status = "TAMPERED"

            ocr_warning = (
                "OCR name differs from expected name"
            )

            decision_reason = (
                "OCR detected a name different "
                "from the expected certificate name."
            )

        # --------------------------------------------------
        # Uploaded OCR matches expected
        # --------------------------------------------------

        else:

            # If reference is readable but does not match
            # expected name, flag certificate inconsistency.

            if (
                reference_reliable
                and
                not reference_matches_expected
            ):

                status = "TAMPERED"

                ocr_warning = (
                    "Reference OCR differs from expected name"
                )

                decision_reason = (
                    "The trusted reference OCR does not "
                    "match the expected certificate name."
                )

            elif visual_score >= threshold:

                status = "TAMPERED"

                decision_reason = (
                    "OCR matched the expected name, "
                    "but the name region shows significant "
                    "visual modification."
                )

            else:

                status = "MATCH"

                decision_reason = (
                    "OCR name matches the expected "
                    "certificate name and the name region "
                    "is visually consistent."
                )

    # ======================================================
    # CASE 2: UPLOADED OCR FAILED
    # ======================================================

    else:

        ocr_warning = (
            "OCR could not reliably read the uploaded name"
        )

        # --------------------------------------------------
        # Reference is reliable and expected
        # --------------------------------------------------

        if (
            reference_reliable
            and
            reference_matches_expected
        ):

            if visual_score >= threshold:

                status = "TAMPERED"

                decision_reason = (
                    "OCR could not reliably read the uploaded "
                    "name, but the name region shows significant "
                    "visual modification."
                )

            else:

                status = "MATCH"

                decision_reason = (
                    "OCR could not reliably read the uploaded "
                    "name, but the name region is visually "
                    "consistent with the trusted reference."
                )

        # --------------------------------------------------
        # Neither OCR result is reliable
        # --------------------------------------------------

        elif not reference_reliable:

            if visual_score >= threshold:

                status = "TAMPERED"

                decision_reason = (
                    "OCR could not reliably read either name, "
                    "and the name region shows significant "
                    "visual modification."
                )

            else:

                # IMPORTANT:
                # We do NOT claim the certificate is definitely
                # valid. The visual comparison is only below the
                # tamper threshold.

                status = "MATCH"

                decision_reason = (
                    "OCR could not reliably read either name, "
                    "and the name region is visually consistent "
                    "with the trusted reference."
                )

        # --------------------------------------------------
        # Reference readable but differs from expected
        # --------------------------------------------------

        else:

            if visual_score >= threshold:

                status = "TAMPERED"

                decision_reason = (
                    "OCR could not reliably read the uploaded "
                    "name and the name region differs "
                    "significantly from the reference."
                )

            else:

                status = "MATCH"

                decision_reason = (
                    "OCR could not reliably read the uploaded "
                    "name, but the name region is visually "
                    "consistent with the trusted reference."
                )

    # ------------------------------------------------------
    # RETURN RESULT
    # ------------------------------------------------------

    return {

        "reference_text":
            reference_text,

        "uploaded_text":
            uploaded_text,

        "expected_name":
            expected_name,

        "text_similarity":
            round(
                float(text_similarity),
                4
            ),

        "expected_match_score":
            round(
                float(expected_match_score),
                4
            ),

        "reference_expected_similarity":
            round(
                float(reference_expected_similarity),
                4
            ),

        "similarity":
            similarity,

        "ink_difference":
            ink_difference,

        "edge_difference":
            edge_difference,

        "tamper_score":
            visual_score,

        "threshold":
            threshold,

        "name_region": {

            "x":
                int(x),

            "y":
                int(y),

            "width":
                int(width),

            "height":
                int(height)
        },

        "ocr_warning":
            ocr_warning,

        "decision_reason":
            decision_reason,

        "status":
            status
    }


# ==========================================================
# ALIAS
# ==========================================================

compare_name = compare_name_region

