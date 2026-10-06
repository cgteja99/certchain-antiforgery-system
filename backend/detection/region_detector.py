import cv2
import numpy as np


# =========================================================
# SIGNATURE DETECTION
# =========================================================

def detect_signature_candidates(image):

    if image is None:
        return []

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV
    )

    height, width = gray.shape

    # -----------------------------------------------------
    # SIGNATURE ZONE
    # -----------------------------------------------------

    x1 = int(width * 0.60)
    x2 = int(width * 0.82)

    y1 = int(height * 0.81)
    y2 = int(height * 0.89)

    x1 = max(0, min(x1, width - 1))
    x2 = max(x1 + 1, min(x2, width))

    y1 = max(0, min(y1, height - 1))
    y2 = max(y1 + 1, min(y2, height))

    roi_gray = gray[y1:y2, x1:x2]
    roi_hsv = hsv[y1:y2, x1:x2]

    if roi_gray.size == 0:
        return []

    # -----------------------------------------------------
    # DARK INK
    # -----------------------------------------------------

    dark = cv2.inRange(
        roi_gray,
        0,
        175
    )

    # -----------------------------------------------------
    # COLORED INK
    # -----------------------------------------------------

    saturation = roi_hsv[:, :, 1]

    colored = cv2.inRange(
        saturation,
        30,
        255
    )

    ink = cv2.bitwise_or(
        dark,
        colored
    )

    # -----------------------------------------------------
    # REMOVE LONG LINES
    # -----------------------------------------------------

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (20, 1)
    )

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, 10)
    )

    horizontal_lines = cv2.morphologyEx(
        ink,
        cv2.MORPH_OPEN,
        horizontal_kernel
    )

    vertical_lines = cv2.morphologyEx(
        ink,
        cv2.MORPH_OPEN,
        vertical_kernel
    )

    lines = cv2.bitwise_or(
        horizontal_lines,
        vertical_lines
    )

    cleaned = cv2.subtract(
        ink,
        lines
    )

    # -----------------------------------------------------
    # CLEAN SMALL NOISE
    # -----------------------------------------------------

    small_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2, 2)
    )

    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_OPEN,
        small_kernel,
        iterations=1
    )

    # -----------------------------------------------------
    # CONNECT SIGNATURE STROKES
    # -----------------------------------------------------

    join_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (9, 5)
    )

    connected = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_CLOSE,
        join_kernel,
        iterations=1
    )

    dilate_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (5, 3)
    )

    connected = cv2.dilate(
        connected,
        dilate_kernel,
        iterations=1
    )

    # -----------------------------------------------------
    # DEBUG
    # -----------------------------------------------------

    cv2.imwrite(
        "reference_data/certificates/debug_signature_connected.png",
        connected
    )

    # -----------------------------------------------------
    # COMPONENTS
    # -----------------------------------------------------

    num_labels, labels, stats, centroids = \
        cv2.connectedComponentsWithStats(
            connected,
            8
        )

    candidates = []

    for i in range(1, num_labels):

        bx = stats[i, cv2.CC_STAT_LEFT]
        by = stats[i, cv2.CC_STAT_TOP]

        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]

        area = stats[i, cv2.CC_STAT_AREA]

        if area < 30:
            continue

        if area > 2500:
            continue

        if bw < 20:
            continue

        if bh < 6:
            continue

        aspect_ratio = bw / float(bh)

        if aspect_ratio < 2.0:
            continue

        if aspect_ratio > 12.0:
            continue

        component_mask = (
            labels[
                by:by + bh,
                bx:bx + bw
            ] == i
        )

        ink_pixels = np.count_nonzero(
            component_mask
        )

        ink_ratio = (
            ink_pixels /
            float(bw * bh)
        )

        sat_crop = saturation[
            by:by + bh,
            bx:bx + bw
        ]

        mean_saturation = float(
            np.mean(sat_crop)
        )

        density_score = 1.0 - min(
            abs(ink_ratio - 0.25) / 0.40,
            1.0
        )

        aspect_score = min(
            aspect_ratio / 5.0,
            1.0
        )

        score = (
            density_score * 0.55
            + aspect_score * 0.45
        )

        if score < 0.35:
            continue

        candidates.append({
            "x": int(bx + x1),
            "y": int(by + y1),
            "width": int(bw),
            "height": int(bh),
            "aspect_ratio": round(
                float(aspect_ratio),
                4
            ),
            "ink_ratio": round(
                float(ink_ratio),
                4
            ),
            "mean_saturation": round(
                mean_saturation,
                2
            ),
            "score": round(
                float(score),
                4
            )
        })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates[:3]


# =========================================================
# SEAL DETECTION
# =========================================================

