# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields
import scapy.packet

import amongus.base_packets
import amongus.enums
import amongus.fields
import amongus.hazel_packets


class AmongUsSubMessage(scapy.packet.Packet):
    name = "AmongUsSubMessage"
    fields_desc = [
        scapy.fields.LenField("length", None, fmt="<H"),
        scapy.fields.ByteEnumField(
            "tag", None, amongus.enums.AmongUsMessageType.as_scapy_dict()
        ),
    ]

    def extract_padding(self, s):
        return s[: self.length], s[self.length :]


sub_message_layer = amongus.base_packets.tagged_layer(AmongUsSubMessage, "tag")


class AmongUsBroadcastMessage(scapy.packet.Packet):
    name = "AmongUsBroadcastMessage"
    fields_desc = [
        scapy.fields.XIntField("game_id", 0x00),
        scapy.fields.PacketListField("messages", None, cls=AmongUsSubMessage),
    ]


scapy.packet.bind_layers(
    amongus.hazel_packets.HazelMessage, AmongUsBroadcastMessage, tag=5
)


class AmongUsDirectedMessage(scapy.packet.Packet):
    name = "AmongUsDirectedMessage"
    fields_desc = [
        scapy.fields.XIntField("game_id", 0x00),
        amongus.fields.PackedUInt32Field("client_id", 0x00),
        scapy.fields.PacketListField("messages", None, cls=AmongUsSubMessage),
    ]


scapy.packet.bind_layers(
    amongus.hazel_packets.HazelMessage, AmongUsDirectedMessage, tag=6
)


# A few messages which aren't deserving of their own module.


@sub_message_layer(amongus.enums.AmongUsMessageType.MSG_CHANGE_SCENE)
class AmongUsChangeSceneMessage(scapy.packet.Packet):
    name = "AmongUsChangeSceneMessage"
    fields_desc = [
        amongus.fields.PackedUInt32Field("client_id", None),
        amongus.fields.SmallFieldLenField("scene_len", 0x00, count_of="scene"),
        scapy.fields.StrLenField("scene", None, length_from=lambda pkt: pkt.scene_len),
    ]


@sub_message_layer(amongus.enums.AmongUsMessageType.MSG_MARK_READY)
class AmongUsMarkReadyMessage(scapy.packet.Packet):
    name = "AmongUsMarkReadyMessage"
    fields_desc = [
        amongus.fields.PackedUInt32Field("client_id", None),
    ]
