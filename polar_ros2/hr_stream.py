import asyncio
from bleak import BleakClient

ADDRESS = "B05FB458-A914-E3BE-880E-E0BCB7D41B2A"
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def parse_hr(data: bytearray):
    """Parse Bluetooth Heart Rate Measurement packet per GATT spec."""
    flags = data[0]
    hr_is_uint16 = flags & 0x01
    contact_supported = (flags >> 2) & 0x01
    contact_detected = (flags >> 1) & 0x01
    rr_present = (flags >> 4) & 0x01

    idx = 1
    if hr_is_uint16:
        bpm = int.from_bytes(data[idx:idx+2], "little")
        idx += 2
    else:
        bpm = data[idx]
        idx += 1

    # RR intervals come in units of 1/1024 second
    rr_intervals = []
    if rr_present:
        while idx + 1 < len(data):
            rr_raw = int.from_bytes(data[idx:idx+2], "little")
            rr_intervals.append(rr_raw / 1024.0)
            idx += 2

    return bpm, rr_intervals, contact_supported, contact_detected

def on_notify(_, data: bytearray):
    bpm, rrs, c_supp, c_det = parse_hr(data)
    rr_str = f" RR={rrs}" if rrs else ""
    contact = "contact-ok" if (not c_supp or c_det) else "no-contact"
    print(f"HR: {bpm} bpm  [{contact}]{rr_str}")

async def main():
    print(f"Connecting to {ADDRESS}...")
    async with BleakClient(ADDRESS) as client:
        print("Connected. Subscribing to heart rate notifications...")
        await client.start_notify(HR_MEASUREMENT_UUID, on_notify)
        print("Ctrl+C to stop.\n")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        await client.stop_notify(HR_MEASUREMENT_UUID)

asyncio.run(main())