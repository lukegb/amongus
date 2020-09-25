# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields
import scapy.packet

import amongus.base_packets
import amongus.enums
import amongus.fields
import amongus.meeting_hud_vote
import amongus.messages
import amongus.player_info


@amongus.messages.sub_message_layer(amongus.enums.AmongUsMessageType.MSG_DATA_UPDATE)
class AmongUsDataMessage(scapy.packet.Packet):
    # The data type here depends on what it's sent to.
    name = "AmongUsDataMessage"
    fields_desc = [
        amongus.fields.PackedUInt32Field("net_id", 0x00),
    ]


initial_data_layers = {}


def _register_initial_data_layer(initial_data_layer):
    def _inner(cls):
        if initial_data_layer in initial_data_layers:
            raise Exception(
                "initial data layer {} already registered".format(initial_data_layer)
            )
        initial_data_layers[initial_data_layer] = cls
        return cls

    return _inner


data_layers = {}


def _register_data_layer(data_layer):
    def _inner(cls):
        if data_layer in data_layers:
            raise Exception("data layer {} already registered".format(data_layer))
        data_layers[data_layer] = cls
        return cls

    return _inner


@_register_initial_data_layer(
    amongus.enums.AmongUsInnerNetClients.CUSTOM_NETWORK_TRANSFORM
)
@_register_data_layer(amongus.enums.AmongUsInnerNetClients.CUSTOM_NETWORK_TRANSFORM)
class AmongUsDataCustomNetworkTransform(scapy.packet.Packet):
    name = "AmongUsDataCustomNetworkTransform"
    fields_desc = [
        scapy.fields.LEShortField("sequence_number", 0x00),
        scapy.fields.LEShortField("x", 0),
        scapy.fields.LEShortField("y", 0),
        scapy.fields.LESignedShortField("x_vel", 0),
        scapy.fields.LESignedShortField("y_vel", 0),
    ]


class PlayerInfoDataMessage(scapy.packet.Packet):
    name = "PlayerInfoDataMessage"
    fields_desc = [
        scapy.fields.ByteField("player_id", 0),
    ]


scapy.packet.bind_layers(PlayerInfoDataMessage, amongus.player_info.PlayerInfo)


@_register_initial_data_layer(amongus.enums.AmongUsInnerNetClients.GAME_DATA)
class AmongUsDataGameDataInitial(scapy.packet.Packet):
    name = "AmongUsDataGameDataInitial"
    fields_desc = [
        amongus.fields.PackedUInt32Field("player_count", 0, count_of="players"),
        scapy.fields.PacketListField(
            "players",
            None,
            cls=PlayerInfoDataMessage,
            count_from=lambda pkt: pkt.player_count,
        ),
    ]


