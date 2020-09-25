# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import copy
import dataclasses
import enum
import logging
from typing import Dict, List, Optional, Tuple

import scapy.packet

import amongus.enums
import amongus.hazel_packets

logger = logging.getLogger(__name__)


net_obj_dataclass_map = {}


def _register_net_obj_dataclass(net_obj_type):
    def _inner(cls):
        if net_obj_type in net_obj_dataclass_map:
            raise Exception(
                "{} already registered in dataclass map".format(net_obj_type)
            )
        net_obj_dataclass_map[net_obj_type] = cls
        return cls

    return _inner


@dataclasses.dataclass
class BaseNetObj:
    @classmethod
    def fields_to_copy(cls):
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def extra_data_from_packet(cls, pkt):
        return {}

    @classmethod
    def data_from_packet(cls, pkt):
        data = {k: getattr(pkt, k) for k in cls.fields_to_copy()}
        data.update(**cls.extra_data_from_packet(pkt))
        return data

    @classmethod
    def construct_from_spawn_data(cls, pkt):
        return cls(**cls.data_from_packet(pkt))

    def update_from_packet(self, pkt):
        raise Exception(self.netobj_type)


@dataclasses.dataclass
class NetObj(BaseNetObj):
    netobj_type: amongus.enums.AmongUsInnerNetClients
    netobj_dead: bool
    net_id: int
    game_state: "GameState" = dataclasses.field(repr=False)

    @classmethod
    def fields_to_copy(cls):
        return [
            f.name
            for f in dataclasses.fields(cls)
            if f.name not in ("netobj_dead", "net_id", "netobj_type", "game_state")
        ]

    @classmethod
    def construct_from_spawn_data(cls, game_state, netobj_type, net_id, pkt):
        data = cls.data_from_packet(pkt)
        data.update(
            netobj_type=netobj_type,
            net_id=net_id,
            netobj_dead=False,
            game_state=game_state,
        )
        return cls(**data)


class GameMapEnum(enum.Enum):
    SKELD = 0
    MIRA_HQ = 1
    POLUS = 2


class KillDistanceEnum(enum.Enum):
    SHORT = 0
    MEDIUM = 1
    LONG = 2


@dataclasses.dataclass
class NetObjGameOptions(BaseNetObj):
    max_players: int
    keywords: int
    map: GameMapEnum
    player_speed: float
    player_vision: float
    imposter_vision: float
    kill_cooldown: float
    common_tasks: int
    long_tasks: int
    short_tasks: int
    emergency_meetings: int
    imposter_count: int
    kill_distance: KillDistanceEnum
    discussion_time: int
    voting_time: int
    is_defaults: bool
    emergency_cooldown: int
    confirm_ejects: bool
    visual_tasks: bool


class RoundState(enum.Enum):
    LOBBY = "lobby"
    ACTIVE = "active"
    MEETING = "meeting"
    POSTGAME = "postgame"


