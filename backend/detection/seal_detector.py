import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim


def compare_seal(
    original_path,
    tampered_path,
    x,
    y,
    width,
    height
):
    original = cv2.imread(original_path)
    tampered = cv2.imread(tampered_path)

    if original is None:
        raise FileNotFoundError(original_path)

    if tampered is None:
        raise FileNotFoundError(tampered_path)

    original_crop = original[
        y:y + height,
        x:x + width
    ]

    tampered_crop = tampered[
        y:y + height,
        x:x + width
    ]

    original_gray = cv2.cvtColor(
        original_crop,
        cv2.COLOR_BGR2GRAY
    )

    tampered_gray = cv2.cvtColor(
        tampered_crop,
        cv2.COLOR_BGR2GRAY
    )

    # SSIM
    similarity = ssim(
        original_gray,
        tampered_gray
    )

    # Pixel difference
    difference = cv2.absdiff(
        original_gray,
        tampered_gray
    )

    pixel_difference = (
        np.mean(difference) / 255.0
    )

    # Edge comparison
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
        ) / 255.0
    )

    # Combined score
    tamper_score = (
        (1 - similarity) * 0.4
        + pixel_difference * 0.3
        + edge_difference * 0.3
    )

    if tamper_score >= 0.25:
        status = "TAMPERED"
    else:
        status = "MATCH"

    return {
        "similarity": round(float(similarity), 4),
        "pixel_difference": round(float(pixel_difference), 4),
        "edge_difference": round(float(edge_difference), 4),
        "tamper_score": round(float(tamper_score), 4),
        "status": status
    }


if __name__ == "__main__":

    original_path = (
        r".\reference_data\certificates\c1.jpeg"
    )

    tampered_path = (
        r".\reference_data\certificates\aligned_t1.jpeg"
    )

    print("CERTIFICATE 1 SEAL TAMPER DETECTION")
    print("=" * 55)

    result = compare_seal(
        original_path,
        tampered_path,
        x=190,
        y=500,
        width=100,
        height=100
    )

    print(result)