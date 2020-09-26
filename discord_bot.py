# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import concurrent
import dataclasses
import threading
import time
from typing import FrozenSet, List

from absl import app
from absl import flags
from absl import logging
import discord
import scapy.all

import amongus.rpcs
import amongus.state_tracker

FLAGS = flags.FLAGS
flags.DEFINE_string(
    "client_token",
    None,
    "Discord client token",
)
flags.DEFINE_integer("guild_id", 547155312071671809, "ID of guild to use.")
flags.DEFINE_integer(
    "main_channel_id",
    759143339898437642,
    "Main channel ID (for people who are alive, etc.)",
)
flags.DEFINE_integer(
    "dead_channel_id", 759143383712661536, "Dead channel ID (for people who are dead)"
)
flags.DEFINE_integer("alive_role", 759143620569333840, "Role ID to add alive people to")
flags.DEFINE_integer("dead_role", 759143500464783420, "Role ID to add dead people to")


def _coerce_list(thing):
    if isinstance(thing, (list, tuple)):
        return list(thing)
    else:
        return [thing]


class UsernameDatabase:
    def __init__(self, data):
        self.usernames_to_discord_ids = {}
        self.discord_ids_to_usernames = {}
        for usernames, client_ids in data:
            usernames = _coerce_list(usernames)
            client_ids = _coerce_list(client_ids)
            for username in usernames:
                self.usernames_to_discord_ids[username] = client_ids
            for client_id in client_ids:
                self.discord_ids_to_usernames[client_id] = usernames

    def usernames_from_discord_ids(self, discord_ids):
        return self.discord_ids_to_usernames.get(discord_ids, [])

    def discord_idss_from_username(self, username):
        return self.usernames_to_discord_ids.get(username, [])


USERNAME_DB = UsernameDatabase(
    [
        ("Memories", 266212268147081216),
        (("Zenras", "Giblets", "Stelbig"), 233707984033677313),
        ("Mumfrey", 235556733639065600),
        ("Raisin", 143158010498252810),
        ("th0rney", 236916600433934337),
        ("HDWolfGamer", 161584244479623168),
        ("lukegb", 102909905052114944),
        ("felltir", 212206922978295808),
        ("NSE", 359435848707604500),
        ("Rosalyan", 226761069576716288),
        ("BrackishBrit", 276851033005752320),
        ("sirrambod", 695013418456973386),
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
class DiscordUser:
    client_name: str
    client_id: int
    client_database_id: int
    channel_id: int
    roles: List[int]


class DiscordBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._game_state = GameState()
        self._guild = None
        self._dead_channel = None
        self._main_channel = None
        self._dead_role = None
        self._alive_role = None

    @classmethod
    def _lowercase_names(cls, names):
        return (n.lower() for n in names)

    @classmethod
    def _is_player_in_list(cls, user, player_names):
        return any(
            (un in cls._lowercase_names(player_names))
            for un in cls._lowercase_names(
                USERNAME_DB.usernames_from_discord_ids(user.id)
            )
        )

    async def sync_role_with_list(self, role, player_names):
        current_users = set(role.members)
        want_users = set()
        for member in self._guild.members:
            if self._is_player_in_list(member, player_names):
                want_users.add(member)

        to_add = want_users - current_users
        to_remove = current_users - want_users
        for member in to_add:
            logging.info("Adding %s to server group %s", str(member), str(role))
            await member.add_roles(role)
        for member in to_remove:
            logging.info("Removing %s from server group %s", str(member), str(role))
            await member.remove_roles(role)

    async def sync_roles(self):
        want_alive_players = self._game_state.alive_players
        want_dead_players = self._game_state.dead_players
        if self._game_state.round_state in (
            amongus.state_tracker.RoundState.LOBBY,
            amongus.state_tracker.RoundState.POSTGAME,
        ):
            want_alive_players = []
            want_dead_players = []
        await self.sync_role_with_list(self._alive_role, self._game_state.alive_players)
        await self.sync_role_with_list(self._dead_role, self._game_state.dead_players)

    async def sync_main_channel_status(self):
        if self._game_state.round_state in (
            amongus.state_tracker.RoundState.LOBBY,
            amongus.state_tracker.RoundState.POSTGAME,
        ):
            await self._main_channel.set_permissions(
                self._dead_role, connect=True, speak=True
            )
            await self._main_channel.set_permissions(
                self._alive_role, connect=True, speak=True
            )
        elif self._game_state.round_state == amongus.state_tracker.RoundState.MEETING:
            await self._main_channel.set_permissions(
                self._dead_role, connect=True, speak=False
            )
            await self._main_channel.set_permissions(
                self._alive_role, connect=True, speak=True
            )
        else:
            await self._main_channel.set_permissions(
                self._dead_role, connect=True, speak=False
            )
            await self._main_channel.set_permissions(
                self._alive_role, connect=True, speak=False
            )

    async def move_people(self):
        if self._game_state.round_state in (
            amongus.state_tracker.RoundState.LOBBY,
            amongus.state_tracker.RoundState.POSTGAME,
            amongus.state_tracker.RoundState.MEETING,
        ):
            # Empty the ghost lobby.
            for member in self._dead_channel.members:
                await member.move_to(self._main_channel)
        elif self._game_state.round_state == amongus.state_tracker.RoundState.ACTIVE:
            # Moving ghosts to ghost lobby.
            for member in self._main_channel.members:
                if self._is_player_in_list(member, self._game_state.dead_players):
                    await member.move_to(self._dead_channel)

    async def sync(self):
        logging.info("Syncing state")
        await self.sync_roles()
        await self.sync_main_channel_status()
        await self.move_people()

    async def update_game_state(self, new_state):
        self._game_state = new_state
        await self.sync()

    async def on_ready(self):
        self._guild = self.get_guild(FLAGS.guild_id)
        self._dead_channel = self._guild.get_channel(FLAGS.dead_channel_id)
        self._main_channel = self._guild.get_channel(FLAGS.main_channel_id)
        self._dead_role = self._guild.get_role(FLAGS.dead_role)
        self._alive_role = self._guild.get_role(FLAGS.alive_role)
        await self.sync()


class ListenerThread(threading.Thread):
    def __init__(self, new_state_cb, loop, **kwargs):
        super().__init__(**kwargs)
        self.loop = loop
        self.new_state_cb = new_state_cb
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
            future = asyncio.run_coroutine_threadsafe(
                self.new_state_cb(new_my_state), self.loop
            )
            try:
                future.result(5)
            except concurrent.futures.TimeoutError:
                logging.exception(
                    "Timed out waiting for coroutine to respond to update"
                )
                raise
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
    if not FLAGS.client_token:
        raise app.UsageError("--client_token is required.")

    scapy.all.conf.use_pcap = True
    scapy.all.conf.sniff_promisc = False
    loop = asyncio.get_event_loop()

    bot = DiscordBot(loop=loop)
    listener_thread = ListenerThread(bot.update_game_state, loop, daemon=True)
    listener_thread.start()
    bot.run(FLAGS.client_token)


if __name__ == "__main__":
    app.run(main)
