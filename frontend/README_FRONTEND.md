# CertChain Frontend

This is a redesigned frontend for the existing CertChain FastAPI backend.

## Files

- `index.html` — page structure
- `style.css` — colorful responsive design
- `script.js` — connects the UI to your existing API

## Backend required

Keep your existing backend running at:

http://localhost:8000

The frontend uses these existing endpoints:

- POST `/issue`
- POST `/verify`
- POST `/revoke/{cert_hash}`
- GET `/health`

## How to run

### Option 1: VS Code Live Server (recommended)

1. Open the `frontend` folder in VS Code.
2. Install/use Live Server.
3. Right-click `index.html`.
4. Choose **Open with Live Server**.
5. Keep the backend running on port 8000.

### Option 2: Open directly

Double-click `index.html`.

Because your FastAPI backend already has CORS enabled, the browser can call `http://localhost:8000`.

## Important

Do not change your backend, Hardhat or IPFS setup just to use this frontend.

Keep:

1. Hardhat node running on `127.0.0.1:8545`
2. IPFS Desktop running
3. FastAPI running on `127.0.0.1:8000`

Then open the frontend.
