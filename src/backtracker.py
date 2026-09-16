from collections import defaultdict


def _student_group_map(student_groups):
    class_to_groups = defaultdict(set)
    for group, class_ids in student_groups.items():
        for cid in class_ids:
            class_to_groups[cid].add(group)
    return class_to_groups


class BacktrackingResolver:
    def __init__(self, classes, rooms, student_groups, time_slots, existing_assignments):
        """
        existing_assignments: dict class_id -> {"room", "slot"} already
                               locked in by Stages 1-3. These count as
                               "used" for conflict-checking but are
                               never touched by this resolver.
        """
        self.class_by_id = {c["id"]: c for c in classes}
        self.rooms = rooms
        self.time_slots = time_slots
        self.class_to_groups = _student_group_map(student_groups)

        # Seed "used" trackers with everything already scheduled.
        self.room_used_in_slot = {slot: set() for slot in time_slots}
        self.professor_used_in_slot = {slot: set() for slot in time_slots}
        self.groups_used_in_slot = {slot: set() for slot in time_slots}

        for cid, info in existing_assignments.items():
            slot, room = info["slot"], info["room"]
            if slot not in self.room_used_in_slot:
                continue
            self.room_used_in_slot[slot].add(room)
            self.professor_used_in_slot[slot].add(self.class_by_id[cid]["professor"])
            self.groups_used_in_slot[slot].update(self.class_to_groups.get(cid, set()))

        self.best_assignments = {}   # best solution found so far (this stage's classes only)
        self.best_unplaced = None    # fewest-unplaced count seen so far

    def _legal_options(self, cid):
        """All (slot, room_id) pairs currently legal for this class."""
        cls = self.class_by_id[cid]
        professor = cls["professor"]
        my_groups = self.class_to_groups.get(cid, set())
        options = []
        for slot in self.time_slots:
            if professor in self.professor_used_in_slot[slot]:
                continue
            if my_groups & self.groups_used_in_slot[slot]:
                continue
            for room in self.rooms:
                if room["capacity"] < cls["students"]:
                    continue
                if room["id"] in self.room_used_in_slot[slot]:
                    continue
                options.append((slot, room["id"]))
        return options

    def _place(self, cid, slot, room_id):
        cls = self.class_by_id[cid]
        self.room_used_in_slot[slot].add(room_id)
        self.professor_used_in_slot[slot].add(cls["professor"])
        self.groups_used_in_slot[slot].update(self.class_to_groups.get(cid, set()))

    def _unplace(self, cid, slot, room_id):
        cls = self.class_by_id[cid]
        self.room_used_in_slot[slot].discard(room_id)
        self.professor_used_in_slot[slot].discard(cls["professor"])
        # Only remove groups this class contributed if no other placed
        # class in this attempt still needs them in this slot.
        for g in self.class_to_groups.get(cid, set()):
            still_needed = any(
                g in self.class_to_groups.get(other, set()) and info["slot"] == slot
                for other, info in self.current.items()
            )
            if not still_needed:
                self.groups_used_in_slot[slot].discard(g)

    def solve(self, unresolved_class_ids):
        """
        Runs MRV-ordered backtracking search over the given class ids.

        Returns:
            assignments: dict class_id -> {"room", "slot"} for classes
                         this stage managed to place
            still_unplaced: list of class_ids flagged for manual
                            intervention
        """
        self.current = {}
        self.best_assignments = {}
        self.best_unplaced = len(unresolved_class_ids) + 1  # worse than any real outcome

        self._search(list(unresolved_class_ids))

        still_unplaced = [cid for cid in unresolved_class_ids if cid not in self.best_assignments]
        return dict(self.best_assignments), still_unplaced

    def _search(self, remaining):
        # Best-effort bookkeeping: whenever we reach a point (including
        # dead ends) where the current partial solution beats our best
        # known outcome, save it.
        unplaced_now = len(remaining)
        if unplaced_now < self.best_unplaced:
            self.best_unplaced = unplaced_now
            self.best_assignments = dict(self.current)

        if not remaining:
            return True  # fully solved this branch

        # MRV: branch on the class with the fewest legal options left.
        options_by_class = {cid: self._legal_options(cid) for cid in remaining}
        cid = min(remaining, key=lambda c: len(options_by_class[c]))
        options = options_by_class[cid]

        if not options:
            # Pruning: this class has zero legal moves -- skip it (leave
            # it unplaced) rather than failing the whole branch, so we
            # can still find the best possible outcome for everyone
            # else. This is the "best effort" behavior.
            next_remaining = [c for c in remaining if c != cid]
            return self._search(next_remaining)

        next_remaining = [c for c in remaining if c != cid]
        for slot, room_id in options:
            self._place(cid, slot, room_id)
            self.current[cid] = {"slot": slot, "room": room_id}

            solved = self._search(next_remaining)

            del self.current[cid]
            self._unplace(cid, slot, room_id)

            if solved:
                return True

        # No option for this class led to a full solution in this
        # branch; report the class itself as unplaced in this branch
        # (best-effort) and keep exploring so a better global optimum
        # can still be recorded.
        return self._search(next_remaining)


def resolve_conflicts(unresolved_class_ids, classes, rooms, student_groups, time_slots, existing_assignments):
    resolver = BacktrackingResolver(classes, rooms, student_groups, time_slots, existing_assignments)
    return resolver.solve(unresolved_class_ids)
