import cv2
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_text(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(image_path)

    # Upscale
    image = cv2.resize(
        image,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # Grayscale
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Mild contrast enhancement
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    # Mild denoising
    denoised = cv2.GaussianBlur(
        enhanced,
        (3, 3),
        0
    )

    # Light sharpening
    sharpened = cv2.addWeighted(
        enhanced,
        1.5,
        denoised,
        -0.5,
        0
    )

    # Save for inspection
    cv2.imwrite(
        r".\reference_data\certificates\debug_c1_ocr.png",
        sharpened
    )

    # OCR
    text = pytesseract.image_to_string(
        sharpened,
        config="--oem 3 --psm 6"
    )

    return text


if __name__ == "__main__":

    image_path = (
        r".\reference_data\certificates\c1.jpeg"
    )

    print("Running improved OCR...")
    print("-" * 50)

    try:

        text = extract_text(image_path)

        print(text)

        print("-" * 50)
        print("OCR completed.")

    except Exception as e:

        print("OCR failed!")
        print("Error:", e)