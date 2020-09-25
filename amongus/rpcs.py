# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields
import scapy.packet

import amongus.enums
import amongus.fields
import amongus.game_options
import amongus.meeting_hud_vote
import amongus.messages
import amongus.player_info


@amongus.messages.sub_message_layer(amongus.enums.AmongUsMessageType.MSG_RPC)
class AmongUsRPCMessage(scapy.packet.Packet):
    name = "AmongUsRPCMessage"
    fields_desc = [
        amongus.fields.PackedUInt32Field("net_id", 0x00),
        scapy.fields.ByteEnumField(
            "call_id", None, amongus.enums.AmongUsRPCType.as_scapy_dict()
        ),
    ]


_register_rpc = amongus.base_packets.tagged_layer(AmongUsRPCMessage, "call_id")


@_register_rpc(amongus.enums.AmongUsRPCType.PLAY_ANIMATION)
class PlayAnimationRPC(scapy.packet.Packet):
    name = "PlayAnimationRPC"
    fields_desc = [scapy.fields.ByteField("id", 0x00)]


@_register_rpc(amongus.enums.AmongUsRPCType.COMPLETE_TASK)
class CompleteTaskRPC(scapy.packet.Packet):
    name = "CompleteTaskRPC"
    fields_desc = [amongus.fields.PackedUInt32Field("task_id", None)]


@_register_rpc(amongus.enums.AmongUsRPCType.GAME_OPTIONS)
class GameOptionsRPC(scapy.packet.Packet):
    name = "GameOptionsRPC"
    fields_desc = [
        amongus.fields.PackedUInt32Field("length", 0x00),
    ]

    def extract_padding(self, s):
        return s[: self.length], s[self.length :]


scapy.packet.bind_layers(GameOptionsRPC, amongus.game_options.GameOptions)


@_register_rpc(amongus.enums.AmongUsRPCType.SET_INFECTED)
class SetInfectedRPC(scapy.packet.Packet):
    name = "SetInfectedRPC"
    fields_desc = [
        amongus.fields.SmallFieldLenField("infected_len", 0x00, count_of="infected"),
        scapy.fields.XStrLenField(
            "infected", None, length_from=lambda pkt: pkt.infected_len
        ),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.EXILED)
class ExiledRPC(scapy.packet.Packet):
    name = "ExiledRPC"
    fields_desc = []


@_register_rpc(amongus.enums.AmongUsRPCType.CHECK_NAME)
class CheckNameRPC(scapy.packet.Packet):
    name = "CheckNameRPC"
    fields_desc = [
        amongus.fields.SmallFieldLenField("name_len", 0x00, count_of="name"),
        scapy.fields.StrLenField("name", None, length_from=lambda pkt: pkt.name_len),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.SET_NAME)
class SetNameRPC(scapy.packet.Packet):
    name = "SetNameRPC"
    fields_desc = [
        amongus.fields.SmallFieldLenField(
            "player_name_len", 0x00, count_of="player_name"
        ),
        scapy.fields.StrLenField(
            "player_name", None, length_from=lambda pkt: pkt.player_name_len
        ),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.CHECK_COLOR)
