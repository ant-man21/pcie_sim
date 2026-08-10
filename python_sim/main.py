import config_space as cs



def enumerate_pcie(curr_bus, next_bus, sim):
	
	for device in range(32):
		# print(curr_bus)
		if curr_bus == 255:
			return # too many buses. might be a dead check
		vendor_id = sim.read_config(curr_bus, device, 0, cs.VENDOR_ID, 2)
		if vendor_id == 0xffff:
			continue
		else:
			#real device
			header_type = sim.read_config(curr_bus, device, 0, cs.HEADER_TYPE, 2)
			print(f"bus{curr_bus}:dev{device}: venid: {hex(vendor_id)} header_type: {hex(header_type)}")
			if header_type == 0x01: #bus
				assigned_bus = next_bus
				sim.write_config(curr_bus, device, 0, cs.SECONDARY_BUS, 1, next_bus)
				next_bus = assigned_bus + 1
				next_bus = enumerate_pcie(assigned_bus, next_bus, sim)
			else: #header_type == 0x00 probably?
				base_class = sim.read_config(curr_bus, device, 0, cs.BASE_CLASS, 2)
				sub_class = sim.read_config(curr_bus, device, 0, cs.SUBCLASS, 2)
				print(f"bus{curr_bus}:dev{device}: venid: {hex(vendor_id)} class: {hex(base_class)}:{hex(sub_class)} ")
				pass
	return next_bus

def main():
	curr_bus = 0
	next_bus = curr_bus + 1
	sim = cs.ConfigSpace("topology.yaml")
	enumerate_pcie(curr_bus, next_bus, sim)

if __name__ == '__main__':
	main()