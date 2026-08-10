"""
ECAM-style config space simulator for the topology in topology.yaml.

This module is the connection point between the YAML and your enumeration
algorithm. It does NOT enumerate anything -- it only answers config-space
reads/writes the way real ECAM hardware would, based on whatever bus
numbers your algorithm has assigned so far. You write the walk (scan bus,
device, function; decide bridge vs. endpoint; recurse; size BARs); this
module is what your walk calls into instead of real MMIO.

Real ECAM address decode, for reference:
    address = ECAM_BASE + (bus << 20) + (device << 15) + (function << 12) + offset

You don't need that math here -- (bus, device, function, offset) IS the
decoded address; read_config()/write_config() take it directly.

    sim = ConfigSpace("topology.yaml")
    vendor_id = sim.read_config(bus=0, device=0, function=0, offset=0x00, size=2)

Key behaviors that mirror real hardware:
  - Nothing behind a bridge is visible until your code writes that bridge's
    Secondary Bus Number register (offset 0x19). That write is what
    "activates" the address range behind it -- same as real firmware.
  - Reading a (bus, device, function) where nothing is present returns all
    1s (0xFFFFFFFF truncated to size), which is how a master-abort looks
    on real hardware -- this is the signal your algorithm uses to know a
    device slot is empty and move on.
  - BAR sizing: write 0xFFFFFFFF to a BAR, then read it back -- you get an
    inverted size mask instead of an address. That's the real BAR-sizing
    trick, same one your bare-metal UEFI app does by hand.

Known simplification: BARs marked kind="mem64" are modeled as a single
32-bit slot here (fine for the sub-4GB sizes in topology.yaml). Real
64-bit BARs consume two consecutive BAR slots (a second all-1s dword
above the address). Extend Node/Bar if you need addresses above 4GB.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import yaml

# ---- config space register offsets (PCI header, common to type 0 and type 1) ----
VENDOR_ID       = 0x00  # 16 bit
DEVICE_ID       = 0x02  # 16 bit
COMMAND         = 0x04  # 16 bit
STATUS          = 0x06  # 16 bit
REVISION_ID     = 0x08  # 8 bit
PROG_IF         = 0x09  # 8 bit
SUBCLASS        = 0x0A  # 8 bit
BASE_CLASS      = 0x0B  # 8 bit
HEADER_TYPE     = 0x0E  # 8 bit (low 7 bits: 0x00 endpoint / 0x01 bridge)

BAR0            = 0x10  # type 0 (endpoint): BAR0-BAR5 at 0x10,0x14,0x18,0x1C,0x20,0x24
PRIMARY_BUS     = 0x18  # type 1 (bridge) only
SECONDARY_BUS   = 0x19  # type 1 only
SUBORDINATE_BUS = 0x1A  # type 1 only

HEADER_TYPE_ENDPOINT = 0x00
HEADER_TYPE_BRIDGE   = 0x01

NO_DEVICE_32 = 0xFFFFFFFF  # what a read returns when nothing answers (master abort)

_BAR_KIND_BITS = {"io": 0x1, "mem32": 0x0, "mem64": 0x4}


@dataclass
class Bar:
    size: int
    kind: str              # "mem32" | "mem64" | "io"
    prefetchable: bool = False
    address: int = 0        # assigned later by your algorithm via write_config
    sizing: bool = False    # True right after an all-1s write, until the next read


@dataclass
class Node:
    kind: str               # "root_port" | "switch_upstream" | "switch_downstream" | "endpoint"
    name: str
    vendor_id: int
    device_id: int
    base_class: int = 0x06  # bridges default to 06/04 (PCI-to-PCI bridge)
    sub_class: int = 0x04
    prog_if: int = 0x00
    bars: list = field(default_factory=list)
    child: Optional["Node"] = None            # single device behind a root/downstream port
    children: list = field(default_factory=list)  # switch downstream ports, index = device #
    secondary_bus: Optional[int] = None
    subordinate_bus: Optional[int] = None

    @property
    def is_bridge(self) -> bool:
        return self.kind in ("root_port", "switch_upstream", "switch_downstream")

    @property
    def header_type(self) -> int:
        return HEADER_TYPE_BRIDGE if self.is_bridge else HEADER_TYPE_ENDPOINT


def _parse_endpoint(raw: dict) -> Node:
    bars = [
        Bar(size=b["size"], kind=b["kind"], prefetchable=b.get("prefetchable", False))
        for b in raw.get("bars", [])
    ]
    return Node(
        kind="endpoint",
        name=raw["name"],
        vendor_id=raw["vendor_id"],
        device_id=raw["device_id"],
        base_class=raw.get("base_class", 0),
        sub_class=raw.get("sub_class", 0),
        prog_if=raw.get("prog_if", 0),
        bars=bars,
    )


def _parse_connects_to(raw: dict) -> Node:
    if raw["type"] == "endpoint":
        return _parse_endpoint(raw)
    if raw["type"] == "switch":
        upstream = Node(
            kind="switch_upstream",
            name=raw["name"],
            vendor_id=raw["vendor_id"],
            device_id=raw["device_id"],
        )
        upstream.children = [_parse_downstream_port(p) for p in raw["downstream_ports"]]
        return upstream
    raise ValueError(f"unknown connects_to type: {raw['type']}")


def _parse_downstream_port(raw: dict) -> Node:
    port = Node(
        kind="switch_downstream",
        name=raw["name"],
        vendor_id=raw.get("vendor_id", 0x10B5),
        device_id=raw.get("device_id", 0x8747),
    )
    port.child = _parse_connects_to(raw["connects_to"])
    return port


def load_topology(path: str) -> list:
    """Returns the list of root-port Nodes: bus 0, device index = list index."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    root_ports = []
    for rp in raw["root_complex"]["root_ports"]:
        port = Node(
            kind="root_port",
            name=rp["name"],
            vendor_id=rp["vendor_id"],
            device_id=rp["device_id"],
        )
        port.child = _parse_connects_to(rp["connects_to"])
        root_ports.append(port)
    return root_ports


