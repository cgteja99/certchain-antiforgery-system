console.log("🔥 CERTCHAIN SCRIPT.JS LOADED");

// ==========================================================
// CERTCHAIN FRONTEND SCRIPT
// ==========================================================

const API_BASE = "http://127.0.0.1:8000";

// ==========================================================
// DOM HELPER
// ==========================================================

const $ = (id) => document.getElementById(id);

// ==========================================================
// TOAST
// ==========================================================

function showToast(message) {
    const toast = $("toast");

    if (!toast) return;

    toast.textContent = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

// ==========================================================
// MESSAGE
// ==========================================================

function setMessage(id, message, type = "normal") {
    const el = $(id);

    if (!el) return;

    el.textContent = message;
    el.className = "message " + type;
}

// ==========================================================
// ESCAPE HTML
// ==========================================================

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

// ==========================================================
// SHORTEN LONG TEXT
// ==========================================================

function shorten(value, n = 42) {
    const s = String(value ?? "");

    if (!s) return "—";

    if (s.length <= n) {
        return s;
    }

    const half = Math.floor(n / 2);

    return s.slice(0, half) + "…" + s.slice(-half);
}

// ==========================================================
// CHECK VALUE
// ==========================================================

function checkValue(
    value,
    trueText = "VALID",
    falseText = "NOT VALID"
) {
    if (value === true) {
        return `
            <b class="ok">
                ✓ ${trueText}
            </b>
        `;
    }

    if (value === false) {
        return `
            <b class="no">
                ✕ ${falseText}
            </b>
        `;
    }

    return `
        <b class="neutral">
            — NOT CHECKED
        </b>
    `;
}

// ==========================================================
// READ JSON RESPONSE
// ==========================================================

async function readJsonResponse(res) {
    const text = await res.text();

    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = {
            detail: text
        };
    }

    if (!res.ok) {
        const detail =
            typeof data.detail === "object"
                ? JSON.stringify(data.detail)
                : data.detail || `HTTP ${res.status}`;

        throw new Error(detail);
    }

    return data;
}

// ==========================================================
// UPLOAD HANDLER
// ==========================================================

function bindUpload(
    inputId,
    chooseId,
    dropId,
    nameId
) {
    const input = $(inputId);
    const choose = $(chooseId);
    const drop = $(dropId);
    const name = $(nameId);

    console.log("UPLOAD BIND:", inputId, {
        input: !!input,
        choose: !!choose,
        drop: !!drop,
        name: !!name
    });

    if (!input || !choose) {
        console.warn(
            "Upload elements missing:",
            inputId,
            chooseId
        );

        return;
    }

    // ------------------------------------------------------
    // CHOOSE BUTTON
    // ------------------------------------------------------

    choose.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();

        input.click();
    });

    // ------------------------------------------------------
    // FILE SELECTED
    // ------------------------------------------------------

    input.addEventListener("change", function () {
        if (input.files && input.files.length > 0) {
            const file = input.files[0];

            console.log("Selected file:", file.name);

            if (name) {
                name.textContent = file.name;
            }
        } else {
            if (name) {
                name.textContent = "No file selected";
            }
        }
    });

    // ------------------------------------------------------
    // DRAG AND DROP
    // ------------------------------------------------------

    if (drop) {
        drop.addEventListener("click", function (event) {
            if (event.target.tagName !== "BUTTON") {
                input.click();
            }
        });

        drop.addEventListener("dragover", function (event) {
            event.preventDefault();
            drop.classList.add("dragover");
        });

        drop.addEventListener("dragleave", function () {
            drop.classList.remove("dragover");
        });

        drop.addEventListener("drop", function (event) {
            event.preventDefault();

            drop.classList.remove("dragover");

            const files = event.dataTransfer.files;

            if (!files || files.length === 0) {
                return;
            }

            try {
                const dataTransfer = new DataTransfer();

                for (const file of files) {
                    dataTransfer.items.add(file);
                }

                input.files = dataTransfer.files;
            } catch (error) {
                console.warn(
                    "Could not assign dropped file:",
                    error
                );
            }

            input.dispatchEvent(
                new Event("change")
            );
        });
    }
}

