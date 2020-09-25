# SPDX-FileCopyrightText: 2020 Luke Granger-Brown
#
# SPDX-License-Identifier: Apache-2.0

import scapy.fields


class VotedForField(scapy.fields.BitField):
    def __init__(self, name):
        super().__init__(name, 0, 4)

    def m2i(self, pkt, x):
        return super().m2i(pkt, x) - 1

    def i2m(self, pkt, x):
        return super().i2m(pkt, x + 1)


class PackedUInt32Field(scapy.fields.Field):
    def __init__(self, *args, length_of=None, count_of=None, **kwargs):
        super().__init__(*args, **kwargs)

    def i2m(self, pkt, val):
        out = []
        while val > 0x80:
            out.append(((val & 0x7F) | 0x80))
            val = val >> 7
        out.append((val))
        return bytes(out)

    def addfield(self, pkt, s, val):
        return s + self.i2m(pkt, val)

    def m2i(self, pkt, s):
        v = 0
        shift = 0
        for ch in s:
            if ch >= 0x80:
                ch ^= 0x80
            v |= ch << shift
            shift += 7
        return v

    def getfield(self, pkt, s):
        last_posn = None
        for posn, ch in enumerate(s):
            if ch < 0x80:
                last_posn = posn + 1
                break
        return s[last_posn:], self.m2i(pkt, s[:last_posn])


class PackedUInt32FlagField(PackedUInt32Field):
    def m2i(self, pkt, x):
        bits = []
        cnt = 0
        x = super().m2i(pkt, x)
        while x != 0:
            if (x & 0b1) != 0:
                bits.append(cnt)
            cnt += 1
            x = x >> 1
        return bits

    def i2m(self, pkt, bits):
        x = 0
        for b in bits:
            x |= 1 << b
        return super().i2m(pkt, x)


class SmallFieldLenField(scapy.fields.FieldLenField):
    def __init__(self, *args, **kwargs):
        kwargs["fmt"] = "B"
        super().__init__(*args, **kwargs)


class OptField(scapy.fields.ConditionalField):
    def __init__(self, fld, flag_byte):
        self.flag_byte = flag_byte
        super().__init__(fld, cond=self.cond)

    def cond(self, pkt):
        return pkt.initial or self.flag_byte in pkt.updated
