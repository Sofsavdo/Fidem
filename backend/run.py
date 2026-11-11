"""Start the API listening on BOTH IPv4 and IPv6 (separate sockets).

Railway's private network resolves service names to IPv6 addresses
(`<service>.railway.internal`), while the public edge and healthchecks reach
the container over IPv4. `uvicorn --host 0.0.0.0` only serves IPv4 and
`--host ::` depends on the OS dual-stack default, so bind each family
explicitly and hand both sockets to uvicorn.

Start command:  python run.py
"""
import os
import socket

import uvicorn


def _bind(family: int, host: str, port: int) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if family == socket.AF_INET6:
        # IPv6 socket only serves IPv6, so it can't clash with the IPv4 one.
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.bind((host, port))
    sock.set_inheritable(True)
    return sock


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    app = os.environ.get("UVICORN_APP", "server:app")
    sockets = [_bind(socket.AF_INET, "0.0.0.0", port)]
    try:
        sockets.append(_bind(socket.AF_INET6, "::", port))
    except OSError as exc:  # host without IPv6: IPv4 alone is still fine
        print(f"IPv6 listener unavailable, serving IPv4 only: {exc}", flush=True)
    config = uvicorn.Config(app, log_level="info")
    uvicorn.Server(config).run(sockets=sockets)


if __name__ == "__main__":
    main()