@dataclasses.dataclass
class GameState:
    game_options: NetObjGameOptions = None
    net_obj_map: Dict[int, BaseNetObj] = dataclasses.field(default_factory=dict)
    scene: str = "OnlineGame"
    chat_log: List[str] = dataclasses.field(default_factory=list)

    @property
    def extra_serializable_attributes(self):
        return ["round_state"]

    def find_netobj_of_type(self, cls):
        netobj = None
        for v in self.net_obj_map.values():
            if v.netobj_dead:
                continue
            if isinstance(v, cls):
                if netobj:
                    raise Exception("multiple netobj of type {}".format(cls))
                netobj = v
        return netobj

    def get_game_data_player(self, player_id):
        game_data = self.find_netobj_of_type(NetObjGameData)
        for p in game_data.players:
            if p.player_id == player_id:
                return p
        p = NetObjGameDataPlayer(player_id=player_id)
        game_data.players.append(p)
        logger.warning("Generating GameDataPlayer instance for player %d", player_id)
        return p

    @property
    def round_state(self) -> RoundState:
        # The round is not active if we have an alive LobbyBehavior.
        if self.find_netobj_of_type(NetObjLobbyBehavior):
            return RoundState.LOBBY
        elif self.scene == "EndGame":
            return RoundState.POSTGAME
        elif self.find_netobj_of_type(NetObjMeetingHud):
            return RoundState.MEETING
        return RoundState.ACTIVE

    def reset(self):
        logger.info("Resetting state")
        self.net_obj_map = {}
        self.game_options = None

    def process_packet(self, pkt) -> bool:
        if amongus.hazel_packets.Hazel not in pkt:
            return False
        hzl = pkt[amongus.hazel_packets.Hazel]
        if hzl.type in (
            amongus.enums.HazelPacketType.PING.value,
            amongus.enums.HazelPacketType.ACK.value,
        ):
            return False
        if amongus.messages.AmongUsBroadcastMessage in hzl:
            msgs = hzl[amongus.messages.AmongUsBroadcastMessage].messages
        elif amongus.messages.AmongUsDirectedMessage in hzl:
            msgs = hzl[amongus.messages.AmongUsDirectedMessage].messages
        else:
            return False
        for msg in msgs:
            if msg.tag == amongus.enums.AmongUsMessageType.MSG_SPAWN.value:
                spawn = msg[amongus.spawn.AmongUsSpawnMessage]
                prefab = amongus.enums.AmongUsInnerNetSpawnPrefabs(spawn.spawnable_id)
                if prefab == amongus.enums.AmongUsInnerNetSpawnPrefabs.LOBBY_BEHAVIOR:
                    # Reset the state!
                    self.reset()
                if len(prefab.spawn_children) != len(spawn.children):
                    logger.warning(
                        "Spawned spawnable_id=%d with %d children (expected %d)",
                        spawn.spawnable_id,
                        len(spawn.children),
                        len(prefab.spawn_children),
                    )
                else:
                    for ch in zip(prefab.spawn_children, spawn.children):
                        child_enum, child_pkt = ch
                        child_cls = net_obj_dataclass_map.get(child_enum, None)
                        if not child_cls:
                            logger.warning(
                                "Unknown spawnable %s with net_id=%d",
                                child_enum,
                                child_pkt.net_id,
                            )
                            continue
                        initial_layer = amongus.data.initial_data_layers.get(
                            child_enum, None
                        )
                        if initial_layer:
                            initial_data = initial_layer(child_pkt.msg)
                        elif len(child_pkt.msg) == 0:
                            # We don't have an initial layer for PLAYER_PHYSICS. There's no data.
                            initial_data = None
                        else:
                            logger.warning(
                                "Unknown initial_data_layer %s with net_id=%d (payload length=%d)",
                                child_enum,
                                child_pkt.net_id,
                                len(child_pkt.msg),
                            )
                            continue
                        if (
                            child_pkt.net_id in self.net_obj_map
                            and not self.net_obj_map[child_pkt.net_id].netobj_dead
                        ):
                            logger.warning(
                                "Spawning %s on top of existing %s (net_id=%d)",
                                child_enum,
                                self.net_obj_map[child_pkt.net_id].netobj_type,
                                child_pkt.net_id,
                            )
                        self.net_obj_map[
                            child_pkt.net_id
                        ] = child_cls.construct_from_spawn_data(
                            self, child_enum, child_pkt.net_id, initial_data
                        )
            elif msg.tag == amongus.enums.AmongUsMessageType.MSG_RPC.value:
                rpc = msg[amongus.rpcs.AmongUsRPCMessage]
                obj = self.net_obj_map.get(rpc.net_id, None)
                if not obj:
                    logger.warning(
                        "RPC sent to net_id=%d that I didn't see spawn", rpc.net_id
                    )
                    continue
                if obj.netobj_dead:
                    logger.warning(
                        "RPC sent to net_id=%d (%s) that is already dead",
                        rpc.net_id,
                        obj.netobj_type,
                    )
                rpc_enum = amongus.enums.AmongUsRPCType(rpc.call_id)
                handler = getattr(obj, "handle_{}".format(rpc_enum._name_), None)
                if not handler:
                    logger.warning(
                        "RPC %s sent to net_id=%d (%s) with no registered handler",
                        rpc_enum,
                        rpc.net_id,
                        obj.netobj_type,
                    )
                    continue
                handler(rpc)
            elif msg.tag == amongus.enums.AmongUsMessageType.MSG_DATA_UPDATE.value:
                update = msg[amongus.data.AmongUsDataMessage]
                obj = self.net_obj_map.get(update.net_id, None)
                if not obj:
                    logger.warning(
                        "Data update for net_id=%d that I didn't see spawn",
                        update.net_id,
                    )
                    continue
                if obj.netobj_dead:
                    logger.warning(
                        "Data update for net_id=%d (%s) that is already dead",
                        update.net_id,
                        obj.netobj_type,
                    )
                update_layer = amongus.data.data_layers.get(obj.netobj_type, None)
                if not update_layer:
                    logger.warning(
                        "Data update for net_id=%d (%s) that has no associated update layer",
                        update.net_id,
                        obj.netobj_type,
                    )
                    continue
                obj.update_from_packet(update_layer(update[scapy.packet.Raw].load))
            elif msg.tag == amongus.enums.AmongUsMessageType.MSG_DESPAWN.value:
                despawn = msg[amongus.spawn.AmongUsDespawnMessage]
                if despawn.net_id in self.net_obj_map:
                    self.net_obj_map[despawn.net_id].netobj_dead = True
                else:
                    logger.warning(
                        "Despawning net_id=%d that I didn't see spawn", despawn.net_id
                    )
            elif msg.tag == amongus.enums.AmongUsMessageType.MSG_CHANGE_SCENE.value:
                scene = msg.scene.decode("utf8")
                logger.info("Changing scene to %s", scene)
                self.scene = scene
        return True

    def asdict(self):
        return asdict(self)


