import cv2
import pytesseract
import re


# =========================================================
# TESSERACT CONFIGURATION
# =========================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# =========================================================
# NAME REGION EXTRACTION
# =========================================================

def extract_name_region(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(
            image_path
        )

    # -----------------------------------------------------
    # CERTIFICATE NAME REGION
    # -----------------------------------------------------

    crop = image[
        150:230,
        70:430
    ]

    # -----------------------------------------------------
    # ENLARGE
    # -----------------------------------------------------

    crop = cv2.resize(
        crop,
        None,
        fx=4,
        fy=4,
        interpolation=cv2.INTER_CUBIC
    )

    # -----------------------------------------------------
    # GRAYSCALE
    # -----------------------------------------------------

    gray = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2GRAY
    )

    # -----------------------------------------------------
    # CONTRAST ENHANCEMENT
    # -----------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    # -----------------------------------------------------
    # SAVE DEBUG IMAGE
    # -----------------------------------------------------

    output_path = (
        r".\reference_data\certificates\debug_name.png"
    )

    cv2.imwrite(
        output_path,
        enhanced
    )

    # -----------------------------------------------------
    # OCR
    # -----------------------------------------------------

    text = pytesseract.image_to_string(
        enhanced,
        config="--oem 3 --psm 6"
    )

    return text, output_path


# =========================================================
# NORMALIZE NAME
# =========================================================

def normalize_name(name):

    if name is None:
        return None

    # Keep alphabetic characters and spaces
    name = re.sub(
        r"[^A-Za-z ]",
        " ",
        name
    )

    # Remove multiple spaces
    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip().upper()


# =========================================================
# FIND NAME
# =========================================================

def find_name(text):

    if not text:
        return None

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # -----------------------------------------------------
    # FIRST: LOOK FOR CANDIDATE NAME PATTERN
    # -----------------------------------------------------
    #
    # We expect a name containing at least 3 words.
    #
    # Example:
    #
    # KHOT KALPESH MOHAN PS
    # Mahindre Komal Surendra
    #
    # -----------------------------------------------------

    possible_names = []

    for line in lines:

        cleaned = normalize_name(line)

        if not cleaned:
            continue

        words = cleaned.split()

        # A candidate name normally contains
        # at least 3 alphabetic words.
        if len(words) < 3:
            continue

        # Reject obvious certificate/OCR headings
        rejected_words = {
            "THIS",
            "CERTIFY",
            "BOARD",
            "CANDIDATE",
            "FULL",
            "NAME",
            "SCHOOL",
            "CERTIFICATE",
            "STATEMENT",
            "SECONDARY",
            "DIVISIONAL",
            "SERIAL",
            "NUMBER",
            "MOTHER",
            "MARCH"
        }

        if any(
            word in rejected_words
            for word in words
        ):
            continue

        possible_names.append(
            cleaned
        )

    # -----------------------------------------------------
    # RETURN FIRST VALID NAME
    # -----------------------------------------------------

    if possible_names:
        return possible_names[0]

    return None


# =========================================================
# MAIN TEST
# =========================================================

if __name__ == "__main__":

    image_path = (
        r".\reference_data\certificates\aligned_t1.jpeg"
    )

    print(
        "STUDENT NAME DETECTION"
    )

    print(
        "=" * 55
    )

    try:

        text, output_path = (
            extract_name_region(
                image_path
            )
        )

        print(
            "OCR from name region:"
        )

        print(
            "-" * 55
        )

        print(text)

        detected_name = find_name(
            text
        )

        print(
            "-" * 55
        )

        print(
            "Detected name:"
        )

        print(
            detected_name
        )

        print(
            "-" * 55
        )

        print(
            "Name crop saved to:"
        )

        print(
            output_path
        )

    except Exception as e:

        print(
            "Name detection failed!"
        )

        print(
            "Error:",
            e
        )