class CheckColorRPC(scapy.packet.Packet):
    name = "CheckColorRPC"
    fields_desc = [
        scapy.fields.ByteField("color", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.SET_COLOR)
class SetColorRPC(scapy.packet.Packet):
    name = "SetColorRPC"
    fields_desc = [
        scapy.fields.ByteField("color", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.SET_HAT)
class SetHatRPC(scapy.packet.Packet):
    name = "SetHatRPC"
    fields_desc = [
        amongus.fields.PackedUInt32Field("hat", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.SET_SKIN)
class SetSkinRPC(scapy.packet.Packet):
    name = "SetSkinRPC"
    fields_desc = [
        amongus.fields.PackedUInt32Field("skin", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.REPORT_DEAD_BODY)
class ReportDeadBodyRPC(scapy.packet.Packet):
    name = "ReportDeadBodyRPC"
    fields_desc = [
        scapy.fields.ByteField("who", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.MURDER_PLAYER)
class MurderPlayerRPC(scapy.packet.Packet):
    name = "MurderPlayerRPC"
    fields_desc = [amongus.fields.PackedUInt32Field("net_id", None)]


@_register_rpc(amongus.enums.AmongUsRPCType.ADD_CHAT)
class AddChatRPC(scapy.packet.Packet):
    name = "AddChatRPC"
    fields_desc = [
        amongus.fields.SmallFieldLenField("msg_len", 0x00, count_of="msg"),
        scapy.fields.StrLenField("msg", None, length_from=lambda pkt: pkt.msg_len),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.START_MEETING)
class StartMeetingRPC(scapy.packet.Packet):
    name = "StartMeetingRPC"
    fields_desc = [
        scapy.fields.ByteField("who", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.SET_SCANNER)
class SetScannerRPC(scapy.packet.Packet):
    name = "SetScannerRPC"
    fields_desc = [
        scapy.fields.ByteField("on", 0x00),  # boolean
        scapy.fields.ByteField("id", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.ADD_CHAT_NOTE)
class AddChatNoteRPC(scapy.packet.Packet):
    name = "AddChatNoteRPC"
    fields_desc = [
        scapy.fields.ByteField("src_player", 0x00),
        scapy.fields.ByteField("note_id", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.SET_PET)
class SetPetRPC(scapy.packet.Packet):
    name = "SetPetRPC"
    fields_desc = [
        amongus.fields.PackedUInt32Field("pet", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.GAME_COUNTDOWN)
class GameCountdownRPC(scapy.packet.Packet):
    name = "GameCountdownRPC"
    fields_desc = [
        amongus.fields.PackedUInt32Field("sequence_number", 0x00),
        scapy.fields.ByteField("countdown", 0x00),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.ENTER_VENT)
class EnterVentRPC(scapy.packet.Packet):
    name = "EnterVentRPC"
    fields_desc = [amongus.fields.PackedUInt32Field("vent_id", 0)]


@_register_rpc(amongus.enums.AmongUsRPCType.EXIT_VENT)
class ExitVentRPC(scapy.packet.Packet):
    name = "ExitVentRPC"
    fields_desc = [amongus.fields.PackedUInt32Field("vent_id", 0)]


@_register_rpc(amongus.enums.AmongUsRPCType.CUSTOM_NETWORK_TRANSFORM_SNAPTO)
class SnapToRPC(scapy.packet.Packet):
    name = "SnapToRPC"
    fields_desc = [
        scapy.fields.LEShortField("x", 0),
        scapy.fields.LEShortField("y", 0),
        scapy.fields.LEShortField("sequence_number", 0),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.CLOSE_MEETING_HUD)
class CloseMeetingHUDRPC(scapy.packet.Packet):
    name = "CloseMeetingHUDRPC"
    fields_desc = []


@_register_rpc(amongus.enums.AmongUsRPCType.VOTING_COMPLETE)
class VotingCompleteRPC(scapy.packet.Packet):
    name = "VotingCompleteRPC"
    fields_desc = [
        amongus.fields.SmallFieldLenField("votes_len", 0x00, count_of="votes"),
        scapy.fields.PacketListField(
            "votes",
            [],
            cls=amongus.meeting_hud_vote.MeetingHudVote,
            count_from=lambda pkt: pkt.votes_len,
        ),
        scapy.fields.ByteField("exiled_player_id", None),
        scapy.fields.ByteField("tie", None),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.CAST_VOTE)
class CastVoteRPC(scapy.packet.Packet):
    name = "CastVoteRPC"
    fields_desc = [
        scapy.fields.ByteField("src_player_id", None),
        scapy.fields.ByteField("suspect_player_id", None),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.CLEAR_VOTE)
class ClearVoteRPC(scapy.packet.Packet):
    name = "ClearVoteRPC"
    fields_desc = []


@_register_rpc(amongus.enums.AmongUsRPCType.ADD_VOTE_BAN_VOTE)
class AddVoteBanVoteRPC(scapy.packet.Packet):
    name = "AddVoteBanVoteRPC"
    fields_desc = [
        scapy.fields.IntField("src_client_id", 0),
        scapy.fields.IntField("target_client_id", 0),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.CLOSE_DOORS_OF_TYPE)
class CloseDoorsOfTypeRPC(scapy.packet.Packet):
    name = "CloseDoorsOfTypeRPC"
    fields_desc = [
        scapy.fields.ByteField("door_type_id", 0),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.REPAIR_SYSTEM)
class RepairSystemRPC(scapy.packet.Packet):
    name = "RepairSystemRPC"
    fields_desc = [
        scapy.fields.ByteField("system_id", 0),
        amongus.fields.PackedUInt32Field("net_id", 0),
        scapy.fields.ByteField("amount", 0),
    ]


@_register_rpc(amongus.enums.AmongUsRPCType.SET_TASKS)
class SetTasksRPC(scapy.packet.Packet):
    name = "SetTasksRPC"
    fields_desc = [
        scapy.fields.ByteField("player_id", 0),
        amongus.fields.SmallFieldLenField(
            "task_types_len", 0x00, count_of="task_types"
        ),
        scapy.fields.XStrLenField(
            "task_types", None, length_from=lambda pkt: pkt.task_types_len
        ),
    ]


class PlayerInfoSubMessage(scapy.packet.Packet):
    name = "PlayerInfoSubMessage"
    fields_desc = [
        scapy.fields.LenField("length", None, fmt="<H"),
        scapy.fields.ByteField("tag", 0x00),
    ]

    def extract_padding(self, s):
        return s[: self.length], s[self.length :]


scapy.packet.bind_layers(PlayerInfoSubMessage, amongus.player_info.PlayerInfo)


@_register_rpc(amongus.enums.AmongUsRPCType.PLAYER_INFO)
class PlayerInfoRPC(scapy.packet.Packet):
    name = "PlayerInfoRPC"
    fields_desc = [
        scapy.fields.PacketListField("player_infos", None, cls=PlayerInfoSubMessage)
    ]
