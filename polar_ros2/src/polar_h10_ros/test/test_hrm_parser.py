"""Unit tests for the HRM packet parser. No ROS or Bluetooth needed: `pytest test/`."""
import pytest

from polar_h10_ros.hrm_parser import parse_hrm


def test_polar_h10_typical_packet():
    # flags 0x16: uint8 HR, contact supported + detected, RR present
    s = parse_hrm(bytes([0x16, 0x48, 0x55, 0x03]))
    assert s.bpm == 72
    assert s.sensor_contact is True
    assert s.rr_intervals_s == pytest.approx((853 / 1024,))
    assert s.energy_expended_kj is None


def test_multiple_rr_intervals():
    s = parse_hrm(bytes([0x10, 0x50, 0x00, 0x04, 0x00, 0x02]))
    assert s.bpm == 80
    assert s.rr_intervals_s == pytest.approx((1.0, 0.5))


def test_no_rr_gives_empty_tuple():
    assert parse_hrm(bytes([0x06, 0x3C])).rr_intervals_s == ()


def test_uint16_heart_rate():
    s = parse_hrm(bytes([0x01, 0x2C, 0x01]))  # 0x012C = 300
    assert s.bpm == 300


def test_contact_supported_but_not_detected():
    assert parse_hrm(bytes([0x04, 0x3C])).sensor_contact is False


def test_contact_not_supported_is_none():
    # bit 1 alone is meaningless without bit 2
    assert parse_hrm(bytes([0x02, 0x3C])).sensor_contact is None


def test_energy_field_is_skipped_before_rr():
    # flags: energy (0x08) + RR (0x10); energy = 0x0102, RR = 1024 -> 1.0 s
    s = parse_hrm(bytes([0x18, 0x3C, 0x02, 0x01, 0x00, 0x04]))
    assert s.energy_expended_kj == 0x0102
    assert s.rr_intervals_s == pytest.approx((1.0,))


@pytest.mark.parametrize('packet', [
    b'',
    bytes([0x16]),
    bytes([0x01, 0x2C]),            # uint16 HR missing a byte
    bytes([0x08, 0x3C, 0x01]),      # energy missing a byte
    bytes([0x10, 0x3C, 0x55]),      # odd RR byte count
])
def test_malformed_packets_raise(packet):
    with pytest.raises(ValueError):
        parse_hrm(packet)
