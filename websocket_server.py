# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import copy
import dataclasses
import enum
import json
import logging
import threading

from scapy.all import conf
from scapy.all import sniff
import websockets

import amongus

loop = asyncio.get_event_loop()


def listener(wsh):
    conf.use_pcap = True
    conf.sniff_promisc = False
    state = amongus.GameState()

    def process_packet(pkt):
        if state.process_packet(pkt):
            asyncio.run_coroutine_threadsafe(
                wsh.broadcast_state(json.dumps(state.asdict())), loop
            )

    logging.info("listener ready")
    sniff(prn=process_packet, filter="udp and (src port 22023 or dst port 22023)")


class WebSocketHandler:
    def __init__(self):
        self.last_state = None
        self.connected = set()

    async def broadcast_state(self, state):
        try:
            await self._broadcast_state_inner(state)
        except:
            logging.exception("broadcast_state failed")

    async def _broadcast_state_inner(self, state):
        if self.last_state == state:
            return
        self.last_state = state
        if not self.connected:
            return
        logging.debug("Broadcasting state to %d", len(self.connected))
        await asyncio.wait([websocket.send(state) for websocket in self.connected])

    async def handle_websocket(self, websocket, path):
        # Register!
        self.connected.add(websocket)
        try:
            if self.last_state:
                await websocket.send(self.last_state)
            while True:
                await asyncio.sleep(10.0)
                await websocket.ping()
        finally:
            self.connected.remove(websocket)


def main():
    logging.basicConfig(level=logging.DEBUG)
    wsh = WebSocketHandler()
    listener_thread = threading.Thread(target=listener, args=[wsh], daemon=True)
    listener_thread.start()
    start_server = websockets.serve(wsh.handle_websocket, "localhost", 8765)
    loop.run_until_complete(start_server)
    logging.info("websocket server ready")
    loop.run_forever()


if __name__ == "__main__":
    main()
