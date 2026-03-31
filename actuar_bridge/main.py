from __future__ import annotations

import argparse
import json
from pathlib import Path

from actuar_bridge.bridge_client import BridgeClient
from actuar_bridge.executor import AttachedActuarBrowserExecutor, DryRunBridgeExecutor
from actuar_bridge.relay import ExtensionRelayService, ExtensionRelayState
from actuar_bridge.runner import ActuarBridgeRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Actuar Bridge local para AI GYM OS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pair_parser = subparsers.add_parser("pair", help="Parear esta estacao com o AI GYM OS")
    pair_parser.add_argument("--api-base-url", required=True)
    pair_parser.add_argument("--pairing-code", required=True)
    pair_parser.add_argument("--device-name", required=True)
    pair_parser.add_argument("--bridge-version", default="0.1.0")
    pair_parser.add_argument("--browser-name", default="Chrome")
    pair_parser.add_argument("--token-file", default=".actuar-bridge-token.json")

    run_parser = subparsers.add_parser("run", help="Rodar o loop da ponte local")
    run_parser.add_argument("--api-base-url", required=True)
    run_parser.add_argument("--device-token", default="")
    run_parser.add_argument("--token-file", default=".actuar-bridge-token.json")
    run_parser.add_argument("--mode", choices=["dry-run", "attached-browser", "extension-relay"], default="dry-run")
    run_parser.add_argument("--debug-url", default="http://127.0.0.1:9222")
    run_parser.add_argument("--page-url-hint", default="actuar")
    run_parser.add_argument("--listen-host", default="127.0.0.1")
    run_parser.add_argument("--listen-port", type=int, default=44777)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "pair":
        payload = BridgeClient(api_base_url=args.api_base_url).pair(
            pairing_code=args.pairing_code,
            device_name=args.device_name,
            bridge_version=args.bridge_version,
            browser_name=args.browser_name,
        )
        Path(args.token_file).write_text(
            json.dumps(
                {
                    "api_base_url": args.api_base_url,
                    "device_token": payload["device_token"],
                    "device": payload["device"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Estacao pareada com sucesso. Token salvo em {args.token_file}.")
        return

    device_token = args.device_token or _load_token(args.token_file)
    client = BridgeClient(api_base_url=args.api_base_url, device_token=device_token)
    if args.mode == "extension-relay":
        state = ExtensionRelayState(client=client)
        service = ExtensionRelayService(state=state, host=args.listen_host, port=args.listen_port)
        service.run_forever()
        return

    executor = (
        DryRunBridgeExecutor()
        if args.mode == "dry-run"
        else AttachedActuarBrowserExecutor(debug_url=args.debug_url, page_url_hint=args.page_url_hint)
    )
    runner = ActuarBridgeRunner(client=client, executor=executor)
    runner.run_forever()


def _load_token(token_file: str) -> str:
    payload = json.loads(Path(token_file).read_text(encoding="utf-8"))
    return payload["device_token"]


if __name__ == "__main__":
    main()
