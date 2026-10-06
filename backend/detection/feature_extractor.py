import cv2
import numpy as np


# =========================================================
# SIGNATURE FEATURE EXTRACTION
# =========================================================

def extract_signature_features(image, signature):

    if image is None:
        return None

    if signature is None:
        return None

    # -----------------------------------------------------
    # GET SIGNATURE BOUNDING BOX
    # -----------------------------------------------------

    x = int(signature["x"])
    y = int(signature["y"])
    w = int(signature["width"])
    h = int(signature["height"])

    height, width = image.shape[:2]

    # Keep coordinates inside image
    x1 = max(0, x)
    y1 = max(0, y)

    x2 = min(width, x + w)
    y2 = min(height, y + h)

    if x2 <= x1 or y2 <= y1:
        return None

    # -----------------------------------------------------
    # CROP SIGNATURE
    # -----------------------------------------------------

    crop = image[y1:y2, x1:x2]

    if crop.size == 0:
        return None

    gray = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2GRAY
    )

    hsv = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2HSV
    )

    # -----------------------------------------------------
    # BASIC FEATURES
    # -----------------------------------------------------

    crop_height, crop_width = gray.shape

    aspect_ratio = (
        crop_width / float(max(crop_height, 1))
    )

    # -----------------------------------------------------
    # INK MASK
    # -----------------------------------------------------

    dark = cv2.inRange(
        gray,
        0,
        175
    )

    saturation = hsv[:, :, 1]

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
    # INK RATIO
    # -----------------------------------------------------

    ink_pixels = np.count_nonzero(ink)

    total_pixels = ink.size

    ink_ratio = (
        ink_pixels /
        float(max(total_pixels, 1))
    )

    # -----------------------------------------------------
    # EDGE FEATURES
    # -----------------------------------------------------

    edges = cv2.Canny(
        gray,
        50,
        150
    )

    edge_ratio = (
        np.count_nonzero(edges) /
        float(max(edges.size, 1))
    )

    # -----------------------------------------------------
    # COLOR FEATURES
    # -----------------------------------------------------

    mean_hue = float(
        np.mean(hsv[:, :, 0])
    )

    mean_saturation = float(
        np.mean(hsv[:, :, 1])
    )

    mean_value = float(
        np.mean(hsv[:, :, 2])
    )

    # -----------------------------------------------------
    # SIGNATURE PROJECTIONS
    # -----------------------------------------------------

    horizontal_projection = np.sum(
        ink > 0,
        axis=1
    )

    vertical_projection = np.sum(
        ink > 0,
        axis=0
    )

    max_horizontal_density = (
        np.max(horizontal_projection) /
        float(max(crop_width, 1))
    )

    max_vertical_density = (
        np.max(vertical_projection) /
        float(max(crop_height, 1))
    )

    # -----------------------------------------------------
    # CONTOUR FEATURES
    # -----------------------------------------------------

    contours, _ = cv2.findContours(
        ink,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contour_count = len(contours)

    total_contour_area = 0.0

    for contour in contours:

        total_contour_area += cv2.contourArea(
            contour
        )

    contour_area_ratio = (
        total_contour_area /
        float(max(crop_width * crop_height, 1))
    )

    # -----------------------------------------------------
    # RETURN FEATURES
    # -----------------------------------------------------

    return {

        "width": int(crop_width),

        "height": int(crop_height),

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

        "mean_hue": round(
            mean_hue,
            2
        ),

        "mean_saturation": round(
            mean_saturation,
            2
        ),

        "mean_value": round(
            mean_value,
            2
        ),

        "max_horizontal_density": round(
            float(max_horizontal_density),
            4
        ),

        "max_vertical_density": round(
            float(max_vertical_density),
            4
        ),

        "contour_count": int(
            contour_count
        ),

        "contour_area_ratio": round(
            float(contour_area_ratio),
            4
        )
    }


# =========================================================
# SEAL FEATURE EXTRACTION
# =========================================================

def extract_seal_features(image, seal):

    if image is None:
        return None

    if seal is None:
        return None

    # -----------------------------------------------------
    # GET SEAL BOUNDING BOX
    # -----------------------------------------------------

    x = int(seal["x"])
    y = int(seal["y"])
    w = int(seal["width"])
    h = int(seal["height"])

    height, width = image.shape[:2]

    x1 = max(0, x)
    y1 = max(0, y)

    x2 = min(width, x + w)
    y2 = min(height, y + h)

    if x2 <= x1 or y2 <= y1:
        return None

    # -----------------------------------------------------
    # CROP
    # -----------------------------------------------------

    crop = image[y1:y2, x1:x2]

    if crop.size == 0:
        return None

    hsv = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2HSV
    )

    gray = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2GRAY
    )

    # -----------------------------------------------------
    # RED MASK
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
    # COMBINED SEAL MASK
    # -----------------------------------------------------

    color_mask = cv2.bitwise_or(
        red_mask,
        blue_mask
    )

    # -----------------------------------------------------
    # COLOR RATIOS
    # -----------------------------------------------------

    total_pixels = float(
        max(color_mask.size, 1)
    )

    blue_ratio = (
        np.count_nonzero(blue_mask)
        / total_pixels
    )

    red_ratio = (
        np.count_nonzero(red_mask)
        / total_pixels
    )

    color_ratio = (
        np.count_nonzero(color_mask)
        / total_pixels
    )

    # -----------------------------------------------------
    # DETECT DOMINANT COLOR
    # -----------------------------------------------------

    if blue_ratio > red_ratio:

        dominant_color = "blue"

    elif red_ratio > blue_ratio:

        dominant_color = "red"

    else:

        dominant_color = "unknown"

    # -----------------------------------------------------
    # COLOR FEATURES
    # -----------------------------------------------------

    mean_hue = float(
        np.mean(hsv[:, :, 0])
    )

    mean_saturation = float(
        np.mean(hsv[:, :, 1])
    )

    mean_value = float(
        np.mean(hsv[:, :, 2])
    )

    # -----------------------------------------------------
    # EDGE FEATURES
    # -----------------------------------------------------

    edges = cv2.Canny(
        gray,
        50,
        150
    )

    edge_ratio = (
        np.count_nonzero(edges)
        / float(max(edges.size, 1))
    )

    # -----------------------------------------------------
    # CONTOURS
    # -----------------------------------------------------

    contours, _ = cv2.findContours(
        color_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contour_count = len(contours)

    # -----------------------------------------------------
    # LARGEST CONTOUR
    # -----------------------------------------------------

    circularity = 0.0

    largest_area = 0.0
    largest_perimeter = 0.0

    for contour in contours:

        area = cv2.contourArea(
            contour
        )

        perimeter = cv2.arcLength(
            contour,
            True
        )

        if area > largest_area:

            largest_area = area
            largest_perimeter = perimeter

    # -----------------------------------------------------
    # CIRCULARITY
    # -----------------------------------------------------

    if largest_perimeter > 0:

        circularity = (
            4.0
            * np.pi
            * largest_area
            / (largest_perimeter ** 2)
        )

    # -----------------------------------------------------
    # ASPECT RATIO
    # -----------------------------------------------------

    aspect_ratio = (
        w / float(max(h, 1))
    )

    # -----------------------------------------------------
    # RETURN FEATURES
    # -----------------------------------------------------

    return {

        "width": int(w),

        "height": int(h),

        "aspect_ratio": round(
            float(aspect_ratio),
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

        "dominant_color": dominant_color,

        "mean_hue": round(
            mean_hue,
            2
        ),

        "mean_saturation": round(
            mean_saturation,
            2
        ),

        "mean_value": round(
            mean_value,
            2
        ),

        "edge_ratio": round(
            float(edge_ratio),
            4
        ),

        "contour_count": int(
            contour_count
        ),

        "circularity": round(
            float(circularity),
            4
        )
    }