// ==========================================================
// SCROLL
// ==========================================================

function scrollToSection(selector) {
    const section = document.querySelector(selector);

    if (!section) return;

    section.scrollIntoView({
        behavior: "smooth"
    });
}

// ==========================================================
// API HEALTH
// ==========================================================

async function checkApi() {
    try {
        const res = await fetch(
            `${API_BASE}/health`,
            {
                cache: "no-store"
            }
        );

        if (!res.ok) {
            throw new Error(
                "HTTP " + res.status
            );
        }

        const data = await res.json();

        console.log("API HEALTH:", data);

        const apiStatus = $("apiStatus");

        if (apiStatus) {
            apiStatus.textContent = "online";
        }

        const dot = document.querySelector(".dot");

        if (dot) {
            dot.classList.add("online");
        }
    } catch (error) {
        console.error(
            "API HEALTH CHECK FAILED:",
            error
        );

        const apiStatus = $("apiStatus");

        if (apiStatus) {
            apiStatus.textContent = "offline";
        }
    }
}

// ==========================================================
// ISSUE CERTIFICATE
// ==========================================================

async function issueCertificate() {
    const file = $("issueFile")?.files[0];

    const studentId =
        $("studentId")?.value.trim();

    const studentName =
        $("studentName")?.value.trim();

    const course =
        $("course")?.value.trim();

    const btn = $("issueBtn");

    // ------------------------------------------------------
    // VALIDATION
    // ------------------------------------------------------

    if (!file) {
        setMessage(
            "issueMessage",
            "Please choose a certificate image.",
            "error"
        );

        return;
    }

    if (
        !studentId ||
        !studentName ||
        !course
    ) {
        setMessage(
            "issueMessage",
            "Please fill all student details.",
            "error"
        );

        return;
    }

    // ------------------------------------------------------
    // FORM DATA
    // ------------------------------------------------------

    const form = new FormData();

    form.append("file", file);
    form.append("student_id", studentId);
    form.append("student_name", studentName);
    form.append("course", course);

    // ------------------------------------------------------
    // BUTTON
    // ------------------------------------------------------

    if (btn) {
        btn.disabled = true;
        btn.textContent =
            "Issuing on blockchain...";
    }

    setMessage(
        "issueMessage",
        "Uploading, signing and anchoring certificate..."
    );

    try {
        // --------------------------------------------------
        // API REQUEST
        // --------------------------------------------------

        const res = await fetch(
            `${API_BASE}/issue`,
            {
                method: "POST",
                body: form
            }
        );

        console.log(
            "ISSUE HTTP STATUS:",
            res.status
        );

        const data =
            await readJsonResponse(res);

        console.log(
            "ISSUE RESPONSE:",
            data
        );

        // --------------------------------------------------
        // ISSUE RESULT
        // --------------------------------------------------

        const issueResult =
            $("issueResult");

        if (issueResult) {
            issueResult.innerHTML = `
                <div class="verdict authentic">

                    <h3>
                        ✓ Certificate Issued Successfully
                    </h3>

                    <p>
                        ${escapeHtml(
                            data.message ||
                            "Certificate anchored on-chain."
                        )}
                    </p>

                </div>

                <div class="checks">

                    <div class="check">
                        <span>
                            Blockchain Transaction
                        </span>

                        <b class="ok">
                            ✓ SUCCESS
                        </b>
                    </div>

                    <div class="check">
                        <span>
                            Student
                        </span>

                        <b>
                            ${escapeHtml(
                                data.student_name ||
                                studentName
                            )}
                        </b>
                    </div>

                    <div class="check">
                        <span>
                            Student ID
                        </span>

                        <b>
                            ${escapeHtml(
                                data.student_id ||
                                studentId
                            )}
                        </b>
                    </div>

                    <div class="check">
                        <span>
                            Course
                        </span>

                        <b>
                            ${escapeHtml(
                                data.course ||
                                course
                            )}
                        </b>
                    </div>

                    <div class="check">
                        <span>
                            Forgery Pre-check
                        </span>

                        <b class="${
                            data.forgery_check
                                ?.structured_tampering
                                ? "no"
                                : "ok"
                        }">

                            ${
                                data.forgery_check
                                    ?.structured_tampering
                                    ? "✕ TAMPERING"
                                    : "✓ PASSED"
                            }

                        </b>
                    </div>

                </div>

                <div class="details">

                    <div>
                        <span>
                            Certificate Hash
                        </span>

                        <b
                            title="${escapeHtml(
                                data.certificate_hash || ""
                            )}"
                        >
                            ${escapeHtml(
                                shorten(
                                    data.certificate_hash,
                                    54
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        <span>
                            IPFS CID
                        </span>

                        <b
                            title="${escapeHtml(
                                data.ipfs_cid || ""
                            )}"
                        >
                            ${escapeHtml(
                                shorten(
                                    data.ipfs_cid,
                                    54
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        <span>
                            Transaction
                        </span>

                        <b
                            title="${escapeHtml(
                                data.transaction?.tx_hash || ""
                            )}"
                        >
                            ${escapeHtml(
                                shorten(
                                    data.transaction?.tx_hash,
                                    54
                                )
                            )}
                        </b>
                    </div>

                </div>
            `;
        }

        setMessage(
            "issueMessage",
            "Certificate issued successfully.",
            "success"
        );

        showToast(
            "Certificate successfully anchored on-chain."
        );

    } catch (err) {
        console.error(
            "ISSUE ERROR:",
            err
        );

        let message =
            err.message ||
            "Unknown error";

        if (
            message
                .toLowerCase()
                .includes(
                    "certificate already registered"
                )
        ) {
            message =
                "Certificate already registered on blockchain.";
        }

        setMessage(
            "issueMessage",
            "Issue failed: " + message,
            "error"
        );

        showToast(message);

    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent =
                "Issue Certificate";
        }
    }
}