@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_POLUS)
@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_KELD)
@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_MIRA_HQ)
@dataclasses.dataclass
class NetObjShipStatus(NetObj):
    def update_from_packet(self, pkt):
        # TODO(lukegb): I'm too lazy for this.
        pass

    def handle_REPAIR_SYSTEM(self, pkt):
        pass


@dataclasses.dataclass
class NetObjMeetingHudVote(BaseNetObj):
    is_dead: bool
    has_voted: bool
    was_reporter: bool
    voted_for: Optional[int]


@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.MEETING_HUD)
@dataclasses.dataclass
class NetObjMeetingHud(NetObj):
    votes: List[NetObjMeetingHudVote]

    @classmethod
    def extra_data_from_packet(cls, pkt):
        return {
            "votes": [
                NetObjMeetingHudVote.construct_from_spawn_data(v) for v in pkt.votes
            ]
        }

    def update_from_packet(self, pkt):
        for pair in zip(pkt.updated, pkt.votes):
            idx, vote_pkt = pair
            self.votes[idx] = NetObjMeetingHudVote.construct_from_spawn_data(vote_pkt)

    def handle_CAST_VOTE(self, pkt):
        src_player = self.game_state.get_game_data_player(pkt.src_player_id)
        suspect_player_name = None
        if pkt.suspect_player_id != 0xFF:
            suspect_player = self.game_state.get_game_data_player(pkt.suspect_player_id)
            suspect_player_name = suspect_player.name
        else:
            suspect_player_name = "[skip]"
        print("{} votes for {}".format(src_player.name, suspect_player_name))

    def handle_VOTING_COMPLETE(self, pkt):
        print("Voting complete!\n\tVotes:")
        for nvote in enumerate(pkt.votes):
            n, vote = nvote
            src_player = self.game_state.get_game_data_player(n)
            src_player_name = src_player.name
            if vote.was_reporter:
                src_player_name += " (reporter)"
            txt = ""
            if vote.is_dead:
                txt = "is dead"
            elif not vote.has_voted:
                txt = "did not vote"
            elif vote.voted_for == -1:
                txt = "voted to skip"
            else:
                dst_player_name = self.game_state.get_game_data_player(
                    vote.voted_for
                ).name
                txt = "voted for {}".format(dst_player_name)
            print("\t\t{} {}".format(src_player_name, txt))
        print("\n\tResults:")
        if pkt.tie:
            print("\t\t...it was a tie.")
        elif pkt.exiled_player_id == 0xFF:
            print("\t\tSkipped.")
        else:
            exiled_player = self.game_state.get_game_data_player(pkt.exiled_player_id)
            print("\t\t{} was ejected.".format(exiled_player.name))
            exiled_player.is_dead = True

    def handle_CLOSE_MEETING_HUD(self, pkt):
        self.netobj_dead = True


