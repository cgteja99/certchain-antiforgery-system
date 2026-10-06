import cv2
import numpy as np


def align_images(reference_path, uploaded_path):
    reference = cv2.imread(reference_path)
    uploaded = cv2.imread(uploaded_path)

    if reference is None:
        raise FileNotFoundError(
            f"Reference image not found: {reference_path}"
        )

    if uploaded is None:
        raise FileNotFoundError(
            f"Uploaded image not found: {uploaded_path}"
        )

    reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    uploaded_gray = cv2.cvtColor(uploaded, cv2.COLOR_BGR2GRAY)

    # Detect visual features
    orb = cv2.ORB_create(nfeatures=5000)

    keypoints1, descriptors1 = orb.detectAndCompute(
        reference_gray, None
    )

    keypoints2, descriptors2 = orb.detectAndCompute(
        uploaded_gray, None
    )

    if descriptors1 is None or descriptors2 is None:
        raise ValueError(
            "Could not find enough features in the certificate images."
        )

    # Match features
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
        key=lambda match: match.distance
    )

    good_matches = matches[:100]

    if len(good_matches) < 10:
        raise ValueError(
            f"Not enough matching features. Found {len(good_matches)}."
        )

    reference_points = np.float32([
        keypoints1[m.queryIdx].pt
        for m in good_matches
    ]).reshape(-1, 1, 2)

    uploaded_points = np.float32([
        keypoints2[m.trainIdx].pt
        for m in good_matches
    ]).reshape(-1, 1, 2)

    # Calculate transformation
    matrix, mask = cv2.findHomography(
        uploaded_points,
        reference_points,
        cv2.RANSAC,
        5.0
    )

    if matrix is None:
        raise ValueError("Could not align the certificate images.")

    height, width = reference.shape[:2]

    aligned = cv2.warpPerspective(
        uploaded,
        matrix,
        (width, height)
    )

    return reference, aligned


if __name__ == "__main__":

    # Choose which certificate pair to align
    reference_name = "c1.jpeg"
    tampered_name = "t1.jpeg"

    reference_path = (
        f".\\reference_data\\certificates\\{reference_name}"
    )

    tampered_path = (
        f".\\reference_data\\certificates\\{tampered_name}"
    )

    print("Aligning certificate images...")
    print("-" * 50)
    print("Original :", reference_name)
    print("Tampered :", tampered_name)

    try:
        reference, aligned = align_images(
            reference_path,
            tampered_path
        )

        output_path = (
            ".\\reference_data\\certificates\\aligned_t1.jpeg"
        )

        cv2.imwrite(output_path, aligned)

        print()
        print("Alignment successful!")
        print("Reference size:", reference.shape)
        print("Aligned tampered size:", aligned.shape)
        print()
        print("Aligned image saved to:")
        print(output_path)

    except Exception as e:
        print()
        print("Alignment failed!")
        print("Error:", e)