// ==========================================================
// VERIFY CERTIFICATE
// ==========================================================

async function verifyCertificate() {
    console.log(
        "VERIFY FUNCTION STARTED"
    );

    const file =
        $("verifyFile")?.files[0];

    const certificateId =
        $("certificateId")?.value.trim();

    const btn =
        $("verifyBtn");

    // ------------------------------------------------------
    // VALIDATION
    // ------------------------------------------------------

    if (!certificateId) {
        setMessage(
            "verifyMessage",
            "Please enter the certificate ID.",
            "error"
        );

        return;
    }

    if (!file) {
        setMessage(
            "verifyMessage",
            "Please choose a certificate image.",
            "error"
        );

        return;
    }

    // ------------------------------------------------------
    // FORM DATA
    // ------------------------------------------------------

    const form =
        new FormData();

    form.append(
        "file",
        file
    );

    form.append(
        "certificate_id",
        certificateId
    );

    console.log(
        "VERIFY CERTIFICATE ID:",
        certificateId
    );

    console.log(
        "VERIFY FILE:",
        file.name
    );

    // ------------------------------------------------------
    // BUTTON
    // ------------------------------------------------------

    if (btn) {
        btn.disabled = true;
        btn.textContent =
            "Verifying...";
    }

    setMessage(
        "verifyMessage",
        "Finding trusted reference, analysing image and checking blockchain..."
    );

    try {
        // --------------------------------------------------
        // API REQUEST
        // --------------------------------------------------

        const res =
            await fetch(
                `${API_BASE}/verify`,
                {
                    method: "POST",
                    body: form
                }
            );

        console.log(
            "VERIFY HTTP STATUS:",
            res.status
        );

        const data =
            await readJsonResponse(res);

        console.log(
            "VERIFY RESPONSE:",
            data
        );

        // ==================================================
        // WRONG DETAILS
        // ==================================================

        if (
            data.overall_verdict &&
            data.overall_verdict.startsWith(
                "WRONG DETAILS"
            )
        ) {
            console.log(
                "⚠️ WRONG DETAILS DETECTED"
            );

            const result =
                $("verifyResult");

            // Clear previous result
            if (result) {
                result.innerHTML = "";
            }

            // Show only message below button
            setMessage(
                "verifyMessage",
                "WRONG DETAILS - uploaded certificate does not belong to the supplied certificate ID.",
                "error"
            );

            showToast(
                "Wrong certificate ID and certificate image."
            );

            return;
        }

        // ==================================================
        // VERDICT
        // ==================================================

        const verdict =
            data.overall_verdict ||
            "UNKNOWN";

        // ==================================================
        // BASIC VERIFICATION VALUES
        // ==================================================

        const hashFound =
            data.hash_found_onchain === true;

        const signatureValid =
            data.signature_valid === true;

        const notRevoked =
            data.revoked === false;

        const structuredTampering =
            data.forgery_check
                ?.structured_tampering === true;

        // ==================================================
        // INVALID
        // ==================================================

        const isInvalid =
            !structuredTampering &&
            verdict.startsWith("INVALID");

        // ==================================================
        // VISUALLY VERIFIED
        // ==================================================

        const isVisuallyVerified =
            !isInvalid &&
            verdict.startsWith(
                "VISUALLY VERIFIED"
            );

        // ==================================================
        // REVOKED
        // ==================================================

        const isRevoked =
            !isInvalid &&
            (
                data.revoked === true ||
                verdict.startsWith("REVOKED")
            );

        // ==================================================
        // AUTHENTIC
        // ==================================================

        const isAuthentic =
            !isInvalid &&
            !isVisuallyVerified &&
            !isRevoked &&
            hashFound &&
            signatureValid &&
            notRevoked &&
            !structuredTampering;

        // ==================================================
        // FORGED
        // ==================================================

        const isForged =
            !isInvalid &&
            !isVisuallyVerified &&
            !isRevoked &&
            !isAuthentic &&
            structuredTampering;

        // ==================================================
        // VERDICT CLASS
        // ==================================================

        const verdictClass =
            isAuthentic
                ? "authentic"
                : isVisuallyVerified
                    ? "visually-verified"
                    : isRevoked
                        ? "revoked"
                        : "bad";

        // ==================================================
        // VERDICT ICON
        // ==================================================

        const icon =
            isAuthentic
                ? "✓"
                : isVisuallyVerified
                    ? "⚠"
                    : isRevoked
                        ? "⚠"
                        : isForged
                            ? "✕"
                            : "⚠";

        // ==================================================
        // FORGERY DATA
        // ==================================================

        const forgery =
            data.forgery_check || {};

        const student =
            forgery.student_name || {};

        const registerNumber =
            forgery.register_number || {};

        const signature =
            forgery.signature || {};



        const signatureList =
            Array.isArray(signature.signatures)
                ? signature.signatures
                : [];
        
        const tamperedSignatureCount =
            signatureList.filter(
                sig => sig.status === "TAMPERED"
            ).length;

        console.log("🔥 SIGNATURE LIST COUNT:", signatureList.length);
        console.log("🔥 SIGNATURE LIST:", signatureList);

        const seal =
            forgery.seal || {};

        // ==================================================
        // RESULT ELEMENT
        // ==================================================

        const result =
            $("verifyResult");

        if (!result) {
            throw new Error(
                "verifyResult element not found in index.html"
            );
        }

        // ==================================================
        // RESULT PANEL
        // ==================================================

        result.innerHTML = `

            <!-- VERDICT -->

            <div class="verdict ${verdictClass}">

                <h3>

                    ${icon}

                    ${
                        isAuthentic
                            ? "AUTHENTIC"
                            : isVisuallyVerified
                                ? "VISUALLY VERIFIED"
                                : isRevoked
                                    ? "REVOKED"
                                    : isForged
                                        ? "FORGED / ALTERED"
                                        : "INVALID"
                    }

                </h3>

                <p>

                    ${escapeHtml(
                        isForged
                            ? "FORGED / ALTERED - certificate image tampering was detected."
                            : verdict
                    )}

                </p>

            </div>


            <!-- MAIN CHECKS -->

            <div class="checks">

                <!-- Certificate ID -->

                <div class="check">

                    <span>
                        Certificate ID
                    </span>

                    <b>
                        ${escapeHtml(
                            certificateId
                        )}
                    </b>

                </div>


                <!-- Trusted Reference -->

                <div class="check">

                    <span>
                        Trusted Reference
                    </span>

                    ${
                        forgery.reference_used
                            ? `
                                <b class="ok">
                                    ✓ FOUND
                                </b>
                            `
                            : `
                                <b class="no">
                                    ✕ NOT FOUND
                                </b>
                            `
                    }

                </div>


                <!-- Blockchain Hash -->

                <div class="check">

                    <span>
                        Blockchain Hash
                    </span>

                    ${
                        data.hash_found_onchain === true
                            ? `
                                <b class="ok">
                                    ✓ FOUND ON-CHAIN
                                </b>
                            `
                            : `
                                <b class="no">
                                    ✕ NOT FOUND
                                </b>
                            `
                    }

                </div>


                <!-- Digital Signature -->

                <div class="check">

                    <span>
                        Digital Signature
                    </span>

                    ${
                        data.signature_valid === true
                            ? `
                                <b class="ok">
                                    ✓ VALID
                                </b>
                            `
                            : data.signature_valid === false
                                ? `
                                    <b class="no">
                                        ✕ INVALID
                                    </b>
                                `
                                : `
                                    <b class="neutral">
                                        — NOT APPLICABLE
                                    </b>
                                `
                    }

                </div>


                <!-- Revocation -->

                <div class="check">

                    <span>
                        Revocation
                    </span>

                    ${
                        data.revoked === false
                            ? `
                                <b class="ok">
                                    ✓ NOT REVOKED
                                </b>
                            `
                            : data.revoked === true
                                ? `
                                    <b class="warn">
                                        ⚠ REVOKED
                                    </b>
                                `
                                : `
                                    <b class="neutral">
                                        — NOT FOUND
                                    </b>
                                `
                    }

                </div>


                <!-- Register Number -->

                <div class="check">

                    <span>
                        Register Number
                    </span>

                    ${
                        registerNumber.status === "MATCH"
                            ? `
                                <b class="ok">
                                    ✓ MATCH
                                </b>
                            `
                            : registerNumber.status === "TAMPERED"
                                ? `
                                    <b class="no">
                                        ✕ TAMPERED
                                    </b>
                                `
                                : `
                                    <b class="neutral">
                                        — NOT AVAILABLE
                                    </b>
                                `
                    }

                </div>


                <!-- Structured Tampering -->

                <div class="check">

                    <span>
                        Structured Tampering
                    </span>

                    ${
                        forgery.structured_tampering
                            ? `
                                <b class="no">
                                    ✕ DETECTED
                                </b>
                            `
                            : `
                                <b class="ok">
                                    ✓ NOT DETECTED
                                </b>
                            `
                    }

                </div>

            </div>


            <!-- DETAILS -->

            <div class="details">

                <!-- Student Name -->

                <div>

                    <span>
                        Student Name
                    </span>

                    <b class="${
                        student.status === "TAMPERED"
                            ? "no"
                            : "ok"
                    }">

                        ${
                            student.status === "TAMPERED"
                                ? "✕ TAMPERED"
                                : "✓ MATCH"
                        }

                    </b>

                </div>


                <!-- ALL SIGNATURES -->

                <!-- SIGNATURE SUMMARY -->

                <div>

                    <span>
                        Signature
                    </span>

                    <b class="${
                        tamperedSignatureCount > 0
                            ? "no"
                            : signatureList.length > 0
                                ? "ok"
                                : "neutral"
                    }">

                        ${
                            tamperedSignatureCount > 0
                                ? "✕ TAMPERED"
                                : signatureList.length > 0
                                    ? "✓ MATCH"
                                    : "— NOT AVAILABLE"
                        }

                    </b>

                </div>


                <!-- Seal -->

                <div>

                    <span>
                        Seal
                    </span>

                    <b class="${
                        seal.status === "TAMPERED"
                            ? "no"
                            : "ok"
                    }">

                        ${
                            seal.status === "TAMPERED"
                                ? "✕ TAMPERED"
                                : "✓ MATCH"
                        }

                    </b>

                </div>


                <!-- Register Number -->

                <div>

                    <span>
                        Register Number
                    </span>

                    <b class="${
                        registerNumber.status === "TAMPERED"
                            ? "no"
                            : registerNumber.status === "MATCH"
                                ? "ok"
                                : "neutral"
                    }">

                        ${
                            registerNumber.status === "TAMPERED"
                                ? "✕ TAMPERED"
                                : registerNumber.status === "MATCH"
                                    ? "✓ MATCH"
                                    : "— NOT AVAILABLE"
                        }

                    </b>

                </div>


                <!-- Forgery Score -->

                <div>

                    <span>
                        Forgery Score
                    </span>

                    <b>
                        ${
                            Number(
                                forgery.forgery_score ?? 0
                            ).toFixed(4)
                        }
                    </b>

                </div>


                <!-- Threshold -->

                <div>

                    <span>
                        Threshold
                    </span>

                    <b>
                        ${
                            Number(
                                forgery.threshold ?? 0
                            ).toFixed(2)
                        }
                    </b>

                </div>


                <!-- Issuer -->

                <div>

                    <span>
                        Issuer
                    </span>

                    <b
                        title="${escapeHtml(
                            data.issuer || ""
                        )}"
                    >
                        ${escapeHtml(
                            shorten(
                                data.issuer || "—",
                                54
                            )
                        )}
                    </b>

                </div>


                <!-- IPFS CID -->

                <div>

                    <span>
                        IPFS CID
                    </span>

                    <b
                        title="${escapeHtml(
                            data.ipfs_cid || ""
                        )}"
                    >
                        ${escapeHtml(
                            shorten(
                                data.ipfs_cid || "—",
                                54
                            )
                        )}
                    </b>

                </div>


                <!-- Issued At -->

                <div>

                    <span>
                        Issued At
                    </span>

                    <b>

                        ${
                            data.issued_at
                                ? new Date(
                                    data.issued_at * 1000
                                ).toLocaleDateString()
                                : "—"
                        }

                    </b>

                </div>

            </div>
        `;

        // ==================================================
        // NORMAL MESSAGE
        // ==================================================

        setMessage(
            "verifyMessage",
            "Verification completed.",
            "success"
        );

        // ==================================================
        // TOAST
        // ==================================================

        if (isAuthentic) {
            showToast(
                "Certificate is authentic."
            );
        } else if (isRevoked) {
            showToast(
                "Certificate is revoked."
            );
        } else if (isVisuallyVerified) {
            showToast(
                "Certificate visually verified."
            );
        } else if (isForged) {
            showToast(
                "Certificate is forged or altered."
            );
        } else {
            showToast(
                "Certificate verification completed."
            );
        }

    } catch (err) {
        console.error(
            "VERIFY ERROR:",
            err
        );

        setMessage(
            "verifyMessage",
            "Verification failed: " +
                (err.message || "Unknown error"),
            "error"
        );

        showToast(
            "Verification request failed."
        );

    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent =
                "Verify Certificate";
        }
    }
}

