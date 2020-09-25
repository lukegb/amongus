# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields

import amongus.base_packets
import amongus.fields


class MeetingHudVote(amongus.base_packets.NoPayloadPacket):
    name = "MeetingHudVote"
    fields_desc = [
        scapy.fields.BitField("is_dead", 0, 1),
        scapy.fields.BitField("has_voted", 0, 1),
        scapy.fields.BitField("was_reporter", 0, 1),
        scapy.fields.BitField("reserved", 0, 1),
        amongus.fields.VotedForField("voted_for"),
    ]
