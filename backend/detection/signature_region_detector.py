import cv2
import numpy as np


def _iou(a, b):
    ax1 = a["x"]
    ay1 = a["y"]
    ax2 = ax1 + a["width"]
    ay2 = ay1 + a["height"]

    bx1 = b["x"]
    by1 = b["y"]
    bx2 = bx1 + b["width"]
    by2 = by1 + b["height"]

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)

    intersection = iw * ih

    union = (
        a["width"] * a["height"]
        + b["width"] * b["height"]
        - intersection
    )

    if union <= 0:
        return 0.0

    return intersection / union


def _merge_close_components(mask):
    """
    Join nearby handwriting strokes without
    merging the signature with the printed name.
    """

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (25, 5)
    )

    merged = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1
    )

    return merged

def _blue_signature_candidates(image):
    """
    Detect blue handwritten signatures.
    Useful for certificates such as C5.
    """

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV
    )

    # Broad blue range.
    lower = np.array([
        80,
        25,
        25
    ])

    upper = np.array([
        165,
        255,
        255
    ])

    mask = cv2.inRange(
        hsv,
        lower,
        upper
    )

    # Remove tiny noise.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3, 3)
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
    )

    # Join signature strokes.
    merged = _merge_close_components(
        mask
    )

    return merged


def _dark_signature_candidates(image):
    """
    Detect dark/black handwritten signatures.

    Used for certificates where signatures are black.
    """

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    # Dark ink.
    _, mask = cv2.threshold(
        gray,
        150,
        255,
        cv2.THRESH_BINARY_INV
    )

    # Remove tiny noise.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3, 3)
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
    )

    # Connect handwriting strokes.
    merged = _merge_close_components(
        mask
    )

    return merged


def _extract_candidates(
    image,
    mask,
    ink_type
):
    """
    Extract signature-shaped regions from a mask.
    """

    height, width = image.shape[:2]

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    for contour in contours:

        x, y, w, h = cv2.boundingRect(
            contour
        )

        if w <= 0 or h <= 0:
            continue

        area = w * h

        # Ignore tiny noise.
        if area < 500:
            continue

        # Ignore enormous regions.
        if area > width * height * 0.08:
            continue

        center_y = y + h / 2

        # Signatures should normally be in
        # the lower portion of a certificate.
        if center_y < height * 0.58:
            continue

        aspect_ratio = (
            w / float(max(h, 1))
        )

        # Signature-like horizontal shape.
        if aspect_ratio < 1.6:
            continue

        if aspect_ratio > 12:
            continue

        # Prevent extremely thin text lines.
        if h < 12:
            continue

        # Prevent huge vertical blocks.
        if h > height * 0.10:
            continue

        crop = mask[
            y:y + h,
            x:x + w
        ]

        if crop.size == 0:
            continue

        ink_ratio = (
            np.count_nonzero(crop)
            / float(crop.size)
        )

        if ink_ratio < 0.02:
            continue

        if ink_ratio > 0.75:
            continue

        # Edge structure.
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        gray_crop = gray[
            y:y + h,
            x:x + w
        ]

        edges = cv2.Canny(
            gray_crop,
            50,
            150
        )

        edge_ratio = (
            np.count_nonzero(edges)
            / float(edges.size)
        )

        contour_area = cv2.contourArea(
            contour
        )

        rectangularity = (
            contour_area / float(area)
            if area > 0
            else 0
        )

        # Handwritten signatures generally have
        # irregular shapes rather than perfect rectangles.
        irregularity = 1.0 - min(
            rectangularity,
            1.0
        )

        aspect_score = min(
            aspect_ratio / 5.0,
            1.0
        )

        density_score = 1.0 - min(
            abs(ink_ratio - 0.25) / 0.40,
            1.0
        )

        edge_score = min(
            edge_ratio / 0.20,
            1.0
        )

        score = (
            aspect_score * 0.25
            + density_score * 0.30
            + edge_score * 0.20
            + irregularity * 0.25
        )

        candidates.append({
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
            "aspect_ratio": round(
                float(aspect_ratio),
                4
            ),
            "ink_ratio": round(
                float(ink_ratio),
                4
            ),
            "edge_ratio": round(
                float(edge_ratio),
                4
            ),
            "rectangularity": round(
                float(rectangularity),
                4
            ),
            "score": round(
                float(score),
                4
            ),
            "ink_type": ink_type
        })

    return candidates


def detect_signatures(image, expected_count=None):
    """
    Combined automatic signature detector.

    It tries:
        1. blue ink
        2. dark ink

    and combines the candidates.
    """

    if image is None:
        return []

    blue_mask = _blue_signature_candidates(
        image
    )

    dark_mask = _dark_signature_candidates(
        image
    )

    blue = _extract_candidates(
        image,
        blue_mask,
        "blue"
    )

    dark = _extract_candidates(
        image,
        dark_mask,
        "dark"
    )

    candidates = blue + dark

    # Sort strongest first.
    candidates.sort(
        key=lambda c: c["score"],
        reverse=True
    )

    # Remove overlapping duplicate boxes.
    selected = []

    for candidate in candidates:

        duplicate = False

        for existing in selected:

            if _iou(
                candidate,
                existing
            ) > 0.35:

                duplicate = True
                break

        if not duplicate:
            selected.append(
                candidate
            )

    if expected_count is not None:
        return selected[:expected_count]
    
    return selected