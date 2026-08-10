# pcie_sim Repository
PCIe enumeration and config space, three ways: an EDK2-protocol UEFI app, a bare-metal UEFI app that walks config space and sizes a BAR manually, and a Python topology/enumeration simulator.

## Purpose for this Project
I want to learn more about PCIe from my job. I have a basic understanding form work but writing some tools to see how PCIe devices get enumurated on a system and simulating a whole PCIe Topology will help visualize what is going on during enumeration.

## Components of this project
I will have 3 tools as stated above. The configurable topology/enumeration sim. You can configure your own root complex, root ports, switches and end devices with names via the YAML and the python sim will enumurate it and assign bus, device, function numbers, configure its BARs, and publish a table for required MMIO space. Then you can type an address and highlight what device was selected.

For better learning exersise, the PcieBareMetalApp, will implement part of the enmuration that PciBusDxe does in EDK2. It will discover devices using the ECAM Base and publish all the Ven IDs it finds. then it will size 1 bar on 1 device. It will break boot, but this is for baremetal understanding not a bare metal enumeration app. I would not recommend to run this on anything other than QEMU it serves no useful purpose on real hardware.

For practical use, PcieDiagApp will be built to publish PCIe tree (pci command does the same thing) in addition publish the same MMIO address spaces in UEFI shell. The project will also hopefully publish he MCFG ACPI table used for the enumeration. idk how far I will and how much I can publish for this realistically.

## How to run this project
1. python setup TODO
2. UEFI app run setup TODO

## AI Disclaimer
My buddy Claude will help out to optimize development speed and fix bugs. But this is my project and my design.