# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields

import amongus.base_packets
import amongus.fields


class PlayerInfoTask(amongus.base_packets.NoPayloadPacket):
    name = "PlayerInfoTask"
    fields_desc = [
        amongus.fields.PackedUInt32Field("task_id", 0),
        scapy.fields.ByteField("task_done", 0),
    ]


class PlayerInfo(amongus.base_packets.NoPayloadPacket):
    name = "PlayerInfo"
    fields_desc = [
        amongus.fields.SmallFieldLenField(
            "player_name_len", 0x00, count_of="player_name"
        ),
        scapy.fields.StrLenField(
            "player_name", None, length_from=lambda pkt: pkt.player_name_len
        ),
        scapy.fields.ByteField("color_id", 0),
        amongus.fields.PackedUInt32Field("hat_id", 0),
        amongus.fields.PackedUInt32Field("pet_id", 0),
        amongus.fields.PackedUInt32Field("skin_id", 0),
        scapy.fields.BitField("reserved", 0, 5),
        scapy.fields.BitField("is_dead", 0, 1),
        scapy.fields.BitField("is_impostor", 0, 1),
        scapy.fields.BitField("disconnected", 0, 1),
        amongus.fields.SmallFieldLenField("task_count", 0, count_of="tasks"),
        scapy.fields.PacketListField(
            "tasks", None, count_from=lambda pkt: pkt.task_count, cls=PlayerInfoTask
        ),
    ]
