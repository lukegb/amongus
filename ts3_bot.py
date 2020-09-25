# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import dataclasses
import multiprocessing
import queue
import threading
import time
from typing import FrozenSet, List

from absl import app
from absl import flags
from absl import logging
import scapy.all
import ts3

import amongus.rpcs
import amongus.state_tracker

FLAGS = flags.FLAGS
flags.DEFINE_string(
    "connection_string",
    None,
    "py-ts3 connection string (e.g. ssh://serveradmin:foooo@localhost:10022)",
)
flags.DEFINE_integer("server_id", 1, "Server ID of virtual server to use.")
flags.DEFINE_integer(
    "main_channel_id", 62, "Main channel ID (for people who are alive, etc.)"
)
flags.DEFINE_integer("dead_channel_id", 65, "Dead channel ID (for people who are dead)")
flags.DEFINE_integer("alive_server_group", 25, "Server group to add alive people to")
flags.DEFINE_integer("dead_server_group", 24, "Server group to add dead people to")
# flags.DEFINE_integer("observer_server_group", 11, "Server group to treat as observers")
flags.DEFINE_integer(
    "round_live_talk_power", 300, "Talk power to set main channel to during rounds"
)
flags.DEFINE_integer(
    "round_discuss_talk_power",
    200,
    "Talk power to set main channel to during discussion time",
)
flags.DEFINE_integer(
    "game_dead_talk_power",
    0,
    "Talk power to set main channel to when game isn't happening",
)
flags.DEFINE_integer(
    "keepalive_interval_seconds",
    60,
    "Interval between sending TS3 serverquery keepalives",
)


class UsernameDatabase:
    def __init__(self, data):
        self.usernames_to_ts3_db_ids = {}
        self.ts3_db_ids_to_usernames = {}
        for usernames, client_ids in data:
            for username in usernames:
                self.usernames_to_ts3_db_ids[username] = list(client_ids)
            for client_id in client_ids:
                self.ts3_db_ids_to_usernames[client_id] = list(usernames)

    def usernames_from_db_id(self, db_id):
        return self.ts3_db_ids_to_usernames.get(db_id, [])

    def db_ids_from_username(self, username):
        return self.usernames_to_ts3_db_ids.get(username, [])


USERNAME_DB = UsernameDatabase(
    [
        (("Memories",), (240,)),
        (("Zenras", "Giblets", "Stelbig"), (279,)),
        (("Mumfrey",), (112,)),
        (("SilvaJ",), (199,)),
        (("th0rney",), (146,)),
        (("HDWolfGamer",), (276,)),
        (("lukegb",), (164,)),
        (
            ("felltir",),
            (
                205,
                243,
            ),
        ),
        (
            ("NSE",),
            (
                171,
                177,
                288,
            ),
        ),
        (
            ("Rosalyan",),
            (
                174,
                269,
            ),
        ),
        (("BrackishBrit",), (168,)),
        (
            ("sirrambod",),
            (
                122,
                155,
                178,
            ),
        ),
        (("Echo",), (302,)),
    ]
)


@dataclasses.dataclass(frozen=True, eq=True)
class GameState:
    round_state: amongus.state_tracker.RoundState = (
        amongus.state_tracker.RoundState.LOBBY
    )
    alive_players: FrozenSet[str] = dataclasses.field(default_factory=frozenset)
    dead_players: FrozenSet[str] = dataclasses.field(default_factory=frozenset)


@dataclasses.dataclass(frozen=True)
class TS3Client:
    client_name: str
    client_id: int
    client_database_id: int
    channel_id: int
    server_groups: List[int]