// ==========================================================
// REVOKE CERTIFICATE
// ==========================================================

async function revokeCertificate() {
    const hash =
        $("revokeHash")?.value.trim();

    const btn =
        $("revokeBtn");

    // ------------------------------------------------------
    // VALIDATION
    // ------------------------------------------------------

    if (!hash) {
        setMessage(
            "revokeMessage",
            "Enter the certificate hash.",
            "error"
        );

        return;
    }

    // ------------------------------------------------------
    // BUTTON
    // ------------------------------------------------------

    if (btn) {
        btn.disabled = true;
        btn.textContent =
            "Revoking...";
    }

    setMessage(
        "revokeMessage",
        "Submitting revocation transaction..."
    );

    try {
        // --------------------------------------------------
        // API REQUEST
        // --------------------------------------------------

        const res =
            await fetch(
                `${API_BASE}/revoke/${encodeURIComponent(hash)}`,
                {
                    method: "POST"
                }
            );

        const data =
            await readJsonResponse(res);

        console.log(
            "REVOKE RESPONSE:",
            data
        );

        // --------------------------------------------------
        // RESULT
        // --------------------------------------------------

        const revokeResult =
            $("revokeResult");

        if (revokeResult) {
            revokeResult.innerHTML = `
                <div class="verdict ${
                    data.status === "success"
                        ? "revoked"
                        : "bad"
                }">

                    <h3>

                        ${
                            data.status === "success"
                                ? "✓ Certificate Revoked"
                                : "✕ Revocation Failed"
                        }

                    </h3>

                    <p>
                        Blockchain transaction status:
                        ${escapeHtml(
                            data.status || "unknown"
                        )}
                    </p>

                </div>

                <div class="details">

                    <div>

                        <span>
                            Transaction Hash
                        </span>

                        <b>
                            ${escapeHtml(
                                data.tx_hash ||
                                "N/A"
                            )}
                        </b>

                    </div>

                </div>
            `;
        }

        setMessage(
            "revokeMessage",
            "Revocation completed.",
            "success"
        );

        showToast(
            "Certificate revocation submitted."
        );

    } catch (err) {
        console.error(
            "REVOKE ERROR:",
            err
        );

        setMessage(
            "revokeMessage",
            "Revocation failed: " +
                (err.message || "Unknown error"),
            "error"
        );

        showToast(
            "Revocation failed."
        );

    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent =
                "Revoke Certificate";
        }
    }
}

