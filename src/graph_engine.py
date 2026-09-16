from collections import defaultdict


def build_conflict_graph(classes, student_groups):
    """
    Returns adjacency dict: class_id -> set of conflicting class_ids.
    """
    class_ids = [c["id"] for c in classes]
    professor_of = {c["id"]: c["professor"] for c in classes}
    adjacency = {cid: set() for cid in class_ids}

    # Edge type 1: same professor.
    by_professor = defaultdict(list)
    for cid, prof in professor_of.items():
        by_professor[prof].append(cid)
    for prof, cids in by_professor.items():
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                adjacency[cids[i]].add(cids[j])
                adjacency[cids[j]].add(cids[i])

    # Edge type 2: shared student group.
    for group, cids in student_groups.items():
        cids = [c for c in cids if c in adjacency]  # ignore unknown ids defensively
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                adjacency[cids[i]].add(cids[j])
                adjacency[cids[j]].add(cids[i])

    return adjacency


def welsh_powell_coloring(adjacency):
    """
    Welsh-Powell graph coloring.

    Returns:
        coloring: dict class_id -> color index (0, 1, 2, ...)
        num_colors: total distinct colors used
    """
    # Sort nodes by degree, descending.
    nodes_by_degree = sorted(adjacency.keys(), key=lambda n: len(adjacency[n]), reverse=True)

    coloring = {}
    for node in nodes_by_degree:
        used_colors = {coloring[neighbor] for neighbor in adjacency[node] if neighbor in coloring}
        color = 0
        while color in used_colors:
            color += 1
        coloring[node] = color

    num_colors = (max(coloring.values()) + 1) if coloring else 0
    return coloring, num_colors


def colors_to_time_slots(coloring, time_slots):
    """
    Maps each color index to an actual time-slot name.
    If more colors are needed than available time slots, the extra
    colors wrap around is NOT done automatically here -- that would
    silently reintroduce conflicts. Instead we report the shortfall so
    the caller (main.py) can hand the overflow classes to Stage 4
    (backtracking) as "best effort" cases.

    Returns:
        slot_assignment: dict class_id -> slot_name (only for classes
                          whose color fits within available time_slots)
        overflow_classes: list of class_ids whose color index has no
                           corresponding time slot
    """
    slot_assignment = {}
    overflow_classes = []
    for cid, color in coloring.items():
        if color < len(time_slots):
            slot_assignment[cid] = time_slots[color]
        else:
            overflow_classes.append(cid)
    return slot_assignment, overflow_classes


def compare_to_greedy(greedy_unplaced, overflow_classes, num_colors, num_time_slots):
    """
    Produces a short comparison summary (string) between the Stage 1
    greedy result and the Stage 2 graph-coloring result.
    """
    lines = []
    lines.append(f"Graph coloring needed {num_colors} distinct time slots "
                  f"(available: {num_time_slots}).")
    lines.append(f"Greedy baseline left {len(greedy_unplaced)} class(es) completely unplaced.")
    if overflow_classes:
        # Color indexes are zero-based, while this is a human-facing slot number.
        first_missing_slot = num_time_slots + 1
        lines.append(f"Graph coloring left {len(overflow_classes)} class(es) without a "
                     f"conflict-free slot (the first unavailable slot would be "
                     f"#{first_missing_slot}).")
    else:
        lines.append("Graph coloring assigned every class to an available "
                     "conflict-free time slot.")
    if len(overflow_classes) < len(greedy_unplaced):
        lines.append("=> Graph coloring prevented more conflicts than the greedy baseline, "
                      "because it looks at the WHOLE conflict structure at once (via node "
                      "degree ordering) instead of committing to placements one class at a "
                      "time without ever revisiting them.")
    elif len(overflow_classes) == len(greedy_unplaced) == 0:
        lines.append("=> Both approaches found a fully conflict-free arrangement for this "
                      "dataset; graph coloring's advantage would show up on a denser, more "
                      "constrained dataset.")
    else:
        lines.append("=> On this particular dataset the two approaches performed similarly; "
                      "graph coloring's real advantage is structural (guaranteed zero hard "
                      "conflicts among colored classes) rather than raw placement count.")
    return "\n".join(lines)


if __name__ == "__main__":
    import json

    with open("../data/constraints.json") as f:
        data = json.load(f)

    adjacency = build_conflict_graph(data["classes"], data["student_groups"])
    coloring, num_colors = welsh_powell_coloring(adjacency)
    slot_assignment, overflow = colors_to_time_slots(coloring, data["time_slots"])

    print(f"Chromatic number found (Welsh-Powell): {num_colors}")
    print(f"Classes successfully time-slotted: {len(slot_assignment)}")
    print(f"Overflow (no available slot): {overflow}")