class TS3Bot:
    def __init__(self, ts3conn, queue):
        self.ts3conn = ts3conn
        self.queue = queue
        self.last_keepalive = None
        self.state = GameState()

    def send_keepalive_if_needed(self):
        now = time.monotonic()
        if (
            self.last_keepalive is not None
            and (now - self.last_keepalive) < FLAGS.keepalive_interval_seconds
        ):
            return
        logging.info("Sending TS3 serverquery keepalive")
        self.last_keepalive = now
        self.ts3conn.send_keepalive()

    def online_clients(self):
        online_clients = []
        for client in self.ts3conn.exec_("clientlist", "groups").parsed:
            if client["client_type"] != "0":
                continue
            online_clients.append(
                TS3Client(
                    client_name=client["client_nickname"],
                    client_id=int(client["clid"]),
                    client_database_id=int(client["client_database_id"]),
                    channel_id=int(client["cid"]),
                    server_groups=frozenset(
                        int(n) for n in client["client_servergroups"].split(",")
                    ),
                )
            )
        return online_clients

    @classmethod
    def _lowercase_names(cls, names):
        return (n.lower() for n in names)

    @classmethod
    def _is_player_in_list(cls, client, player_names):
        return any(
            (un in cls._lowercase_names(player_names))
            for un in cls._lowercase_names(
                USERNAME_DB.usernames_from_db_id(client.client_database_id)
            )
        )

    def sync_server_group_with_list(self, sgid, player_names, online_clients):
        current_clients = set()
        for client in online_clients:
            if sgid in client.server_groups:
                current_clients.add(client)

        want_clients = set()
        for client in online_clients:
            if self._is_player_in_list(client, player_names):
                want_clients.add(client)

        modified_database_ids = set()
        to_add = want_clients - current_clients
        to_remove = current_clients - want_clients
        for client in to_add:
            logging.info("Adding %s to server group %d", str(client), sgid)
            if client.client_database_id in modified_database_ids:
                continue
            modified_database_ids.add(client.client_database_id)
            self.ts3conn.exec_(
                "servergroupaddclient", sgid=sgid, cldbid=client.client_database_id
            )
        for client in to_remove:
            logging.info("Removing %s from server group %d", str(client), sgid)
            if client.client_database_id in modified_database_ids:
                continue
            modified_database_ids.add(client.client_database_id)
            self.ts3conn.exec_(
                "servergroupdelclient", sgid=sgid, cldbid=client.client_database_id
            )

    def sync_server_groups(self, online_clients):
        want_alive_players = self.state.alive_players
        want_dead_players = self.state.dead_players
        if self.state.round_state in (
            amongus.state_tracker.RoundState.LOBBY,
            amongus.state_tracker.RoundState.POSTGAME,
        ):
            want_alive_players = []
            want_dead_players = []
        self.sync_server_group_with_list(
            FLAGS.alive_server_group,
            self.state.alive_players,
            online_clients,
        )
        self.sync_server_group_with_list(
            FLAGS.dead_server_group, self.state.dead_players, online_clients
        )

    def sync_main_channel_status(self):
        target_channel_topic = self.state.round_state.value
        if self.state.round_state in (
            amongus.state_tracker.RoundState.LOBBY,
            amongus.state_tracker.RoundState.POSTGAME,
        ):
            target_channel_talk_power = FLAGS.game_dead_talk_power
        elif self.state.round_state == amongus.state_tracker.RoundState.MEETING:
            target_channel_talk_power = FLAGS.round_discuss_talk_power
        else:
            target_channel_talk_power = FLAGS.round_live_talk_power
        current_status = self.ts3conn.exec_("channelinfo", cid=FLAGS.main_channel_id)
        current_channel_talk_power = int(
            current_status.parsed[0]["channel_needed_talk_power"]
        )
        current_channel_topic = current_status.parsed[0]["channel_topic"]
        if (
            current_channel_talk_power != target_channel_talk_power
            or current_channel_topic != target_channel_topic
        ):
            logging.info(
                "Updating channel id=%d with talk power=%d and topic=%s",
                FLAGS.main_channel_id,
                target_channel_talk_power,
                target_channel_topic,
            )
            self.ts3conn.exec_(
                "channeledit",
                cid=FLAGS.main_channel_id,
                channel_needed_talk_power=target_channel_talk_power,
                channel_topic=target_channel_topic,
            )

    def _move_people_matching_predicate(self, online_clients, predicate, cid, log_text):
        to_move = set()
        for client in online_clients:
            if predicate(client):
                logging.info("Moving client %s %s", str(client), log_text)
                to_move.add(client)
        if to_move:
            cmd = self.ts3conn.query("clientmove", cid=cid)
            for client in to_move:
                cmd = cmd.pipe(clid=client.client_id)
            cmd.fetch()

    def move_people(self, online_clients):
        if self.state.round_state in (
            amongus.state_tracker.RoundState.LOBBY,
            amongus.state_tracker.RoundState.POSTGAME,
            amongus.state_tracker.RoundState.MEETING,
        ):
            # Empty the ghost lobby.
            self._move_people_matching_predicate(
                online_clients,
                lambda client: client.channel_id == FLAGS.dead_channel_id,
                FLAGS.main_channel_id,
                "out of dead channel into main lobby",
            )
        elif self.state.round_state == amongus.state_tracker.RoundState.ACTIVE:
            # Moving ghosts to ghost lobby.
            self._move_people_matching_predicate(
                online_clients,
                lambda client: client.channel_id == FLAGS.main_channel_id
                and self._is_player_in_list(client, self.state.dead_players),
                FLAGS.dead_channel_id,
                "INTO dead channel",
            )

    def sync(self):
        online_clients = self.online_clients()
        self.sync_server_groups(online_clients)
        self.sync_main_channel_status()
        self.move_people(online_clients)

    def run(self):
        self.ts3conn.exec_("use", sid=1)
        self.ts3conn.exec_("servernotifyregister", event="server")
        self.ts3conn.exec_("servernotifyregister", event="channel", id=0)
        self.sync()
        while True:
            self.send_keepalive_if_needed()

            try:
                event = self.ts3conn.wait_for_event(timeout=0.2)
                self.sync()
            except ts3.query.TS3TimeoutError:
                pass

            try:
                result = self.queue.get_nowait()
                self.state = result
                self.sync()
            except queue.Empty:
                pass


