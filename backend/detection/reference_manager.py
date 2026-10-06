import hashlib
import json
import os
from pathlib import Path

REFERENCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "reference_data",
    "certificates"
)

REFERENCE_FILE = os.path.join(
    REFERENCE_DIR,
    "certificate_references.json"
)


# Existing project certificates are kept as a fallback.
CERTIFICATE_REFERENCE_MAP = {
    "A1465289": "c1.jpeg",
    "S150173796": "c2.jpeg",
    "1PE10EC038": "c3.jpeg",
    "MITU18DSME0016": "c4.jpeg",
    "95649026484": "c5.jpeg",
    "30906103052/RG": "c6.jpeg",
    "0425/2010": "c7.jpeg",
    "204163090011": "c8.jpeg",
    "1402005144": "c9.jpeg",
}


# Preserve the existing name-region configuration used by the
# project. Dynamic certificates can still use the normal detector
# defaults when no special region is configured.
NAME_REGION_MAP = {
    "A1465289": {
        "x": 150,
        "y": 190,
        "width": 220,
        "height": 50,
        "threshold": 0.45,
    },
    "S150173796": {
        "x": 150,
        "y": 190,
        "width": 220,
        "height": 50,
        "threshold": 0.45,
    },
}


def _ensure_reference_dir():
    os.makedirs(REFERENCE_DIR, exist_ok=True)


def _load_references():
    if not os.path.exists(REFERENCE_FILE):
        return {}

    try:
        with open(
            REFERENCE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_references(references):
    _ensure_reference_dir()

    temp_file = REFERENCE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            references,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(temp_file, REFERENCE_FILE)


def save_reference(certificate_hash: str, fields: dict):
    """Save or update trusted certificate metadata."""

    references = _load_references()
    references[str(certificate_hash)] = dict(fields or {})
    _save_references(references)


def get_reference(certificate_hash: str):
    """Return trusted metadata stored for a certificate hash."""

    references = _load_references()
    return references.get(certificate_hash)


def save_reference_image(
    certificate_id: str,
    file_bytes: bytes,
    original_filename: str = "certificate.jpeg"
):
    """
    Save the exact issued certificate bytes as its trusted reference.

    The filename is generated from the SHA-256 of the uploaded bytes,
    so certificate IDs containing '/', spaces, etc. are always safe.
    """

    if not certificate_id:
        raise ValueError("Certificate ID is required.")

    if not file_bytes:
        raise ValueError("Certificate image is empty.")

    _ensure_reference_dir()

    extension = Path(original_filename or "certificate.jpeg").suffix.lower()

    if extension not in {".jpeg", ".jpg", ".png"}:
        extension = ".jpeg"

    digest = hashlib.sha256(file_bytes).hexdigest()
    filename = f"ref_{digest}{extension}"
    path = Path(REFERENCE_DIR) / filename

    if not path.exists():
        with open(path, "wb") as f:
            f.write(file_bytes)

    return path


def get_reference_image(certificate_id: str):
    """
    Return the trusted reference certificate image.

    Lookup order:
    1. Existing C1-C9 hard-coded mappings.
    2. Existing certificate-ID-based image filenames.
    3. Dynamically registered references stored in
       certificate_references.json.
    """

    if not certificate_id:
        return None

    certificate_id = str(certificate_id).strip()

    # 1. Existing C1-C9 mapping.
    mapped_filename = CERTIFICATE_REFERENCE_MAP.get(certificate_id)

    if mapped_filename:
        image_path = os.path.join(
            REFERENCE_DIR,
            mapped_filename
        )

        if os.path.exists(image_path):
            return image_path

    # 2. Existing ID-based files.
    for extension in [
        ".jpeg",
        ".jpg",
        ".png"
    ]:
        image_path = os.path.join(
            REFERENCE_DIR,
            certificate_id + extension
        )

        if os.path.exists(image_path):
            return image_path

    # 3. Dynamic registration in JSON.
    references = _load_references()

    for stored_id, record in references.items():
        if not isinstance(record, dict):
            continue

        record_id = str(
            record.get("certificate_id", "")
        ).strip()

        if stored_id == certificate_id or record_id == certificate_id:
            reference_image = str(
                record.get("reference_image", "")
            ).strip()

            if not reference_image:
                continue

            # Only allow a basename so the JSON cannot escape the
            # trusted reference directory.
            reference_name = os.path.basename(reference_image)
            image_path = os.path.join(
                REFERENCE_DIR,
                reference_name
            )

            if os.path.exists(image_path):
                return image_path

    return None


def get_name_region(certificate_id: str):
    """Return configured name region, if one exists."""

    if not certificate_id:
        return None

    return NAME_REGION_MAP.get(
        str(certificate_id).strip()
    )


def list_reference_images():
    """Return available trusted certificate reference images."""

    if not os.path.exists(REFERENCE_DIR):
        return []

    images = []

    for filename in os.listdir(REFERENCE_DIR):
        lower = filename.lower()

        if not lower.endswith(
            (".jpeg", ".jpg", ".png")
        ):
            continue

        if lower.startswith("debug_"):
            continue

        if lower.startswith("aligned_"):
            continue

        if lower.startswith("_"):
            continue

        images.append(
            os.path.join(
                REFERENCE_DIR,
                filename
            )
        )

    return sorted(images)


if __name__ == "__main__":
    print("Reference directory:", REFERENCE_DIR)
    print("C1:", get_reference_image("A1465289"))
    print("C3:", get_reference_image("1PE10EC038"))
    print("C4:", get_reference_image("MITU18DSME0016"))
