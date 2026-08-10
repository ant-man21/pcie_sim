"""Render the device tree declared in a topology YAML file as a Mermaid diagram.

This visualizes the static YAML shape itself (root ports, switches, downstream
ports, endpoints) -- the same tree topology.md sketches by hand -- so you can
sanity-check a topology before running enumeration against it. It does not
run enumeration and has no bus numbers, since the YAML doesn't have any on
purpose (see topology.yaml's header comment).

Usage:
    python3 visualize_topology.py [topology.yaml] [-o out.md]
"""

import argparse

import config_space as cs

_KIND_LABEL = {
    "root_port": "Root Port",
    "switch_upstream": "Switch",
    "switch_downstream": "Downstream Port",
    "endpoint": "Endpoint",
}


def _node_label(node: cs.Node) -> str:
    kind = _KIND_LABEL[node.kind]
    return f"{node.name}<br/>{kind}<br/>{hex(node.vendor_id)}:{hex(node.device_id)}"


def _children_of(node: cs.Node) -> list:
    if node.kind == "switch_upstream":
        return node.children
    if node.child is not None:
        return [node.child]
    return []


def _walk(node: cs.Node, node_id: str, lines: list, counter: list) -> None:
    lines.append(f'    {node_id}["{_node_label(node)}"]')
    for child in _children_of(node):
        counter[0] += 1
        child_id = f"N{counter[0]}"
        lines.append(f"    {node_id} --> {child_id}")
        _walk(child, child_id, lines, counter)


def generate_mermaid(yaml_path: str) -> str:
    root_ports = cs.load_topology(yaml_path)
    lines = ["graph TD", '    RC["Root Complex"]']
    counter = [0]
    for port in root_ports:
        counter[0] += 1
        node_id = f"N{counter[0]}"
        lines.append(f"    RC --> {node_id}")
        _walk(port, node_id, lines, counter)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_path", nargs="?", default="topology.yaml")
    parser.add_argument("-o", "--out", help="write a Mermaid-fenced markdown file instead of printing")
    args = parser.parse_args()

    diagram = generate_mermaid(args.yaml_path)
    if args.out:
        with open(args.out, "w") as f:
            f.write(f"```mermaid\n{diagram}\n```\n")
        print(f"wrote {args.out}")
    else:
        print(f"```mermaid\n{diagram}\n```")


if __name__ == "__main__":
    main()
