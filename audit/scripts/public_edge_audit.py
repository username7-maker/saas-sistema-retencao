"""Low-rate, unauthenticated observation of the fixed published Cordex edge."""

from __future__ import annotations

import hashlib
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


FRONTEND = "https://saas-frontend-pearl.vercel.app"
API = "https://ai-gym-os-api-production.up.railway.app"
ALLOWED_HOSTS = {"saas-frontend-pearl.vercel.app", "ai-gym-os-api-production.up.railway.app"}
SAFE_HEADERS = {
    "cache-control",
    "content-security-policy",
    "content-type",
    "cross-origin-opener-policy",
    "permissions-policy",
    "referrer-policy",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "x-vercel-cache",
    "access-control-allow-origin",
    "access-control-allow-methods",
    "access-control-allow-credentials",
}


def _guard(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise RuntimeError("Public audit target is outside the fixed allowlist")


def _request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, limit: int = 1_500_000) -> dict:
    _guard(url)
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "Cordex-Safe-Audit/1.0", **(headers or {})})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(limit)
            status = response.status
            response_headers = response.headers
    except urllib.error.HTTPError as exc:
        body = exc.read(limit)
        status = exc.code
        response_headers = exc.headers
    elapsed = round((time.perf_counter() - started) * 1000)
    return {
        "status": status,
        "elapsed_ms": elapsed,
        "bytes_read": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "headers": {key.lower(): value for key, value in response_headers.items() if key.lower() in SAFE_HEADERS},
        "body": body,
    }


def _tls(host: str) -> dict:
    context = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=15) as raw:
        with context.wrap_socket(raw, server_hostname=host) as secured:
            certificate = secured.getpeercert()
            return {
                "version": secured.version(),
                "cipher": secured.cipher()[0] if secured.cipher() else None,
                "not_before": certificate.get("notBefore"),
                "not_after": certificate.get("notAfter"),
                "subject_alt_name_count": len(certificate.get("subjectAltName", [])),
            }


def _public_result(result: dict) -> dict:
    return {key: value for key, value in result.items() if key != "body"}


def main() -> None:
    homepage = _request(f"{FRONTEND}/")
    html = homepage["body"].decode("utf-8", errors="replace")
    asset_paths = sorted(set(re.findall(r'(?:src|href)="([^"?#]+\.(?:js|css))', html)))[:8]
    assets = []
    published_routes: set[str] = set()
    source_maps = []
    for asset_path in asset_paths:
        asset_url = urllib.parse.urljoin(FRONTEND, asset_path)
        asset = _request(asset_url)
        body_text = asset["body"].decode("utf-8", errors="replace")
        published_routes.update(
            route
            for route in re.findall(r'path:"(\/[A-Za-z0-9_/:*\-]+)"', body_text)
            if len(route) <= 160
        )
        has_source_mapping_url = "sourceMappingURL=" in body_text
        assets.append({"path": asset_path, **_public_result(asset), "source_mapping_comment": has_source_mapping_url})
        assets[-1]["google_fonts_import"] = "fonts.googleapis.com" in body_text
        map_probe = _request(f"{asset_url}.map", method="HEAD", limit=2048)
        source_maps.append(
            {
                "path": f"{asset_path}.map",
                **_public_result(map_probe),
                "map_content_type": "json" in map_probe["headers"].get("content-type", "").lower(),
            }
        )

    health = _request(f"{API}/health")
    ready = _request(f"{API}/health/ready")
    missing_frontend = _request(f"{FRONTEND}/_audit_nonexistent_20260710")
    missing_api = _request(f"{API}/_audit_nonexistent_20260710")
    allowed_cors = _request(
        f"{API}/health",
        method="OPTIONS",
        headers={"Origin": FRONTEND, "Access-Control-Request-Method": "GET"},
        limit=4096,
    )
    denied_cors = _request(
        f"{API}/health",
        method="OPTIONS",
        headers={"Origin": "https://audit.invalid", "Access-Control-Request-Method": "GET"},
        limit=4096,
    )

    output = {
        "classification": "observation",
        "target": "published-edge",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "unauthenticated low-rate GET/HEAD/OPTIONS only",
        "frontend": _public_result(homepage),
        "api_health": _public_result(health),
        "api_ready": _public_result(ready),
        "tls": {
            "frontend": _tls("saas-frontend-pearl.vercel.app"),
            "api": _tls("ai-gym-os-api-production.up.railway.app"),
        },
        "assets": assets,
        "source_map_probes": source_maps,
        "published_bundle_routes": sorted(published_routes),
        "error_behavior": {
            "frontend_missing": _public_result(missing_frontend),
            "api_missing": _public_result(missing_api),
        },
        "cors": {
            "published_origin": _public_result(allowed_cors),
            "unlisted_origin": _public_result(denied_cors),
        },
        "sensitive_artifacts_recorded": False,
        "limitations": [
            "No authentication, form submission, upload, WebSocket, load, brute force or port scan was performed.",
            "TLS reflects one negotiated handshake, not a full protocol/cipher audit.",
            "Route strings in a bundle do not prove authorization or functional reachability.",
        ],
    }
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
