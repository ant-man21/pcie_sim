import config_space as cs
import json
from dataclasses import dataclass, field
from dataclasses import asdict

@dataclass
class DiscoveredBar:
    index: int
    size: int
    kind: str            # decoded from the low bits of the sized-back value
    prefetchable: bool
    address: int = 0

@dataclass
class DiscoveredDevice:
    bus: int
    device: int
    function: int
    vendor_id: int
    device_id: int
    base_class: int
    sub_class: int
    bars: list = field(default_factory=list)
    secondary_bus: int = None
    subordinate_bus: int = None

def enumerate_pcie(curr_bus, next_bus, sim, device_list):
	
	for device in range(32):
		# print(curr_bus)
		if curr_bus == 255:
			return # too many buses.
		vendor_id = sim.read_config(curr_bus, device, 0, cs.VENDOR_ID, 2)
		bars = []
		secondary_bus = None
		subordinate_bus = None
		if vendor_id == 0xffff:
			continue
		else:
			#real device
			header_type = sim.read_config(curr_bus, device, 0, cs.HEADER_TYPE, 2)
			# print(f"bus{curr_bus}:dev{device}: venid: {hex(vendor_id)} header_type: {hex(header_type)}")
			#^these prints seem more in order. for debug
			if header_type == 0x01: #bus
				assigned_bus = next_bus
				sim.write_config(curr_bus, device, 0, cs.SECONDARY_BUS, 1, next_bus)
				next_bus = assigned_bus + 1
				next_bus = enumerate_pcie(assigned_bus, next_bus, sim, device_list)
				sim.write_config(curr_bus, device, 0, cs.SUBORDINATE_BUS, 1, next_bus-1)
				secondary_bus = assigned_bus
				subordinate_bus = next_bus - 1
			else: #header_type == 0x00 probably?
				#read bars here?
				for i in range(0,6):
					offset = cs.BAR0 + 4*i
					sim.write_config(curr_bus, device, 0, offset, 4, 0xFFFFFFFF)   # step 1: write all-1s
					raw = sim.read_config(curr_bus, device, 0, offset, 4)          # step 2: read back
					# print(f"bus{curr_bus}:dev{device}: bar{i} raw: {hex(raw)}") #more debug
					if raw == 0:
						break # no more BARs
					flags = raw & 0xF #grab first byte and read the flags for kind
					mask = raw & 0xFFFFFFF0 #grab the rest of the bits except the flags.
					bar = DiscoveredBar(
						index=i, #which of the 0-5 bars
						size=(~mask & 0xFFFFFFFF) + 1, #clear bits in mask and keep rest for size + 1
						kind="io" if flags & 0x1 else ("mem64" if flags & 0x4 else "mem32"), 
						prefetchable=bool(flags & 0x8)
					)
					bars.append(bar)
				pass
				# print(f"bus{curr_bus}:dev{device}: venid: {hex(vendor_id)} class: {hex(base_class)}:{hex(sub_class)}")
			device_list.append(
				DiscoveredDevice(
					bus=curr_bus,
					device=device,
					function=0,
					vendor_id=sim.read_config(curr_bus, device, 0, cs.VENDOR_ID, 2),
					device_id=sim.read_config(curr_bus, device, 0, cs.DEVICE_ID, 2),
					base_class=sim.read_config(curr_bus, device, 0, cs.BASE_CLASS, 2),
					sub_class=sim.read_config(curr_bus, device, 0, cs.SUBCLASS, 2),
					bars=bars,
					secondary_bus=secondary_bus,
					subordinate_bus=subordinate_bus,
				)
			)
			# print(f"bus{curr_bus}:dev{device}: venid: {hex(vendor_id)} class: {hex(base_class)}:{hex(sub_class)}")

	return next_bus

def main():
	curr_bus = 0
	next_bus = curr_bus + 1
	device_list = []
	sim = cs.ConfigSpace("topology.yaml")
	enumerate_pcie(curr_bus, next_bus, sim, device_list)
	# Convert dataclasses -> dictionaries -> JSON
	with open("devices_unsorted.json", "w") as f:
		json.dump(
			[asdict(device) for device in device_list],
			f,
			indent=2
		)
	device_list.sort(key=lambda d: (d.bus, d.device, d.function)) #in firmware do we just own the disorganized. can it be created sorted. no probably not.
	for device in device_list:
		print(
			f"{device.bus:02x}:{device.device:02x}.{device.function:x} "
			f"{device.vendor_id:04x}:{device.device_id:04x}"
		)
	# Convert dataclasses -> dictionaries -> JSON
	with open("devices.json", "w") as f:
		json.dump(
			[asdict(device) for device in device_list],
			f,
			indent=2
		)
if __name__ == '__main__':
	main()