def detect_seal_candidates(image):

    if image is None:
        return []

    height, width = image.shape[:2]

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV
    )

    # -----------------------------------------------------
    # BLUE MASK
    # -----------------------------------------------------

    lower_blue = np.array([
        90,
        40,
        30
    ])

    upper_blue = np.array([
        140,
        255,
        255
    ])

    blue_mask = cv2.inRange(
        hsv,
        lower_blue,
        upper_blue
    )

    # -----------------------------------------------------
    # RED / MAROON MASK
    # -----------------------------------------------------

    lower_red_1 = np.array([
        0,
        35,
        25
    ])

    upper_red_1 = np.array([
        12,
        255,
        255
    ])

    lower_red_2 = np.array([
        160,
        35,
        25
    ])

    upper_red_2 = np.array([
        179,
        255,
        255
    ])

    red_1 = cv2.inRange(
        hsv,
        lower_red_1,
        upper_red_1
    )

    red_2 = cv2.inRange(
        hsv,
        lower_red_2,
        upper_red_2
    )

    red_mask = cv2.bitwise_or(
        red_1,
        red_2
    )

    # -----------------------------------------------------
    # PROCESS EACH COLOR SEPARATELY
    # -----------------------------------------------------

    masks = [
        ("blue", blue_mask),
        ("red", red_mask)
    ]

    candidates = []

    image_area = width * height

    for color_name, original_mask in masks:

        mask = original_mask.copy()

        # -------------------------------------------------
        # MORPHOLOGICAL CLEANUP
        # -------------------------------------------------

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (5, 5)
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel,
            iterations=2
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel,
            iterations=1
        )

        # -------------------------------------------------
        # DEBUG
        # -------------------------------------------------

        cv2.imwrite(
            f"reference_data/certificates/debug_seal_{color_name}_mask.png",
            mask
        )

        # -------------------------------------------------
        # FIND CONTOURS
        # -------------------------------------------------

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:

            x, y, w, h = cv2.boundingRect(
                contour
            )

            if w <= 0 or h <= 0:
                continue

            box_area = w * h

            # -------------------------------------------------
            # SIZE FILTER
            # -------------------------------------------------

            if box_area < 100:
                continue

            if box_area > image_area * 0.08:
                continue

            # -------------------------------------------------
            # POSITION FILTER
            # -------------------------------------------------

            center_y = y + h / 2.0

            if center_y < height * 0.50:
                continue

            # -------------------------------------------------
            # ASPECT RATIO
            # -------------------------------------------------

            aspect_ratio = (
                w / float(max(h, 1))
            )

            if aspect_ratio < 0.50:
                continue

            if aspect_ratio > 2.00:
                continue

            # -------------------------------------------------
            # COLOR RATIO
            # -------------------------------------------------

            color_crop = mask[
                y:y + h,
                x:x + w
            ]

            color_ratio = (
                np.count_nonzero(color_crop)
                / float(max(color_crop.size, 1))
            )

            if color_ratio < 0.10:
                continue

            # -------------------------------------------------
            # BLUE RATIO
            # -------------------------------------------------

            blue_crop = blue_mask[
                y:y + h,
                x:x + w
            ]

            blue_ratio = (
                np.count_nonzero(blue_crop)
                / float(max(blue_crop.size, 1))
            )

            # -------------------------------------------------
            # RED RATIO
            # -------------------------------------------------

            red_crop = red_mask[
                y:y + h,
                x:x + w
            ]

            red_ratio = (
                np.count_nonzero(red_crop)
                / float(max(red_crop.size, 1))
            )

            # -------------------------------------------------
            # CIRCULARITY
            # -------------------------------------------------

            contour_area = cv2.contourArea(
                contour
            )

            perimeter = cv2.arcLength(
                contour,
                True
            )

            if perimeter > 0:

                circularity = (
                    4.0
                    * np.pi
                    * contour_area
                    / (perimeter * perimeter)
                )

            else:

                circularity = 0.0

            # -------------------------------------------------
            # SATURATION
            # -------------------------------------------------

            saturation_crop = hsv[
                y:y + h,
                x:x + w,
                1
            ]

            mean_saturation = float(
                np.mean(saturation_crop)
            )

            # -------------------------------------------------
            # VALUE
            # -------------------------------------------------

            value_crop = hsv[
                y:y + h,
                x:x + w,
                2
            ]

            mean_value = float(
                np.mean(value_crop)
            )

            # -------------------------------------------------
            # SCORES
            # -------------------------------------------------

            circularity_score = min(
                circularity / 0.80,
                1.0
            )

            color_score = min(
                color_ratio / 0.60,
                1.0
            )

            saturation_score = min(
                mean_saturation / 120.0,
                1.0
            )

            aspect_score = (
                1.0 -
                min(
                    abs(aspect_ratio - 1.0),
                    1.0
                )
            )

            score = (
                circularity_score * 0.40
                + color_score * 0.30
                + saturation_score * 0.15
                + aspect_score * 0.15
            )

            candidates.append({

                "x": int(x),

                "y": int(y),

                "width": int(w),

                "height": int(h),

                "area": int(box_area),

                "aspect_ratio": round(
                    float(aspect_ratio),
                    4
                ),

                "circularity": round(
                    float(circularity),
                    4
                ),

                "blue_ratio": round(
                    float(blue_ratio),
                    4
                ),

                "red_ratio": round(
                    float(red_ratio),
                    4
                ),

                "color_ratio": round(
                    float(color_ratio),
                    4
                ),

                "mean_saturation": round(
                    float(mean_saturation),
                    2
                ),

                "mean_value": round(
                    float(mean_value),
                    2
                ),

                "color": color_name,

                "score": round(
                    float(score),
                    4
                )
            })

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates[:10]