"""Parser for the Bluetooth GATT Heart Rate Measurement (HRM) characteristic (0x2A37).

Every BLE heart-rate strap, Polar H10 included, sends this same packet format
as a notification, roughly once per second. This module turns the raw bytes
into an `HrmSample`. It has no ROS or BLE imports so it can be unit-tested
with plain pytest.

Packet layout (all multi-byte fields are little-endian):

    byte 0          flags
      bit 0         HR value format: 0 = uint8, 1 = uint16
      bit 1         sensor contact detected  (only meaningful if bit 2 is set)
      bit 2         sensor contact feature supported
      bit 3         energy expended field present (uint16, kJ)
      bit 4         RR-interval fields present
      bits 5-7      reserved
    byte 1 (or 1-2) heart rate in BPM
    next 2 bytes    energy expended, only if bit 3
    rest            zero or more uint16 RR intervals, only if bit 4,
                    in units of 1/1024 s

Example from a Polar H10: 16 48 55 03
    flags 0x16 = 0b0001_0110 -> uint8 HR, contact supported AND detected, RR present
    0x48 = 72 BPM
    0x0355 = 853 -> 853 / 1024 = 0.833 s between beats (= 72 BPM)
"""
from dataclasses import dataclass
from typing import Optional, Tuple

FLAG_HR_UINT16 = 0x01
FLAG_CONTACT_DETECTED = 0x02
FLAG_CONTACT_SUPPORTED = 0x04
FLAG_ENERGY_PRESENT = 0x08
FLAG_RR_PRESENT = 0x10

RR_UNITS_PER_SECOND = 1024.0


@dataclass(frozen=True)
class HrmSample:
    bpm: int
    rr_intervals_s: Tuple[float, ...]
    # None when the sensor does not support contact detection (flag bit 2 clear).
    sensor_contact: Optional[bool]
    energy_expended_kj: Optional[int]


def parse_hrm(data: bytes) -> HrmSample:
    """Parse one HRM notification payload. Raises ValueError on a malformed packet."""
    data = bytes(data)
    if len(data) < 2:
        raise ValueError(f'HRM packet too short ({len(data)} bytes): {data.hex()}')

    flags = data[0]
    i = 1

    if flags & FLAG_HR_UINT16:
        _require(data, i, 2, 'uint16 heart rate')
        bpm = int.from_bytes(data[i:i + 2], 'little')
        i += 2
    else:
        bpm = data[i]
        i += 1

    if flags & FLAG_CONTACT_SUPPORTED:
        sensor_contact = bool(flags & FLAG_CONTACT_DETECTED)
    else:
        sensor_contact = None

    # Energy expended sits between HR and RR; it must be skipped even though we
    # don't publish it, otherwise the RR values would be read from the wrong offset.
    energy = None
    if flags & FLAG_ENERGY_PRESENT:
        _require(data, i, 2, 'energy expended')
        energy = int.from_bytes(data[i:i + 2], 'little')
        i += 2

    rr = ()
    if flags & FLAG_RR_PRESENT:
        rest = data[i:]
        if len(rest) % 2:
            raise ValueError(f'odd number of RR bytes ({len(rest)}): {data.hex()}')
        rr = tuple(
            int.from_bytes(rest[j:j + 2], 'little') / RR_UNITS_PER_SECOND
            for j in range(0, len(rest), 2)
        )

    return HrmSample(bpm=bpm, rr_intervals_s=rr, sensor_contact=sensor_contact,
                     energy_expended_kj=energy)


def _require(data: bytes, offset: int, size: int, what: str) -> None:
    if len(data) < offset + size:
        raise ValueError(f'HRM packet truncated reading {what}: {data.hex()}')
