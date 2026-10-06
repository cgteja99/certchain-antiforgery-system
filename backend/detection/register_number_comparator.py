import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# =========================================================
# NORMALIZE UNIVERSITY SEAT NUMBER
# =========================================================

def _normalize_register_text(text):
    """
    Keep only letters and digits.

    Example:
        "1PE10EC038"
        becomes:
        "1PE10EC038"
    """

    if not text:
        return ""

    return "".join(
        ch.upper()
        for ch in str(text)
        if ch.isalnum()
    )


# =========================================================
# OCR UNIVERSITY SEAT NUMBER
# =========================================================

def _ocr_register_number(image):

    try:

        import pytesseract

    except ImportError:

        return ""

    try:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # -------------------------------------------------
        # Upscale
        # -------------------------------------------------

        gray = cv2.resize(
            gray,
            None,
            fx=4,
            fy=4,
            interpolation=cv2.INTER_CUBIC
        )

        # -------------------------------------------------
        # Improve contrast
        # -------------------------------------------------

        gray = cv2.GaussianBlur(
            gray,
            (3, 3),
            0
        )

        threshold = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY
            + cv2.THRESH_OTSU
        )[1]

        # -------------------------------------------------
        # OCR
        #
        # University Seat Number can contain
        # LETTERS + DIGITS.
        # -------------------------------------------------

        text = pytesseract.image_to_string(
            threshold,
            config=(
                "--psm 7 "
                "-c tessedit_char_whitelist="
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "abcdefghijklmnopqrstuvwxyz"
                "0123456789"
            )
        )

        return _normalize_register_text(
            text
        )

    except Exception:

        return ""


# =========================================================
# UNIVERSITY SEAT NUMBER COMPARISON
# =========================================================

def compare_register_number(
    original_path,
    tampered_path,
    x,
    y,
    width,
    height
):

    original = cv2.imread(
        original_path
    )

    tampered = cv2.imread(
        tampered_path
    )

    if original is None:

        raise FileNotFoundError(
            original_path
        )

    if tampered is None:

        raise FileNotFoundError(
            tampered_path
        )

    # =====================================================
    # CROP UNIVERSITY SEAT NUMBER
    # =====================================================

    original_crop = original[
        y:y + height,
        x:x + width
    ]

    tampered_crop = tampered[
        y:y + height,
        x:x + width
    ]

    if (
        original_crop.size == 0
        or tampered_crop.size == 0
    ):

        raise ValueError(
            "University Seat Number region is empty."
        )

    # =====================================================
    # OCR COMPARISON
    # =====================================================

    original_text = _ocr_register_number(
        original_crop
    )

    tampered_text = _ocr_register_number(
        tampered_crop
    )

    print()
    print("=" * 60)
    print("UNIVERSITY SEAT NUMBER DEBUG")
    print("=" * 60)

    print(
        "Reference OCR :",
        original_text
    )

    print(
        "Uploaded OCR  :",
        tampered_text
    )

    # =====================================================
    # OCR COMPARISON
    # =====================================================

    ocr_checked = False
    ocr_match = None

    if (
        len(original_text) >= 6
        and len(tampered_text) >= 6
    ):

        ocr_checked = True

        ocr_match = (
            original_text
            == tampered_text
        )

        if ocr_match:

            print(
                "OCR Result    : MATCH"
            )

        else:

            print(
                "OCR Result    : TAMPERED"
            )

    else:

        print(
            "OCR Result    : NOT RELIABLE"
        )

    # =====================================================
    # IMAGE COMPARISON
    # =====================================================

    original_gray = cv2.cvtColor(
        original_crop,
        cv2.COLOR_BGR2GRAY
    )

    tampered_gray = cv2.cvtColor(
        tampered_crop,
        cv2.COLOR_BGR2GRAY
    )

    similarity = ssim(
        original_gray,
        tampered_gray
    )

    difference = cv2.absdiff(
        original_gray,
        tampered_gray
    )

    pixel_difference = (
        np.mean(difference)
        / 255.0
    )

    original_edges = cv2.Canny(
        original_gray,
        50,
        150
    )

    tampered_edges = cv2.Canny(
        tampered_gray,
        50,
        150
    )

    edge_difference = (
        np.mean(
            cv2.absdiff(
                original_edges,
                tampered_edges
            )
        )
        / 255.0
    )

    # =====================================================
    # IMAGE TAMPER SCORE
    # =====================================================

    image_tamper_score = (
        (1 - similarity) * 0.55
        + pixel_difference * 0.30
        + edge_difference * 0.15
    )

    # =====================================================
    # FINAL DECISION
    # =====================================================

    if ocr_checked:

        if ocr_match:

            status = "MATCH"

            tamper_score = float(
                image_tamper_score
            )

        else:

            status = "TAMPERED"

            tamper_score = max(
                float(image_tamper_score),
                0.50
            )

    else:

        # If OCR cannot read the number,
        # use image comparison.

        if image_tamper_score >= 0.03:

            status = "TAMPERED"

        else:

            status = "MATCH"

        tamper_score = float(
            image_tamper_score
        )

    print(
        "SSIM          :",
        round(float(similarity), 4)
    )

    print(
        "Pixel Diff    :",
        round(float(pixel_difference), 4)
    )

    print(
        "Edge Diff     :",
        round(float(edge_difference), 4)
    )

    print(
        "Tamper Score  :",
        round(float(tamper_score), 4)
    )

    print(
        "FINAL STATUS  :",
        status
    )

    print("=" * 60)
    print()

    # =====================================================
    # RETURN RESULT
    # =====================================================

    return {

        "similarity":
            round(
                float(similarity),
                4
            ),

        "pixel_difference":
            round(
                float(pixel_difference),
                4
            ),

        "edge_difference":
            round(
                float(edge_difference),
                4
            ),

        "tamper_score":
            round(
                float(tamper_score),
                4
            ),

        "status":
            status,

        "reference_text":
            original_text,

        "uploaded_text":
            tampered_text,

        "ocr_checked":
            ocr_checked,

        "ocr_match":
            ocr_match
    }