# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields
import scapy.packet

import amongus.base_packets
import amongus.enums
import amongus.fields
import amongus.messages


class AmongUsSpawnChild(amongus.base_packets.NoPayloadPacket):
    name = "AmongUsSpawnChild"
    fields_desc = [
        amongus.fields.PackedUInt32Field("net_id", None),
        scapy.fields.FieldLenField("msg_len", None, count_of="msg", fmt="<H"),
        scapy.fields.ByteField("tag", 0x00),
        scapy.fields.XStrLenField("msg", "", length_from=lambda pkt: pkt.msg_len),
    ]


@amongus.messages.sub_message_layer(amongus.enums.AmongUsMessageType.MSG_SPAWN)
class AmongUsSpawnMessage(scapy.packet.Packet):
    name = "AmongUsSpawnMessage"
    fields_desc = [
        amongus.fields.PackedUInt32Field("spawnable_id", None),
        amongus.fields.PackedUInt32Field("owner_id", 0),
        scapy.fields.BitField("reserved", 0, 7),
        scapy.fields.BitField("is_client_character", 0, 1),
        amongus.fields.PackedUInt32Field("children_cnt", 0),
        scapy.fields.PacketListField(
            "children",
            None,
            cls=AmongUsSpawnChild,
            count_from=lambda pkt: pkt.children_cnt,
        ),
    ]


@amongus.messages.sub_message_layer(amongus.enums.AmongUsMessageType.MSG_DESPAWN)
class AmongUsDespawnMessage(scapy.packet.Packet):
    name = "AmongUsDespawnMessage"
    fields_desc = [amongus.fields.PackedUInt32Field("net_id", None)]
