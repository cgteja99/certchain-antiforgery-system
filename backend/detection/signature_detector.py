import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim


def compare_signature_region(
    reference_path,
    aligned_path,
    region,
    region_name
):
    """
    Compare a trusted signature region against
    the same region in the aligned uploaded certificate.

    Designed to detect:
    - replaced signatures
    - removed signatures
    - modified signatures
    - substantially changed signature strokes
    """

    original = cv2.imread(reference_path)
    aligned = cv2.imread(aligned_path)

    if original is None:
        raise FileNotFoundError(reference_path)

    if aligned is None:
        raise FileNotFoundError(aligned_path)

    # =====================================================
    # REGION
    # =====================================================

    x = int(region["x"])
    y = int(region["y"])
    width = int(region["width"])
    height = int(region["height"])

    if width <= 0 or height <= 0:
        raise ValueError(
            "Invalid signature region."
        )

    # =====================================================
    # SAFE BOUNDS
    # =====================================================

    h1, w1 = original.shape[:2]
    h2, w2 = aligned.shape[:2]

    x1 = max(0, min(x, w1))
    y1 = max(0, min(y, h1))

    x2 = min(x + width, w1)
    y2 = min(y + height, h1)

    tx1 = max(0, min(x, w2))
    ty1 = max(0, min(y, h2))

    tx2 = min(x + width, w2)
    ty2 = min(y + height, h2)

    if x2 <= x1 or y2 <= y1:
        raise ValueError(
            "Invalid reference signature region."
        )

    if tx2 <= tx1 or ty2 <= ty1:
        raise ValueError(
            "Signature region is outside uploaded image."
        )

    # =====================================================
    # CROP
    # =====================================================

    original_crop = original[
        y1:y2,
        x1:x2
    ]

    aligned_crop = aligned[
        ty1:ty2,
        tx1:tx2
    ]

    # =====================================================
    # SAME SIZE
    # =====================================================

    target_h = min(
        original_crop.shape[0],
        aligned_crop.shape[0]
    )

    target_w = min(
        original_crop.shape[1],
        aligned_crop.shape[1]
    )

    if target_h <= 0 or target_w <= 0:
        raise ValueError(
            "Empty signature crop."
        )

    original_crop = original_crop[
        :target_h,
        :target_w
    ]

    aligned_crop = aligned_crop[
        :target_h,
        :target_w
    ]

    # =====================================================
    # GRAYSCALE
    # =====================================================

    original_gray = cv2.cvtColor(
        original_crop,
        cv2.COLOR_BGR2GRAY
    )

    aligned_gray = cv2.cvtColor(
        aligned_crop,
        cv2.COLOR_BGR2GRAY
    )

    # =====================================================
    # LIGHT BLUR
    #
    # Reduces tiny scanner/compression differences.
    # =====================================================

    original_gray = cv2.GaussianBlur(
        original_gray,
        (3, 3),
        0
    )

    aligned_gray = cv2.GaussianBlur(
        aligned_gray,
        (3, 3),
        0
    )

    # =====================================================
    # SSIM
    # =====================================================

    similarity = ssim(
        original_gray,
        aligned_gray,
        data_range=255
    )

    # =====================================================
    # BINARY INK
    # =====================================================

    _, original_ink = cv2.threshold(
        original_gray,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    _, aligned_ink = cv2.threshold(
        aligned_gray,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    # =====================================================
    # INK DIFFERENCE
    # =====================================================

    ink_difference_image = cv2.absdiff(
        original_ink,
        aligned_ink
    )

    changed_pixels = np.count_nonzero(
        ink_difference_image
    )

    total_pixels = ink_difference_image.size

    ink_difference = (
        changed_pixels /
        float(max(total_pixels, 1))
    )

    # =====================================================
    # INK AREA DIFFERENCE
    # =====================================================

    original_ink_pixels = np.count_nonzero(
        original_ink
    )

    aligned_ink_pixels = np.count_nonzero(
        aligned_ink
    )

    ink_area_difference = (
        abs(
            original_ink_pixels -
            aligned_ink_pixels
        )
        /
        float(
            max(
                original_ink_pixels,
                aligned_ink_pixels,
                1
            )
        )
    )

    # =====================================================
    # EDGE COMPARISON
    # =====================================================

    original_edges = cv2.Canny(
        original_gray,
        50,
        150
    )

    aligned_edges = cv2.Canny(
        aligned_gray,
        50,
        150
    )

    edge_difference = (
        np.mean(
            cv2.absdiff(
                original_edges,
                aligned_edges
            )
        )
        / 255.0
    )

    # =====================================================
    # INK OVERLAP / IOU
    # =====================================================

    original_binary = (
        original_ink > 0
    )

    aligned_binary = (
        aligned_ink > 0
    )

    intersection = np.logical_and(
        original_binary,
        aligned_binary
    ).sum()

    union = np.logical_or(
        original_binary,
        aligned_binary
    ).sum()

    ink_iou = (
        intersection /
        float(max(union, 1))
    )

    # =====================================================
    # FINAL TAMPER SCORE
    # =====================================================

    #
    # Higher score = more different
    #

    ssim_difference = (
        1.0 - float(similarity)
    )

    iou_difference = (
        1.0 - float(ink_iou)
    )

    tamper_score = (
        ssim_difference * 0.35
        + ink_difference * 0.30
        + edge_difference * 0.20
        + iou_difference * 0.15
    )

    # =====================================================
    # DECISION
    # =====================================================

    #
    # 0.12 is intentionally more sensitive than
    # the previous 0.20 threshold.
    #

    if tamper_score >= 0.12:

        status = "TAMPERED"

    else:

        status = "MATCH"

    # =====================================================
    # DEBUG
    # =====================================================

    print()
    print("-" * 60)
    print("SIGNATURE DEBUG")
    print("Region            :", region_name)
    print("X                 :", x)
    print("Y                 :", y)
    print("Width             :", width)
    print("Height            :", height)
    print("SSIM              :", round(float(similarity), 4))
    print(
        "SSIM Difference   :",
        round(float(ssim_difference), 4)
    )
    print(
        "Ink Difference    :",
        round(float(ink_difference), 4)
    )
    print(
        "Ink Area Diff     :",
        round(float(ink_area_difference), 4)
    )
    print(
        "Edge Difference   :",
        round(float(edge_difference), 4)
    )
    print(
        "Ink IoU            :",
        round(float(ink_iou), 4)
    )
    print(
        "Tamper Score      :",
        round(float(tamper_score), 4)
    )
    print("Status            :", status)
    print("-" * 60)

    # =====================================================
    # RETURN
    # =====================================================

    return {

        "region": region_name,

        "x": x,
        "y": y,
        "width": width,
        "height": height,

        "ssim_similarity": round(
            float(similarity),
            4
        ),

        "ink_difference": round(
            float(ink_difference),
            4
        ),

        "ink_area_difference": round(
            float(ink_area_difference),
            4
        ),

        "edge_difference": round(
            float(edge_difference),
            4
        ),

        "ink_iou": round(
            float(ink_iou),
            4
        ),

        "tamper_score": round(
            float(tamper_score),
            4
        ),

        "status": status
    }