@_register_initial_data_layer(amongus.enums.AmongUsInnerNetClients.MEETING_HUD)
class AmongUsDataMeetingHudInitial(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataMeetingHudInitial"
    fields_desc = [
        scapy.fields.PacketListField(
            "votes", None, cls=amongus.meeting_hud_vote.MeetingHudVote
        ),
    ]


@_register_data_layer(amongus.enums.AmongUsInnerNetClients.MEETING_HUD)
class AmongUsDataMeetingHud(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataMeetingHud"
    fields_desc = [
        amongus.fields.PackedUInt32FlagField("updated", []),
        scapy.fields.PacketListField(
            "votes",
            None,
            cls=amongus.meeting_hud_vote.MeetingHudVote,
            count_from=lambda pkt: len(pkt.updated),
        ),
    ]


class AmongUsDataReactorUser(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataReactorUser"
    fields_desc = [
        scapy.fields.ByteField("user_id", 0),
        scapy.fields.ByteField("console_id", 0),
    ]


class AmongUsDataReactorStatus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataReactorStatus"
    fields_desc = [
        scapy.fields.Field("countdown", 1000.0, "<f"),
        amongus.fields.PackedUInt32Field("user_cnt", 0, count_of="users"),
        scapy.fields.PacketListField(
            "users", [], cls=AmongUsDataReactorUser, count_from=lambda pkt: pkt.user_cnt
        ),
    ]


class AmongUsDataSwitchStatus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataSwitchStatus"
    fields_desc = [
        scapy.fields.ByteField("expected", 0),
        scapy.fields.ByteField("active", 0),
        scapy.fields.ByteField("value", 0),
    ]


class AmongUsDataLifeSupportCompletedConsole(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataLifeSupportCompletedConsole"
    fields_desc = [
        amongus.fields.PackedUInt32Field("console_id", 0),
    ]


class AmongUsDataLifeSupportStatus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataLifeSupportStatus"
    fields_desc = [
        scapy.fields.Field("countdown", 1000.0, "<f"),
        amongus.fields.PackedUInt32Field("completed_cnt", 0, count_of="completed"),
        scapy.fields.PacketListField(
            "completed",
            [],
            cls=AmongUsDataLifeSupportCompletedConsole,
            count_from=lambda pkt: pkt.completed_cnt,
        ),
    ]


class AmongUsDataMedScanStatus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataMedScanStatus"
    fields_desc = [
        amongus.fields.PackedUInt32Field("user_cnt", 0, length_of="users"),
        scapy.fields.XStrLenField("users", "", length_from=lambda pkt: pkt.user_cnt),
    ]


class AmongUsDataSecurityCameraStatus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataSecurityCameraStatus"
    fields_desc = [
        amongus.fields.PackedUInt32Field("user_cnt", 0, length_of="users"),
        scapy.fields.XStrLenField("users", "", length_from=lambda pkt: pkt.user_cnt),
    ]


class AmongUsDataHudOverrideStatus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataHudOverrideStatus"
    fields_desc = [
        scapy.fields.ByteField("active", 0),
    ]


class MiraHQActiveConsole(amongus.base_packets.NoPayloadPacket):
    name = "MiraHQActiveConsole"
    fields_desc = [
        scapy.fields.ByteField("console_id", 0),
        scapy.fields.ByteField("user_id", 0),  # ??? I think?
    ]


class AmongUsDataHudOverrideStatusMiraHQ(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataHudOverrideStatusMiraHQ"
    fields_desc = [
        amongus.fields.PackedUInt32Field(
            "active_consoles_cnt", 0, count_of="active_consoles"
        ),
        scapy.fields.PacketListField(
            "active_consoles",
            [],
            cls=MiraHQActiveConsole,
            count_from=lambda pkt: pkt.active_consoles_cnt,
        ),
        amongus.fields.PackedUInt32Field(
            "completed_consoles_cnt", 0, count_of="completed_consoles"
        ),
        scapy.fields.XStrLenField(
            "completed_consoles", "", length_from=lambda pkt: pkt.completed_consoles_cnt
        ),
    ]


class AmongUsDataDoorsStatusKeld(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataDoorsStatusKeld"
    fields_desc = [
        amongus.fields.PackedUInt32FlagField("updated", []),
        scapy.fields.XStrLenField(
            "doors_open", "", length_from=lambda pkt: len(pkt.updated)
        ),
    ]


class AmongUsDataDoorsStatusKeldInitial(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataDoorsStatusKeldInitial"
    fields_desc = [
        scapy.fields.XStrLenField("doors_open", "", length_from=lambda _: 13),
    ]


class PolusDoorTimer(amongus.base_packets.NoPayloadPacket):
    name = "PolusDoorTimer"
    fields_desc = [
        scapy.fields.ByteField("door_id", 0),
        scapy.fields.Field("timer", 1000.0, "<f"),
    ]


class AmongUsDataDoorsStatusPolus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataDoorsStatusPolus"
    fields_desc = [
        scapy.fields.ByteField("timer_cnt", 0),
        scapy.fields.PacketListField(
            "timers", [], cls=PolusDoorTimer, count_from=lambda pkt: pkt.timer_cnt
        ),
        scapy.fields.XStrLenField("doors_status", "", length_from=lambda pkt: 16),
    ]


class AmongUsDataSabotageStatus(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsDataSabotageStatus"
    fields_desc = [
        scapy.fields.Field("countdown", 1000.0, "<f"),
    ]


@_register_initial_data_layer(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_KELD)
class AmongUsDataShipStatusKeldInitial(scapy.packet.Packet):
    name = "AmongUsDataShipStatusKeldInitial"
    fields_desc = [
        scapy.fields.PacketField("reactor", default=None, cls=AmongUsDataReactorStatus),
        scapy.fields.PacketField("switch", default=None, cls=AmongUsDataSwitchStatus),
        scapy.fields.PacketField(
            "life_support", default=None, cls=AmongUsDataLifeSupportStatus
        ),
        scapy.fields.PacketField(
            "med_scan", default=None, cls=AmongUsDataMedScanStatus
        ),
        scapy.fields.PacketField(
            "security_camera", default=None, cls=AmongUsDataSecurityCameraStatus
        ),
        scapy.fields.PacketField(
            "hud_override", default=None, cls=AmongUsDataHudOverrideStatus
        ),
        scapy.fields.PacketField(
            "doors", default=None, cls=AmongUsDataDoorsStatusKeldInitial
        ),
        scapy.fields.PacketField(
            "sabotage", default=None, cls=AmongUsDataSabotageStatus
        ),
    ]
    initial = True


@_register_data_layer(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_KELD)
class AmongUsDataShipStatusKeld(AmongUsDataShipStatusKeldInitial):
    name = "AmongUsDataShipStatusKeld"
    fields_desc = [
        amongus.fields.PackedUInt32FlagField("updated", []),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "reactor", default=None, cls=AmongUsDataReactorStatus
            ),
            0x3,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "switch", default=None, cls=AmongUsDataSwitchStatus
            ),
            0x7,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "life_support", default=None, cls=AmongUsDataLifeSupportStatus
            ),
            0x8,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "med_scan", default=None, cls=AmongUsDataMedScanStatus
            ),
            0xA,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "security_camera", default=None, cls=AmongUsDataSecurityCameraStatus
            ),
            0xB,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "hud_override", default=None, cls=AmongUsDataHudOverrideStatus
            ),
            0xE,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "doors", default=None, cls=AmongUsDataDoorsStatusKeld
            ),
            0x10,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "sabotage", default=None, cls=AmongUsDataSabotageStatus
            ),
            0x11,
        ),
    ]
    initial = False


