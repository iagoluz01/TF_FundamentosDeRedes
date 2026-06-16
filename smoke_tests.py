#!/usr/bin/env python3
from ring_node import (
    DATA,
    STATUS_UNKNOWN,
    Config,
    DataPacket,
    corrupt_message,
    crc32_text,
    parse_float,
)


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main():
    config = Config.from_file("config.example.txt")
    assert_equal(config.nickname, "B", "nickname")
    assert_equal(config.hop_delay, 2.0, "hop_delay")
    assert_equal(config.error_rate, 0.2, "error_rate")
    assert_equal(config.token_timeout, 2.5, "token_timeout")
    assert_equal(config.min_token_interval, 2.0, "min_token_interval")
    assert_equal(parse_float("2,5"), 2.5, "comma float")

    message = "Oi pessoal: teste com dois pontos"
    packet = DataPacket(
        origin="B",
        destination="A",
        status=STATUS_UNKNOWN,
        crc=crc32_text(message),
        message=message,
    )
    parsed = DataPacket.parse(packet.wire())
    assert_equal(parsed.origin, "B", "packet origin")
    assert_equal(parsed.destination, "A", "packet destination")
    assert_equal(parsed.status, STATUS_UNKNOWN, "packet status")
    assert_equal(parsed.message, message, "packet message")

    damaged = corrupt_message(message)
    if damaged == message:
        raise AssertionError("corrupt_message did not change the message")
    if crc32_text(damaged) == packet.crc:
        raise AssertionError("CRC should change after message corruption")

    try:
        DataPacket.parse(f"{DATA}:B:A:{STATUS_UNKNOWN}:not-a-number:msg")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid CRC was accepted")

    print("smoke tests ok")


if __name__ == "__main__":
    main()
