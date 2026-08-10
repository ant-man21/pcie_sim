**Topology** = the physical/logical shape of how PCIe devices connect to each other. In PCIe specifically: a tree rooted at the Root Complex (CPU/memory interface), branching through optional Switches (each with one upstream port and multiple downstream ports), terminating in Endpoints (NICs, GPUs, NVMe drives, etc.) or Bridges to other buses. Enumeration is the software process (BIOS/OS) walking that tree via config-space reads to discover bus/device/function numbers and assign resources.

Example Flow:
```mermaid
graph TD
    RC["Root Complex<br/>bus 0"] --> SW["Switch<br/>bus 1"]
    SW --> EP1["NVMe SSD<br/>bus 2, dev 0"]
    SW --> EP2["Ethernet<br/>bus 3, dev 0"]
    RC --> EP3["NIC<br/>bus 4, dev 0"]
    RC --> EP4["GPU<br/>bus 5, dev 0"]
```

Edit node labels/structure however you like (add more switches, nested branches, multi-function devices like `dev 0, fn 0/1`). When you paste your version back, I'll check it for structural issues (e.g., switch needing exactly one upstream port, valid bus numbering, dangling nodes) and convert it into a YAML device tree for your sim.

Paste your mermaid whenever it's ready.