class ConfigSpace:
    """Simulated ECAM. Talks in (bus, device, function, offset, size) like real MMIO."""

    def __init__(self, yaml_path: str):
        self.root_ports = load_topology(yaml_path)
        self._map = {(0, i, 0): port for i, port in enumerate(self.root_ports)}

    def _activate(self, node: Node, new_bus: int) -> None:
        """Called when your code writes a bridge's Secondary Bus Number.
        Exposes whatever is behind that bridge at the new bus number."""
        node.secondary_bus = new_bus
        if node.kind == "switch_upstream":
            for i, dp in enumerate(node.children):
                self._map[(new_bus, i, 0)] = dp
        elif node.child is not None:
            self._map[(new_bus, 0, 0)] = node.child

    def read_config(self, bus: int, device: int, function: int, offset: int, size: int) -> int:
        node = self._map.get((bus, device, function))
        if node is None:
            return NO_DEVICE_32 & ((1 << (size * 8)) - 1)

        if offset == VENDOR_ID:
            return node.vendor_id
        if offset == DEVICE_ID:
            return node.device_id
        if offset == HEADER_TYPE:
            return node.header_type
        if offset == BASE_CLASS:
            return node.base_class
        if offset == SUBCLASS:
            return node.sub_class
        if offset == PROG_IF:
            return node.prog_if

        if node.is_bridge:
            if offset == SECONDARY_BUS:
                return node.secondary_bus or 0
            if offset == SUBORDINATE_BUS:
                return node.subordinate_bus or 0
        elif BAR0 <= offset < BAR0 + 4 * len(node.bars):
            idx = (offset - BAR0) // 4
            bar = node.bars[idx]
            flags = _BAR_KIND_BITS[bar.kind] | (0x8 if bar.prefetchable else 0)
            if bar.sizing:
                bar.sizing = False  # trick is one-shot, like real hardware
                mask = (~(bar.size - 1)) & 0xFFFFFFFF
                return (mask & 0xFFFFFFF0) | flags
            return (bar.address & 0xFFFFFFF0) | flags
        return 0

    def write_config(self, bus: int, device: int, function: int, offset: int, size: int, value: int) -> None:
        node = self._map.get((bus, device, function))
        if node is None:
            return  # writes to nothing present are dropped, like real hardware

        if node.is_bridge and offset == SECONDARY_BUS:
            self._activate(node, value)
            return
        if node.is_bridge and offset == SUBORDINATE_BUS:
            node.subordinate_bus = value
            return
        if (not node.is_bridge) and BAR0 <= offset < BAR0 + 4 * len(node.bars):
            idx = (offset - BAR0) // 4
            bar = node.bars[idx]
            if value == 0xFFFFFFFF:
                bar.sizing = True
            else:
                bar.address = value & 0xFFFFFFF0
            return
