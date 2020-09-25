# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.packet


def tagged_layer(parent_packet, tag_name):
    def tagged(tag):
        def _wrap(cls):
            scapy.packet.bind_layers(parent_packet, cls, **{tag_name: tag.value})
            return cls

        return _wrap

    return tagged


class NoPayloadPacket(scapy.packet.Packet):
    def extract_padding(self, s):
        return b"", s
