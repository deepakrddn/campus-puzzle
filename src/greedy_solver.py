from collections import defaultdict


def _student_group_map(student_groups):
    """Map class_id -> set of student groups that attend it."""
    class_to_groups = defaultdict(set)
    for group, class_ids in student_groups.items():
        for cid in class_ids:
            class_to_groups[cid].add(group)
    return class_to_groups


def greedy_schedule(classes, rooms, student_groups, time_slots):
    """
    Returns:
        assignments: dict class_id -> {"room": room_id, "slot": slot_name}
        unplaced: list of class_ids that could not be placed
    """
    class_to_groups = _student_group_map(student_groups)

    # Sorting key: number of enrolled students, descending (harder classes first).
    sorted_classes = sorted(classes, key=lambda c: c["students"], reverse=True)

    # Track what's already used in each slot.
    room_used_in_slot = {slot: set() for slot in time_slots}       # slot -> {room_id}
    professor_used_in_slot = {slot: set() for slot in time_slots}  # slot -> {professor_id}
    groups_used_in_slot = {slot: set() for slot in time_slots}     # slot -> {group}

    assignments = {}
    unplaced = []

    for cls in sorted_classes:
        cid = cls["id"]
        professor = cls["professor"]
        my_groups = class_to_groups.get(cid, set())

        placed = False
        for slot in time_slots:
            # Hard constraint: professor already teaching this slot.
            if professor in professor_used_in_slot[slot]:
                continue
            # Hard constraint: a student group that needs this class is already
            # committed to another class in this slot.
            if my_groups & groups_used_in_slot[slot]:
                continue

            for room in rooms:
                rid = room["id"]
                if rid in room_used_in_slot[slot]:
                    continue
                if room["capacity"] < cls["students"]:
                    continue  # doesn't fit

                # Found a valid room/slot -- commit it.
                assignments[cid] = {"room": rid, "slot": slot}
                room_used_in_slot[slot].add(rid)
                professor_used_in_slot[slot].add(professor)
                groups_used_in_slot[slot].update(my_groups)
                placed = True
                break

            if placed:
                break

        if not placed:
            unplaced.append(cid)

    return assignments, unplaced


def wasted_capacity(assignments, classes, rooms):
    """Total unused seats across all placed classes (lower is better)."""
    room_cap = {r["id"]: r["capacity"] for r in rooms}
    class_size = {c["id"]: c["students"] for c in classes}
    total_waste = 0
    for cid, info in assignments.items():
        total_waste += room_cap[info["room"]] - class_size[cid]
    return total_waste


if __name__ == "__main__":
    import json

    with open("../data/constraints.json") as f:
        data = json.load(f)

    assignments, unplaced = greedy_schedule(
        data["classes"], data["rooms"], data["student_groups"], data["time_slots"]
    )
    print(f"Placed {len(assignments)} / {len(data['classes'])} classes")
    print(f"Unplaced: {unplaced}")
    print(f"Wasted capacity: {wasted_capacity(assignments, data['classes'], data['rooms'])}")