@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.LOBBY_BEHAVIOR)
@dataclasses.dataclass
class NetObjLobbyBehavior(NetObj):
    pass


@dataclasses.dataclass
class NetObjGameDataPlayerTask(BaseNetObj):
    task_id: int
    task_done: bool
    task_type: Optional[int] = None

    @classmethod
    def fields_to_copy(cls):
        return ["task_id", "task_done"]

    def update_from_rpc(self, pkt):
        self.task_done = pkt.task_done


@dataclasses.dataclass
class NetObjGameDataPlayer(BaseNetObj):
    player_id: int
    name: str = "???"
    color_id: int = 0
    hat_id: int = 0
    pet_id: int = 0
    skin_id: int = 0
    is_dead: bool = False
    is_impostor: bool = False
    disconnected: bool = False
    tasks: List[NetObjGameDataPlayerTask] = None

    @classmethod
    def fields_to_copy(cls):
        return ["player_id"]

    @classmethod
    def extra_data_from_packet(cls, pkt):
        pi = pkt[amongus.player_info.PlayerInfo]
        d = {
            "tasks": [
                NetObjGameDataPlayerTask.construct_from_spawn_data(t) for t in pi.tasks
            ],
        }
        subfields = [
            "color_id",
            "hat_id",
            "pet_id",
            "skin_id",
            "is_dead",
            "is_impostor",
            "disconnected",
        ]
        d.update(**{k: getattr(pi, k) for k in subfields})
        d["name"] = pi.player_name.decode("utf8")
        return d

    def update_from_player_info(self, pkt):
        subfields = [
            "color_id",
            "hat_id",
            "pet_id",
            "skin_id",
            "is_dead",
            "is_impostor",
            "disconnected",
        ]
        for f in subfields:
            setattr(self, f, getattr(pkt, f))
        self.name = pkt.player_name.decode("utf8")

        if not self.tasks:
            self.tasks = [
                NetObjGameDataPlayerTask.construct_from_spawn_data(t) for t in pkt.tasks
            ]
        else:
            tasks_by_id = {}
            for task in self.tasks:
                tasks_by_id[task.task_id] = task
            for taskpkt in pkt.tasks:
                if taskpkt.task_id not in tasks_by_id:
                    t = NetObjGameDataPlayerTask(
                        task_id=taskpkt.task_id, task_done=False
                    )
                    tasks_by_id[t.task_id] = t
                    self.tasks.append(t)
                tasks_by_id[taskpkt.task_id].update_from_rpc(taskpkt)


