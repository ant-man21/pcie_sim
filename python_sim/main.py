import config_space as cs

def main():
	sim = cs.ConfigSpace("topology.yaml")
	vendor_id = sim.read_config(0, 0, 0, cs.VENDOR_ID, 2) #root port 0
	print(hex(vendor_id))
	sim.write_config(0, 0, 0, cs.SECONDARY_BUS, 1, 1)
	vendor_id = sim.read_config(1, 0, 0, cs.VENDOR_ID, 2) #switch 0
	print(hex(vendor_id))



	sim.write_config(1, 0, 0, cs.SECONDARY_BUS, 1, 2)

	next_bus = 3
	for device in (0, 1, 2):
		vendor_id = sim.read_config(2, device, 0, cs.VENDOR_ID, 2)
		if vendor_id == 0xFFFF:
			print(str(device) + " no device")
			continue

		header_type = sim.read_config(2, device, 0, cs.HEADER_TYPE, 1)
		print(f"dev{device}: vendor={hex(vendor_id)} header_type={hex(header_type)}")

		if header_type != 0x01:
			continue		  # it's an endpoint -- nothing behind it, nothing to assign

		assigned_bus = next_bus
		sim.write_config(2, device, 0, cs.SECONDARY_BUS, 1, assigned_bus)
		next_bus += 1
		for j in range(0, 32):
			v = sim.read_config(assigned_bus, j, 0, cs.BASE_CLASS, 2)
			if v == 0xFFFF:
				break
			print(f"bus{assigned_bus}: dev{j}: v={hex(v)}")

	# vendor_id = sim.read_config(0, 1, 0, cs.VENDOR_ID, 2)  # root_port 1
	# print(hex(vendor_id))
	# sim.write_config(0, 1, 0, cs.SECONDARY_BUS, 1, 5)
	# vendor_id = sim.read_config(5, 0, 0, cs.BASE_CLASS, 2)  # root_port 1
	# print(hex(vendor_id))

	# vendor_id = sim.read_config(0, 2, 0, cs.VENDOR_ID, 2)  # root_port 1
	# print(hex(vendor_id))
	# sim.write_config(0, 2, 0, cs.SECONDARY_BUS, 1, 6)
	# vendor_id = sim.read_config(6, 0, 0, cs.BASE_CLASS, 2)  # root_port 1
	# print(hex(vendor_id))


if __name__ == '__main__':
	main()