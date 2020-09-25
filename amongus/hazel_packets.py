# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields
import scapy.layers.inet
import scapy.packet

import amongus.base_packets
import amongus.enums


class Hazel(scapy.packet.Packet):
    name = "Hazel"
    fields_desc = [
        scapy.fields.ByteEnumField(
            "type",
            amongus.enums.HazelPacketType.NONE.value,
            amongus.enums.HazelPacketType.as_scapy_dict(),
        )
    ]


scapy.packet.bind_layers(scapy.layers.inet.UDP, Hazel, sport=22023)
scapy.packet.bind_layers(scapy.layers.inet.UDP, Hazel, dport=22023)

hazel_layer = amongus.base_packets.tagged_layer(Hazel, "type")


@hazel_layer(amongus.enums.HazelPacketType.PING)
class HazelPing(scapy.packet.Packet):
    name = "HazelPing"
    fields_desc = [
        scapy.fields.ShortField("id", 0x00),
    ]


@hazel_layer(amongus.enums.HazelPacketType.ACK)
class HazelAck(scapy.packet.Packet):
    name = "HazelAck"
    fields_desc = [
        scapy.fields.ShortField("id", 0x00),
        scapy.fields.ByteField("terminator", 0xFF),
    ]


@hazel_layer(amongus.enums.HazelPacketType.HELLO)
class HazelHello(scapy.packet.Packet):
    name = "HazelHello"
    fields_desc = [
        scapy.fields.ShortField("id", 0x00),
    ]


@hazel_layer(amongus.enums.HazelPacketType.DISCONNECT)
class HazelDisconnect(scapy.packet.Packet):
    name = "HazelDisconnect"
    fields_desc = []


@hazel_layer(amongus.enums.HazelPacketType.RELIABLE)
class HazelReliable(scapy.packet.Packet):
    name = "HazelReliable"
    fields_desc = [
        scapy.fields.ShortField("id", 0x00),
    ]


@hazel_layer(amongus.enums.HazelPacketType.NONE)
class HazelNone(scapy.packet.Packet):
    name = "HazelNone"
    fields_desc = []


class HazelMessage(scapy.packet.Packet):
    name = "HazelMessage"
    fields_desc = [
        scapy.fields.LenField("length", None, fmt="<H"),
        scapy.fields.ByteField("tag", 0x00),
    ]

    def extract_padding(self, s):
        return s[: self.length], s[self.length :]


scapy.packet.bind_layers(HazelReliable, HazelMessage)
scapy.packet.bind_layers(HazelNone, HazelMessage)