@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.GAME_DATA)
@dataclasses.dataclass
class NetObjGameData(NetObj):
    players: List[NetObjGameDataPlayer]

    @classmethod
    def fields_to_copy(cls):
        return []

    @classmethod
    def extra_data_from_packet(cls, pkt):
        return {
            "players": [
                NetObjGameDataPlayer.construct_from_spawn_data(p) for p in pkt.players
            ]
        }

    def handle_PLAYER_INFO(self, pkt):
        player_infos_by_id = {}
        for player in self.players:
            player_infos_by_id[player.player_id] = player
        for pipkt in pkt.player_infos:
            if pipkt.tag not in player_infos_by_id:
                p = NetObjGameDataPlayer(player_id=pipkt.tag)
                player_infos_by_id[p.player_id] = p
                self.players.append(p)
            player_infos_by_id[pipkt.tag].update_from_player_info(
                pipkt[amongus.player_info.PlayerInfo]
            )

    def handle_SET_TASKS(self, pkt):
        for p in self.players:
            if p.player_id != pkt.player_id:
                continue
            if len(p.tasks) != len(pkt.task_types):
                p.tasks = [
                    NetObjGameDataPlayerTask(
                        task_id=n, task_done=False, task_type=pkt.task_types[n]
                    )
                    for n in range(len(pkt.task_types))
                ]
            else:
                for task_pair in zip(p.tasks, pkt.task_types):
                    task, task_type_id = task_pair
                    task.task_type = task_type_id
            break


@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.VOTE_BAN_SYSTEM)
@dataclasses.dataclass
class NetObjVoteBanSystem(NetObj):
    pass


@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.PLAYER_CONTROL)
@dataclasses.dataclass
class NetObjPlayerControl(NetObj):
    player_id: int

    def handle_CHECK_NAME(self, pkt):
        pass

    def handle_CHECK_COLOR(self, pkt):
        pass

    @property
    def player(self):
        return self._get_game_data_player()

    def _get_game_data_player(self, player_id=None):
        if player_id is None:
            player_id = self.player_id
        return self.game_state.get_game_data_player(player_id=player_id)

    def handle_SET_PET(self, pkt):
        self.player.pet_id = pkt.pet

    def handle_SET_HAT(self, pkt):
        self.player.hat_id = pkt.hat

    def handle_SET_SKIN(self, pkt):
        self.player.skin_id = pkt.skin

    def handle_SET_NAME(self, pkt):
        self.player.name = pkt.name

    def handle_SET_COLOR(self, pkt):
        self.player.color_id = pkt.color

    def handle_COMPLETE_TASK(self, pkt):
        for task in self._get_game_data_player().tasks:
            if pkt.task_id == task.task_id:
                task.task_done = True
                break
        else:
            # TODO(lukegb): Raise exception?
            pass

    def handle_PLAY_ANIMATION(self, pkt):
        pass

    def handle_ADD_CHAT(self, pkt):
        note = "CHAT: {}".format(self.player.name)
        if self.player.is_dead:
            note += " (dead)"
        print("{}: {}".format(note, pkt.msg.decode("utf8")))

    def handle_ADD_CHAT_NOTE(self, pkt):
        if pkt.note_id == 0x00:
            print("{} voted!".format(self._get_game_data_player(pkt.src_player).name))

    def handle_MURDER_PLAYER(self, pkt):
        them_netobj = self.game_state.net_obj_map.get(pkt.payload.net_id, None)
        if not them_netobj:
            print("couldn't find them in MURDER_PLAYER handler")
            return
        them = them_netobj.player
        them.is_dead = True
        print("{} murdered {}".format(self.player.name, them.name))

    def handle_GAME_COUNTDOWN(self, pkt):
        if pkt.countdown == 0xFF:
            print("Game start cancelled.")
            return
        print("Game start in {}...".format(pkt.countdown))

    def handle_SET_INFECTED(self, pkt):
        pass  # We get this data via player info anyway.

    def handle_REPORT_DEAD_BODY(self, pkt):
        me_name = self.player.name
        if pkt.who == 0xFF:
            print("{} pressed the emergency button (REPORT_DEAD_BODY)!".format(me_name))
            return
        who = self._get_game_data_player(pkt.who)
        print("{} reported {}'s death (REPORT_DEAD_BODY)!".format(me_name, who.name))

    def handle_START_MEETING(self, pkt):
        me_name = self.player.name
        if pkt.who == 0xFF:
            print("{} pressed the emergency button!".format(me_name))
            return
        who = self._get_game_data_player(pkt.who)
        print("{} reported {}'s death!".format(me_name, who.name))

    def handle_SET_SCANNER(self, pkt):
        print(
            "SET_SCANNER: id={} on={} (by {})".format(pkt.id, pkt.on, self.player.name)
        )

    def handle_GAME_OPTIONS(self, pkt):
        self.game_state.game_options = NetObjGameOptions.construct_from_spawn_data(pkt)


