import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for 10 seconds... make sure the strap is on and active")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if d.name and "Polar" in d.name:
            print(f"Found: {d.name}  address={d.address}")
    print("Done.")

asyncio.run(main())