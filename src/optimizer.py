def _waste(class_students, room_capacity):
    return room_capacity - class_students


def optimize_room_allocation_for_slot(classes_in_slot, rooms):


    max_capacity = max((r["capacity"] for r in rooms), default=0)
    feasible_classes = [c for c in classes_in_slot if c["students"] <= max_capacity]
    unresolved = [c["id"] for c in classes_in_slot if c["students"] > max_capacity]

    if not feasible_classes:
        return {}, unresolved

    # Sort ascending, as required by the DP's correctness argument above.
    classes_sorted = sorted(feasible_classes, key=lambda c: c["students"])
    rooms_sorted = sorted(rooms, key=lambda r: r["capacity"])

    n = len(classes_sorted)
    m = len(rooms_sorted)
    INF = float("inf")

    # dp[i][j] = min waste matching first i classes using first j rooms
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    for j in range(m + 1):
        dp[0][j] = 0

    # choice[i][j] records whether class i was matched to room j, for backtracking.
    choice = [[False] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        cls = classes_sorted[i - 1]
        for j in range(1, m + 1):
            room = rooms_sorted[j - 1]
            skip_room = dp[i][j - 1]
            take_room = INF
            if room["capacity"] >= cls["students"]:
                prev = dp[i - 1][j - 1]
                if prev != INF:
                    take_room = prev + _waste(cls["students"], room["capacity"])
            if take_room < skip_room:
                dp[i][j] = take_room
                choice[i][j] = True
            else:
                dp[i][j] = skip_room
                choice[i][j] = False

    # Backtrack to recover which room each class got.
    room_for_class = {}
    i, j = n, m
    while i > 0 and j > 0:
        if choice[i][j]:
            room_for_class[classes_sorted[i - 1]["id"]] = rooms_sorted[j - 1]["id"]
            i -= 1
            j -= 1
        else:
            j -= 1

    # Any classes the DP couldn't seat (ran out of rooms in this slot,
    # even though a big-enough room theoretically exists elsewhere)
    # go to unresolved too -- Stage 4 will try to move them to a
    # different slot/room combination.
    for cls in classes_sorted:
        if cls["id"] not in room_for_class:
            unresolved.append(cls["id"])

    return room_for_class, unresolved


def optimize_full_schedule(slot_assignment, classes, rooms):
    """
    Runs the DP independently for every time slot.

    slot_assignment: dict class_id -> slot_name (from Stage 2)
    classes: full class list
    rooms: full room list

    Returns:
        final_assignments: dict class_id -> {"room": room_id, "slot": slot_name}
        unresolved: list of class_ids that got a slot but no room
    """
    class_by_id = {c["id"]: c for c in classes}

    # Group classes by slot.
    classes_per_slot = {}
    for cid, slot in slot_assignment.items():
        classes_per_slot.setdefault(slot, []).append(class_by_id[cid])

    final_assignments = {}
    all_unresolved = []

    for slot, classes_in_slot in classes_per_slot.items():
        room_for_class, unresolved = optimize_room_allocation_for_slot(classes_in_slot, rooms)
        for cid, rid in room_for_class.items():
            final_assignments[cid] = {"room": rid, "slot": slot}
        all_unresolved.extend(unresolved)

    return final_assignments, all_unresolved


def total_wasted_capacity(final_assignments, classes, rooms):
    room_cap = {r["id"]: r["capacity"] for r in rooms}
    class_size = {c["id"]: c["students"] for c in classes}
    return sum(room_cap[info["room"]] - class_size[cid] for cid, info in final_assignments.items())


if __name__ == "__main__":
    import json
    from graph_engine import build_conflict_graph, welsh_powell_coloring, colors_to_time_slots

    with open("../data/constraints.json") as f:
        data = json.load(f)

    adjacency = build_conflict_graph(data["classes"], data["student_groups"])
    coloring, _ = welsh_powell_coloring(adjacency)
    slot_assignment, _ = colors_to_time_slots(coloring, data["time_slots"])

    final_assignments, unresolved = optimize_full_schedule(slot_assignment, data["classes"], data["rooms"])
    print(f"Rooms assigned: {len(final_assignments)}")
    print(f"Unresolved (needs backtracking): {unresolved}")
    print(f"Total wasted capacity: {total_wasted_capacity(final_assignments, data['classes'], data['rooms'])}")