@_register_net_obj_dataclass(amongus.enums.AmongUsInnerNetClients.PLAYER_PHYSICS)
@dataclasses.dataclass
class NetObjPlayerPhysics(NetObj):
    in_vent: bool = False

    @classmethod
    def fields_to_copy(cls):
        return []

    def _get_game_data_player(self):
        player_control_netid = self.net_id - 1
        player_control = self.game_state.net_obj_map.get(player_control_netid, None)
        if not player_control:
            raise KeyError(
                "PlayerPhysics net_id={} couldn't find corresponding PlayerControl net_id={}".format(
                    self.net_id, player_control_netid
                )
            )
        return player_control._get_game_data_player()

    def handle_ENTER_VENT(self, pkt):
        self.in_vent = True
        print(
            "{} entered vent {}".format(self._get_game_data_player().name, pkt.vent_id)
        )

    def handle_EXIT_VENT(self, pkt):
        self.in_vent = False
        print(
            "{} exited vent {}".format(self._get_game_data_player().name, pkt.vent_id)
        )


@_register_net_obj_dataclass(
    amongus.enums.AmongUsInnerNetClients.CUSTOM_NETWORK_TRANSFORM
)
@dataclasses.dataclass
class NetObjCustomNetworkTransform(NetObj):
    sequence_number: int
    pos: Tuple[int, int]
    vel: Tuple[int, int]

    @classmethod
    def fields_to_copy(cls):
        return ["sequence_number"]

    @classmethod
    def extra_data_from_packet(cls, pkt):
        return {
            "pos": (pkt.x, pkt.y),
            "vel": (pkt.x_vel, pkt.y_vel),
        }

    def _valid_sequence_number(self, seq):
        wrapped_sq = (self.sequence_number + 0x7FFF) & 0xFFFF
        if self.sequence_number < wrapped_sq:
            if seq <= self.sequence_number:
                return False
            if wrapped_sq < seq:
                return False
        else:
            if seq <= self.sequence_number and wrapped_sq < seq:
                return False
        return True

    def update_from_packet(self, pkt):
        if not self._valid_sequence_number(pkt.sequence_number):
            return
        self.sequence_number = pkt.sequence_number
        self.pos = (pkt.x, pkt.y)
        self.vel = (pkt.x_vel, pkt.y_vel)

    def handle_CUSTOM_NETWORK_TRANSFORM_SNAPTO(self, pkt):
        if not self._valid_sequence_number(pkt.sequence_number):
            return
        self.sequence_number = pkt.sequence_number
        self.pos = (pkt.x, pkt.y)
        self.vel = (0, 0)


def _is_dataclass_instance(obj):
    return hasattr(type(obj), "__dataclass_fields__")


def asdict(obj):
    # Cribbed from dataclasses.asdict from the Python source code.
    if isinstance(obj, enum.Enum):
        return obj.name
    elif _is_dataclass_instance(obj):
        result = []
        for f in dataclasses.fields(obj):
            if f.name == "game_state" and isinstance(obj, NetObj):
                # Avoid using the backreference.
                continue
            result.append((f.name, asdict(getattr(obj, f.name))))
        for fname in getattr(obj, "extra_serializable_attributes", []):
            result.append((fname, asdict(getattr(obj, fname))))
        return dict(result)
    elif isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[asdict(v) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(asdict(v) for v in obj)
    elif isinstance(obj, dict):
        result = []
        for k, v in obj.items():
            if isinstance(obj, NetObj) and obj.netobj_dead:
                continue
            result.append((asdict(k), asdict(v)))
        return type(obj)(result)
    else:
        return copy.deepcopy(obj)