class ListenerThread(threading.Thread):
    def __init__(self, queue, **kwargs):
        super().__init__(**kwargs)
        self.queue = queue
        self.state = amongus.state_tracker.GameState()
        self.my_state = GameState()

    def process_packet(self, pkt):
        if not self.state.process_packet(pkt):
            return
        round_state = self.state.round_state
        changes = {"round_state": round_state}
        if (
            round_state == amongus.state_tracker.RoundState.LOBBY
            or round_state == amongus.state_tracker.RoundState.MEETING
            or amongus.rpcs.VotingCompleteRPC in pkt
            or amongus.rpcs.SetInfectedRPC in pkt
        ):
            # Update dead/alive players.
            game_data = self.state.find_netobj_of_type(
                amongus.state_tracker.NetObjGameData
            )
            if not game_data:
                logging.error(
                    "NetObjGameData missing when in MEETING state :( - no idea what's going on"
                )
                return
            living_players = set()
            dead_players = set()
            for p in game_data.players:
                if p.is_dead:
                    dead_players.add(p.name)
                else:
                    living_players.add(p.name)
            changes.update(
                alive_players=frozenset(living_players),
                dead_players=frozenset(dead_players),
            )
        new_my_state = dataclasses.replace(self.my_state, **changes)
        if new_my_state != self.my_state:
            logging.info("New state: %s", str(new_my_state))
            self.queue.put(new_my_state)
            self.my_state = new_my_state

    def run(self):
        state = amongus.state_tracker.GameState()

        logging.info("listener ready")
        scapy.all.sniff(
            prn=self.process_packet, filter="udp and (src port 22023 or dst port 22023)"
        )


def main(argv):
    if len(argv) != 1:
        raise app.UsageError("Too many arguments.")
    if not FLAGS.connection_string:
        raise app.UsageError("--connection_string is required.")

    scapy.all.conf.use_pcap = True
    scapy.all.conf.sniff_promisc = False

    queue = multiprocessing.Queue()
    listener_thread = ListenerThread(queue, daemon=True)
    listener_thread.start()

    with ts3.query.TS3ServerConnection(FLAGS.connection_string) as ts3conn:
        bot = TS3Bot(ts3conn, queue)
        bot.run()


if __name__ == "__main__":
    app.run(main)