// ==========================================================
// INITIALIZATION
// ==========================================================

function initializeCertChain() {

    console.log(
        "🚀 Initializing CertChain..."
    );

    // ------------------------------------------------------
    // SCROLL BUTTONS
    // ------------------------------------------------------

    document
        .querySelectorAll("[data-scroll]")
        .forEach((btn) => {

            btn.addEventListener(
                "click",
                () => {
                    scrollToSection(
                        btn.dataset.scroll
                    );
                }
            );

        });

    // ------------------------------------------------------
    // UPLOADS
    // ------------------------------------------------------

    bindUpload(
        "issueFile",
        "issueChoose",
        "issueDrop",
        "issueFileName"
    );

    bindUpload(
        "verifyFile",
        "verifyChoose",
        "verifyDrop",
        "verifyFileName"
    );

    // ------------------------------------------------------
    // BUTTONS
    // ------------------------------------------------------

    const issueBtn =
        $("issueBtn");

    const verifyBtn =
        $("verifyBtn");

    const revokeBtn =
        $("revokeBtn");

    if (issueBtn) {
        issueBtn.onclick =
            issueCertificate;

        console.log(
            "✓ ISSUE BUTTON CONNECTED"
        );
    } else {
        console.warn(
            "Issue button not found."
        );
    }

    if (verifyBtn) {
        verifyBtn.onclick =
            verifyCertificate;

        console.log(
            "✓ VERIFY BUTTON CONNECTED"
        );
    } else {
        console.warn(
            "Verify button not found."
        );
    }

    if (revokeBtn) {
        revokeBtn.onclick =
            revokeCertificate;

        console.log(
            "✓ REVOKE BUTTON CONNECTED"
        );
    }

    // ------------------------------------------------------
    // API CHECK
    // ------------------------------------------------------

    checkApi();

    setInterval(
        checkApi,
        15000
    );

    console.log(
        "✅ CertChain initialization complete."
    );
}

// ==========================================================
// START ONLY AFTER HTML IS READY
// ==========================================================

if (document.readyState === "loading") {

    document.addEventListener(
        "DOMContentLoaded",
        initializeCertChain
    );

} else {

    initializeCertChain();

}