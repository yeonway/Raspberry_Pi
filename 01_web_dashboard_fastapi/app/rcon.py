import os
import socket
import struct
from typing import Iterable


SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0


class RconError(RuntimeError):
    pass


def rcon_host() -> str:
    return os.getenv("MINECRAFT_RCON_HOST", "127.0.0.1").strip() or "127.0.0.1"


def rcon_port() -> int:
    try:
        return int(os.getenv("MINECRAFT_RCON_PORT", "25575"))
    except ValueError:
        return 25575


def rcon_password() -> str:
    return os.getenv("MINECRAFT_RCON_PASSWORD", "").strip()


def rcon_timeout() -> float:
    try:
        return max(1.0, float(os.getenv("MINECRAFT_RCON_TIMEOUT_SECONDS", "10")))
    except ValueError:
        return 10.0


def rcon_configured() -> bool:
    return bool(rcon_password())


def _packet(request_id: int, packet_type: int, payload: str) -> bytes:
    payload_bytes = payload.encode("utf-8")
    body = struct.pack("<ii", request_id, packet_type) + payload_bytes + b"\x00\x00"
    return struct.pack("<i", len(body)) + body


def _read_packet(sock: socket.socket) -> tuple[int, int, str]:
    length_data = _read_exact(sock, 4)
    (length,) = struct.unpack("<i", length_data)
    body = _read_exact(sock, length)
    request_id, packet_type = struct.unpack("<ii", body[:8])
    payload = body[8:-2].decode("utf-8", errors="replace")
    return request_id, packet_type, payload


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RconError("RCON connection closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_rcon_command(command: str) -> str:
    password = rcon_password()
    if not password:
        raise RconError("MINECRAFT_RCON_PASSWORD is not configured")

    with socket.create_connection((rcon_host(), rcon_port()), timeout=rcon_timeout()) as sock:
        sock.settimeout(rcon_timeout())
        sock.sendall(_packet(1, SERVERDATA_AUTH, password))
        auth_id, _, _ = _read_packet(sock)
        if auth_id == -1:
            raise RconError("RCON authentication failed")

        sock.sendall(_packet(2, SERVERDATA_EXECCOMMAND, command))
        _, packet_type, payload = _read_packet(sock)
        if packet_type not in {SERVERDATA_RESPONSE_VALUE, SERVERDATA_EXECCOMMAND}:
            raise RconError(f"Unexpected RCON packet type: {packet_type}")
        return payload


def send_chat_lines(prefix: str, player_name: str, answer: str) -> Iterable[str]:
    clean_answer = " ".join((answer or "").split())
    if not clean_answer:
        clean_answer = "(empty answer)"

    label = f"{prefix} {player_name}: ".strip()
    max_len = 220
    sent = []

    for start in range(0, len(clean_answer), max_len):
        chunk = clean_answer[start : start + max_len]
        command = f"say {label}{chunk}"
        sent.append(send_rcon_command(command))

    return sent