@_register_initial_data_layer(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_MIRA_HQ)
class AmongUsDataShipStatusMiraHQInitial(scapy.packet.Packet):
    name = "AmongUsDataShipStatusMiraHQInitial"
    fields_desc = [
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "reactor", default=None, cls=AmongUsDataReactorStatus
            ),
            0x3,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "switch", default=None, cls=AmongUsDataSwitchStatus
            ),
            0x7,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "life_support", default=None, cls=AmongUsDataLifeSupportStatus
            ),
            0x8,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "med_scan", default=None, cls=AmongUsDataMedScanStatus
            ),
            0xA,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "hud_override", default=None, cls=AmongUsDataHudOverrideStatusMiraHQ
            ),
            0xE,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "sabotage", default=None, cls=AmongUsDataSabotageStatus
            ),
            0x11,
        ),
    ]
    initial = True


@_register_data_layer(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_MIRA_HQ)
class AmongUsDataShipStatusMiraHQ(AmongUsDataShipStatusMiraHQInitial):
    name = "AmongUsDataShipStatusMiraHQ"
    fields_desc = [
        amongus.fields.PackedUInt32FlagField("updated", []),
    ] + AmongUsDataShipStatusMiraHQInitial.fields_desc
    initial = False


@_register_initial_data_layer(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_POLUS)
class AmongUsDataShipStatusPolusInitial(scapy.packet.Packet):
    name = "AmongUsDataShipStatusPolusInitial"
    fields_desc = [
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "switch", default=None, cls=AmongUsDataSwitchStatus
            ),
            0x7,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "med_scan", default=None, cls=AmongUsDataMedScanStatus
            ),
            0xA,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "security_camera", default=None, cls=AmongUsDataSecurityCameraStatus
            ),
            0xB,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "hud_override", default=None, cls=AmongUsDataHudOverrideStatus
            ),
            0xE,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "doors", default=None, cls=AmongUsDataDoorsStatusPolus
            ),
            0x10,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "sabotage", default=None, cls=AmongUsDataSabotageStatus
            ),
            0x11,
        ),
        amongus.fields.OptField(
            scapy.fields.PacketField(
                "reactor", default=None, cls=AmongUsDataReactorStatus
            ),
            0x15,
        ),
    ]
    initial = True


@_register_data_layer(amongus.enums.AmongUsInnerNetClients.SHIP_STATUS_POLUS)
class AmongUsDataShipStatusPolus(AmongUsDataShipStatusPolusInitial):
    name = "AmongUsDataShipStatusPolus"
    fields_desc = [
        amongus.fields.PackedUInt32FlagField("updated", []),
    ] + AmongUsDataShipStatusPolusInitial.fields_desc
    initial = False


@_register_data_layer(amongus.enums.AmongUsInnerNetClients.PLAYER_CONTROL)
class AmongUsDataPlayerControl(scapy.packet.Packet):
    name = "AmongUsDataPlayerControl"
    fields_desc = [
        scapy.fields.ByteField("player_id", 0),
    ]


@_register_initial_data_layer(amongus.enums.AmongUsInnerNetClients.PLAYER_CONTROL)
class AmongUsDataPlayerControlInitial(scapy.packet.Packet):
    name = "AmongUsDataPlayerControlInitial"
    fields_desc = [
        scapy.fields.ByteField("is_new", 0),
        scapy.fields.ByteField("player_id", 0),
    ]
