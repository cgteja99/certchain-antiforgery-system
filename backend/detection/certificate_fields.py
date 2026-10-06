import re
from ocr_detector import extract_text


def extract_fields(text: str) -> dict:
    fields = {
        "student_name": None,
        "student_id": None,
        "course": None,
        "certificate_type": None,
    }

    # Student Name
    match = re.search(
        r"Student\s*Name\s*:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if match:
        fields["student_name"] = match.group(1).strip()

    # Student ID
    # Handles OCR variations such as:
    # Student ID: STU001
    # StudentD sTu001
    # StudentID STU001
    match = re.search(
        r"Student\s*(?:ID|D)\s*:?\s*([A-Za-z0-9_-]+)",
        text,
        re.IGNORECASE
    )

    if match:
        fields["student_id"] = match.group(1).strip().upper()

    # Course
    match = re.search(
        r"Course\s*:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if match:
        fields["course"] = match.group(1).strip()

    # Certificate Type
    match = re.search(
        r"Certificate\s*Type\s*:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if match:
        fields["certificate_type"] = match.group(1).strip()

    return fields


if __name__ == "__main__":

    image_path = r".\reference_data\certificates\c1.jpeg"
    print("Reading certificate...")
    print("-" * 50)

    text = extract_text(image_path)

    print("OCR TEXT:")
    print(text)

    print("-" * 50)
    print("EXTRACTED FIELDS:")
    print("-" * 50)

    fields = extract_fields(text)

    for key, value in fields.items():
        print(f"{key}: {value}")