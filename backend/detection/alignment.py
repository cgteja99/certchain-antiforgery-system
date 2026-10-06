import cv2
import numpy as np


# =========================================================
# CERTIFICATE ALIGNMENT
# =========================================================

def align_certificate(reference, submitted):
    """
    Align submitted certificate to the reference certificate.

    Strategy:
        1. Resize submitted image to reference size.
        2. Use ECC affine alignment.
        3. Ignore the name/signature/seal areas during alignment.
        4. Apply the affine transformation.
        5. Fall back to resized image if alignment fails.

    Returns:
        aligned_image, success
    """

    # -----------------------------------------------------
    # VALIDATE INPUT
    # -----------------------------------------------------

    if reference is None or submitted is None:
        return None, False

    ref_h, ref_w = reference.shape[:2]

    # -----------------------------------------------------
    # RESIZE SUBMITTED IMAGE
    # -----------------------------------------------------

    submitted_resized = cv2.resize(
        submitted,
        (ref_w, ref_h),
        interpolation=cv2.INTER_AREA
    )

    # -----------------------------------------------------
    # GRAYSCALE
    # -----------------------------------------------------

    ref_gray = cv2.cvtColor(
        reference,
        cv2.COLOR_BGR2GRAY
    )

    sub_gray = cv2.cvtColor(
        submitted_resized,
        cv2.COLOR_BGR2GRAY
    )

    # -----------------------------------------------------
    # SMOOTH IMAGES
    # -----------------------------------------------------

    ref_gray = cv2.GaussianBlur(
        ref_gray,
        (5, 5),
        0
    )

    sub_gray = cv2.GaussianBlur(
        sub_gray,
        (5, 5),
        0
    )

    # -----------------------------------------------------
    # ALIGNMENT MASK
    # -----------------------------------------------------
    #
    # We do NOT want ECC to use:
    #
    #   - student name
    #   - marks
    #   - signatures
    #   - seal
    #
    # because these areas may be modified.
    #
    # Use mainly the certificate background/border.
    #
    # -----------------------------------------------------

    mask = np.ones(
        (ref_h, ref_w),
        dtype=np.uint8
    ) * 255

    # -----------------------------------------------------
    # REMOVE NAME REGION
    # -----------------------------------------------------

    mask[
        int(ref_h * 0.27):int(ref_h * 0.43),
        int(ref_w * 0.10):int(ref_w * 0.90)
    ] = 0

    # -----------------------------------------------------
    # REMOVE MARKS / TABLE REGION
    # -----------------------------------------------------

    mask[
        int(ref_h * 0.43):int(ref_h * 0.80),
        int(ref_w * 0.10):int(ref_w * 0.90)
    ] = 0

    # -----------------------------------------------------
    # REMOVE LOWER SIGNATURE / SEAL REGION
    # -----------------------------------------------------

    mask[
        int(ref_h * 0.80):int(ref_h * 0.98),
        int(ref_w * 0.10):int(ref_w * 0.90)
    ] = 0

    # -----------------------------------------------------
    # KEEP OUTER BORDER
    # -----------------------------------------------------

    # Top border
    mask[
        0:int(ref_h * 0.20),
        0:ref_w
    ] = 255

    # Left border
    mask[
        0:ref_h,
        0:int(ref_w * 0.10)
    ] = 255

    # Right border
    mask[
        0:ref_h,
        int(ref_w * 0.90):ref_w
    ] = 255

    # Bottom border
    mask[
        int(ref_h * 0.92):ref_h,
        0:ref_w
    ] = 255

    # -----------------------------------------------------
    # INITIAL AFFINE MATRIX
    # -----------------------------------------------------

    warp_matrix = np.eye(
        2,
        3,
        dtype=np.float32
    )

    # -----------------------------------------------------
    # ECC PARAMETERS
    # -----------------------------------------------------

    criteria = (
        cv2.TERM_CRITERIA_EPS |
        cv2.TERM_CRITERIA_COUNT,
        200,
        1e-6
    )

    # -----------------------------------------------------
    # ECC ALIGNMENT
    # -----------------------------------------------------

    try:

        correlation, warp_matrix = cv2.findTransformECC(
            ref_gray,
            sub_gray,
            warp_matrix,
            cv2.MOTION_AFFINE,
            criteria,
            mask,
            5
        )

    except cv2.error as e:

        print(
            "WARNING: ECC alignment failed:"
        )

        print(e)

        print(
            "Using resized submitted image."
        )

        return submitted_resized, False

    # -----------------------------------------------------
    # SANITY CHECK
    # -----------------------------------------------------

    if not np.isfinite(warp_matrix).all():

        print(
            "WARNING: Invalid alignment matrix."
        )

        return submitted_resized, False

    # -----------------------------------------------------
    # APPLY AFFINE TRANSFORMATION
    # -----------------------------------------------------

    aligned = cv2.warpAffine(
        submitted_resized,
        warp_matrix,
        (ref_w, ref_h),
        flags=(
            cv2.INTER_LINEAR |
            cv2.WARP_INVERSE_MAP
        ),
        borderMode=cv2.BORDER_REPLICATE
    )

    # -----------------------------------------------------
    # CHECK RESULT
    # -----------------------------------------------------

    if aligned is None:

        print(
            "WARNING: Alignment produced no image."
        )

        return submitted_resized, False

    print(
        "ECC correlation:",
        round(float(correlation), 6)
    )

    print(
        "Affine matrix:"
    )

    print(warp_matrix)

    return aligned, True