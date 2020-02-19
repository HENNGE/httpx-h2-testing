import asyncio
import os
import random
import ssl
import sys
import tempfile
from dataclasses import dataclass
from functools import partial
from typing import *

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import DataReceived, RequestReceived, StreamEnded

from .certs import make_cert_and_key


class Stats:
    active_conn = 0
    total_conn = 0
    max_conn = 0
    active_req = 0
    total_req = 0
    max_req = 0

    def print(self):
        sys.stdout.write(
            f"\rAC: {self.active_conn} | TC: {self.total_conn} | MC: {self.max_conn} | AR: {self.active_req} | TR: {self.total_req} | MR: {self.max_req}                  "
        )
        sys.stdout.flush()

    def add_connection(self):
        self.active_conn += 1
        self.total_conn += 1
        self.max_conn = max(self.active_conn, self.max_conn)
        self.print()

    def remove_connection(self):
        self.active_conn -= 1
        self.print()

    def start_request(self):
        self.active_req += 1
        self.total_req += 1
        self.max_req = max(self.active_req, self.max_req)
        self.print()

    def end_request(self):
        self.active_req -= 1
        self.print()


STATS = Stats()

Headers = List[Tuple[bytes, bytes]]


@dataclass
class Response:
    headers: Headers
    body: Optional[bytes] = None


@dataclass
class Request:
    headers: Headers
    body: bytes = b""


async def handler(request: Request, delay: float) -> Response:
    headers = dict(request.headers)
    status = b"405" if headers[b":method"] != b"POST" else b"200"
    await asyncio.sleep(delay)
    return Response([(b":status", status), (b"content-length", b"0"),], b"",)


def drain(conn: H2Connection, into: asyncio.Transport):
    to_send = conn.data_to_send()
    if to_send:
        into.write(to_send)


class H2Protocol(asyncio.Protocol):
    def __init__(self, min_delay: float, max_delay: float):
        self.conn = H2Connection(H2Configuration(client_side=False))
        self.requests = {}
        self.transport: asyncio.Transport
        self.min_delay = min_delay
        self.max_delay = max_delay

    def connection_made(self, transport: asyncio.Transport):
        STATS.add_connection()
        self.transport = transport
        self.conn.initiate_connection()
        drain(self.conn, self.transport)

    def connection_lost(self, exc):
        STATS.remove_connection()

    def data_received(self, data):
        events = self.conn.receive_data(data)
        for event in events:
            if isinstance(event, RequestReceived):
                STATS.start_request()
                self.requests[event.stream_id] = Request(event.headers)
            elif isinstance(event, DataReceived):
                self.requests[event.stream_id].body += data
            elif isinstance(event, StreamEnded):
                task = asyncio.get_event_loop().create_task(
                    handler(
                        self.requests.pop(event.stream_id),
                        random.uniform(self.min_delay, self.max_delay),
                    )
                )

                def done(task):
                    try:
                        response = task.result()
                        self.conn.send_headers(event.stream_id, response.headers)
                        if response.body:
                            self.conn.send_data(event.stream_id, response.body)
                    finally:
                        self.conn.end_stream(event.stream_id)
                        drain(self.conn, self.transport)
                        STATS.end_request()

                task.add_done_callback(done)
        drain(self.conn, self.transport)


async def run_server(port: int, min_delay: float, max_delay: float):
    cert, key = make_cert_and_key()
    with tempfile.TemporaryDirectory() as workspace:
        cert_path = os.path.join(workspace, "cert.pem")
        key_path = os.path.join(workspace, "key.pem")
        with open(cert_path, "wb") as fobj:
            fobj.write(cert.public_bytes(Encoding.PEM))
        with open(key_path, "wb") as fobj:
            fobj.write(
                key.private_bytes(
                    Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
                )
            )
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        ssl_context.set_alpn_protocols(["h2"])
        server = await asyncio.get_event_loop().create_server(
            partial(H2Protocol, min_delay, max_delay),
            "localhost",
            port,
            ssl=ssl_context,
        )
        STATS.print()
        await server.serve_forever()
