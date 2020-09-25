# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields
import scapy.packet


class GameOptions(scapy.packet.Packet):
    name = "GameOptions"
    fields_desc = [
        scapy.fields.ByteField("version", 3),
        scapy.fields.ByteField("max_players", 10),
        scapy.fields.LEIntField("keywords", 0x01),
        scapy.fields.ByteEnumField("map", 0, {0: "skeld", 1: "mira_hq", 2: "polus"}),
        scapy.fields.Field("player_speed", 1.0, "<f"),
        scapy.fields.Field("player_vision", 1.0, "<f"),
        scapy.fields.Field("imposter_vision", 1.0, "<f"),
        scapy.fields.Field("kill_cooldown", 45.0, "<f"),
        scapy.fields.ByteField("common_tasks", 1),
        scapy.fields.ByteField("long_tasks", 1),
        scapy.fields.ByteField("short_tasks", 2),
        scapy.fields.LEIntField("emergency_meetings", 0x01),
        scapy.fields.ByteField("imposter_count", 1),
        scapy.fields.ByteEnumField(
            "kill_distance", 1, {0: "short", 1: "medium", 2: "long"}
        ),
        scapy.fields.LEIntField("discussion_time", 15),
        scapy.fields.LEIntField("voting_time", 120),
        scapy.fields.ByteField("is_defaults", 1),
        scapy.fields.ByteField("emergency_cooldown", 0),
        scapy.fields.ByteField("confirm_ejects", 1),
        scapy.fields.ByteField("visual_tasks", 1),
    ]
