# pcie_sim Repository
PCIe enumeration and config space, three ways: an EDK2-protocol UEFI app, a bare-metal UEFI app that walks config space and sizes a BAR manually, and a Python topology/enumeration simulator.

## Purpose for this Project
I want to learn more about PCIe for my job. I have a basic understanding from work, but writing some tools to see how PCIe devices get enumerated on a system, and simulating a whole PCIe topology, will help visualize what's going on during enumeration.

## Components of this project
I will have 3 tools, as stated above.

The configurable topology/enumeration sim: you can configure your own root complex, root ports, switches, and end devices with names via YAML, and the Python sim will enumerate it, assign bus/device/function numbers, configure BARs, and publish a table of required MMIO space. You can then type an address and it will highlight which device was selected.

For a deeper learning exercise, PcieBareMetalApp will implement part of the enumeration that PciBusDxe does in EDK2. It will discover devices using the ECAM base and publish all the Vendor IDs it finds. Then it will size one BAR on one device and reassign it. Reassigning a BAR moves the device's decode window — the address PciBusDxe originally configured stops working the moment this happens, which will break boot. That's intentional: this app is for understanding bare-metal config access, not a working replacement enumerator. I would not recommend running this on anything other than QEMU — it serves no useful purpose on real hardware.

For practical use, PcieDiagApp will be built to publish the PCIe tree (the `pci` Shell command does the same thing), and will additionally publish the MMIO address spaces and the MCFG ACPI table used during enumeration, directly in the UEFI Shell.

## How to run this project
1. Python setup: TODO
2. UEFI app setup: TODO

## AI Disclaimer
My buddy Claude will help out to optimize development speed and fix bugs. But this is my project and my design.