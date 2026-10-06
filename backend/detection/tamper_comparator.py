from certificate_fields import extract_fields


def compare_fields(original: dict, uploaded: dict) -> dict:
    """
    Compare trusted certificate fields with uploaded certificate fields.
    """

    results = {}

    for field in original:
        original_value = original.get(field)
        uploaded_value = uploaded.get(field)

        if original_value is None:
            results[field] = "UNKNOWN"

        elif uploaded_value is None:
            results[field] = "NOT_DETECTED"

        elif str(original_value).strip().lower() == str(uploaded_value).strip().lower():
            results[field] = "MATCH"

        else:
            results[field] = "MODIFIED"

    return results


if __name__ == "__main__":

    original = {
        "student_name": "Tarun Lamani",
        "student_id": "STU001",
        "course": "Bachelor of Engineering",
        "certificate_type": "TEST DEMONSTRATION"
    }

    # Simulate a tampered certificate
    uploaded = {
        "student_name": "Tarun Lamani",
        "student_id": "STU999",
        "course": "Bachelor of Engineering",
        "certificate_type": "TEST DEMONSTRATION"
    }

    result = compare_fields(original, uploaded)

    print("CERTIFICATE TAMPER COMPARISON")
    print("-" * 45)

    for field, status in result.items():
        print(f"{field}: {status}")