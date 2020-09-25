# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import enum


class ScapyEnum(enum.Enum):
    @classmethod
    def as_scapy_dict(cls):
        return {v.value: k for k, v in cls.__members__.items()}


@enum.unique
class HazelPacketType(ScapyEnum):
    NONE = 0
    RELIABLE = 1
    HELLO = 8
    PING = 12
    DISCONNECT = 9
    ACK = 10
    FRAG = 11


@enum.unique
class AmongUsMessageType(ScapyEnum):
    # InnerNetClient.HandleGameDataInner
    MSG_DATA_UPDATE = 0x1  ## ??? [uint32 ID, ...]
    MSG_RPC = 0x2  ## ??? [uint32 ID, ...]

    MSG_SPAWN = 0x4  ## ??? [uint32 spawnable object ID, uint32 owner ID, ???, byte flags (lowest bit == ???), uint32 children_cnt, [uint32 item, msg (deserialize?)]]
    MSG_DESPAWN = 0x5  ## ??? [uint32 net ID]

    MSG_CHANGE_SCENE = 0x6  ## ??? [uint32 client ID, string scene?]
    MSG_MARK_READY = 0x7  ## ??? [uint32 client ID]


@enum.unique
class AmongUsInnerNetSpawnPrefabs(ScapyEnum):
    SHIP_STATUS_KELD = 0
    MEETING_HUD = 1
    LOBBY_BEHAVIOR = 2
    GAME_DATA = 3
    PLAYER = 4
    SHIP_STATUS_MIRA_HQ = 5
    SHIP_STATUS_POLUS = 6

    @property
    def spawn_children(self):
        return {
            self.SHIP_STATUS_KELD: [AmongUsInnerNetClients.SHIP_STATUS_KELD],
            self.MEETING_HUD: [AmongUsInnerNetClients.MEETING_HUD],
            self.LOBBY_BEHAVIOR: [AmongUsInnerNetClients.LOBBY_BEHAVIOR],
            self.GAME_DATA: [
                AmongUsInnerNetClients.GAME_DATA,
                AmongUsInnerNetClients.VOTE_BAN_SYSTEM,
            ],
            self.PLAYER: [
                AmongUsInnerNetClients.PLAYER_CONTROL,
                AmongUsInnerNetClients.PLAYER_PHYSICS,
                AmongUsInnerNetClients.CUSTOM_NETWORK_TRANSFORM,
            ],
            self.SHIP_STATUS_MIRA_HQ: [AmongUsInnerNetClients.SHIP_STATUS_MIRA_HQ],
            self.SHIP_STATUS_POLUS: [AmongUsInnerNetClients.SHIP_STATUS_POLUS],
        }.get(self)


@enum.unique
class AmongUsInnerNetClients(ScapyEnum):
    SHIP_STATUS_KELD = 0
    MEETING_HUD = 1
    LOBBY_BEHAVIOR = 2
    GAME_DATA = 3
    VOTE_BAN_SYSTEM = 4
    PLAYER_CONTROL = 5
    PLAYER_PHYSICS = 6
    CUSTOM_NETWORK_TRANSFORM = 7

    SHIP_STATUS_MIRA_HQ = 0xF1
    SHIP_STATUS_POLUS = 0xF2


@enum.unique
class AmongUsRPCType(ScapyEnum):
    # PlayerControl.HandleRpc
    PLAY_ANIMATION = 0x0
    COMPLETE_TASK = 0x1
    GAME_OPTIONS = 0x2
    SET_INFECTED = 0x3
    EXILED = 0x4
    CHECK_NAME = 0x5
    SET_NAME = 0x6
    CHECK_COLOR = 0x7
    SET_COLOR = 0x8
    SET_HAT = 0x9
    SET_SKIN = 0xA
    REPORT_DEAD_BODY = 0xB
    MURDER_PLAYER = 0xC
    ADD_CHAT = 0xD
    START_MEETING = 0xE
    SET_SCANNER = 0xF
    ADD_CHAT_NOTE = 0x10
    SET_PET = 0x11
    GAME_COUNTDOWN = 0x12

    # PlayerPhysics.HandleRpc
    ENTER_VENT = 0x13  # [packed_uint32]
    EXIT_VENT = 0x14  # [packed_uint32]

    # CustomNetworkTransform.HandleRpc
    # Teleport? Used while venting.
    CUSTOM_NETWORK_TRANSFORM_SNAPTO = 0x15  # [position (vector2), min_sid (uint16)]

    # MeetingHud.HandleRpc
    CLOSE_MEETING_HUD = 0x16  # []
    VOTING_COMPLETE = 0x17  # [states (bytes), exiled_player_id (byte), tie (bool)]
    CAST_VOTE = 0x18  # [src_player (byte), suspect_player (byte)]
    CLEAR_VOTE = 0x19  # []

    # VoteBanSystem.HandleRpc
    ADD_VOTE_BAN_VOTE = 0x1A  # [src_client (int32), client_id (int32)]

    # ShipStatus.HandleRpc
    CLOSE_DOORS_OF_TYPE = 0x1B  # [door_type_id (byte)???]
    REPAIR_SYSTEM = (
        0x1C  # [system_id (byte)???, player_data (msgext netobject), amount (byte)]
    )

    # GameData.HandleRpc
    SET_TASKS = 0x1D  # [player_id (byte), task_type_ids (bytes)]
    PLAYER_INFO = 0x1E  # [player_data (submessages)]
