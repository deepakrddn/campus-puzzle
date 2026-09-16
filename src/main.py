import json
import os

from greedy_solver import greedy_schedule, wasted_capacity as greedy_waste
from graph_engine import (
    build_conflict_graph,
    welsh_powell_coloring,
    colors_to_time_slots,
    compare_to_greedy,
)
from optimizer import optimize_full_schedule, total_wasted_capacity
from backtracker import resolve_conflicts
from visualization import write_waste_comparison_chart


DATA_PATH = os.path.join("..", "data", "constraints.json")
OUTPUT_PATH = os.path.join("..", "results", "schedule_output.txt")
CHART_PATH = os.path.join("..", "results", "waste_comparison.svg")


def load_data(path=DATA_PATH):
    with open(path) as f:
        return json.load(f)


def run_pipeline(data):
    classes = data["classes"]
    rooms = data["rooms"]
    student_groups = data["student_groups"]
    time_slots = data["time_slots"]

    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("THE CAMPUS PUZZLE - FULL PIPELINE REPORT")
    report_lines.append("=" * 70)

    # ---------- Stage 1: Greedy baseline ----------
    greedy_assignments, greedy_unplaced = greedy_schedule(classes, rooms, student_groups, time_slots)
    report_lines.append("\n--- Stage 1: Greedy Baseline ---")
    report_lines.append(f"Placed: {len(greedy_assignments)} / {len(classes)}")
    report_lines.append(f"Unplaced: {greedy_unplaced}")
    report_lines.append(f"Wasted capacity: {greedy_waste(greedy_assignments, classes, rooms)}")

    # ---------- Stage 2: Graph coloring ----------
    adjacency = build_conflict_graph(classes, student_groups)
    coloring, num_colors = welsh_powell_coloring(adjacency)
    slot_assignment, overflow_classes = colors_to_time_slots(coloring, time_slots)

    report_lines.append("\n--- Stage 2: Graph Coloring (Welsh-Powell) ---")
    report_lines.append(f"Colors (distinct time slots) needed: {num_colors}")
    report_lines.append(f"Classes with a conflict-free slot: {len(slot_assignment)}")
    report_lines.append(f"Overflow (no slot available): {overflow_classes}")
    report_lines.append("")
    report_lines.append(compare_to_greedy(greedy_unplaced, overflow_classes, num_colors, len(time_slots)))

    # ---------- Stage 3: DP room optimization ----------
    final_assignments, unresolved_after_dp = optimize_full_schedule(slot_assignment, classes, rooms)

    report_lines.append("\n--- Stage 3: DP Room Allocation ---")
    report_lines.append(f"Classes fully scheduled (slot + room): {len(final_assignments)}")
    report_lines.append(f"Unresolved after DP (no room fit in their slot): {unresolved_after_dp}")
    report_lines.append(f"Total wasted capacity: {total_wasted_capacity(final_assignments, classes, rooms)}")
    if greedy_assignments:
        improvement = greedy_waste(greedy_assignments, classes, rooms) - total_wasted_capacity(
            final_assignments, classes, rooms
        )
        report_lines.append(f"Improvement over greedy baseline: {improvement} fewer wasted seats")

    # ---------- Stage 4: Backtracking best-effort ----------
    all_unresolved = list(set(overflow_classes) | set(unresolved_after_dp))
    if all_unresolved:
        report_lines.append("\n--- Stage 4: Backtracking Best-Effort ---")
        report_lines.append(f"Classes handed to backtracking: {all_unresolved}")

        backtrack_assignments, still_unplaced = resolve_conflicts(
            all_unresolved, classes, rooms, student_groups, time_slots, final_assignments
        )
        for cid, info in backtrack_assignments.items():
            final_assignments[cid] = info

        report_lines.append(f"Backtracking placed: {len(backtrack_assignments)} additional class(es)")
        report_lines.append(f"Still unplaced (flagged for manual intervention): {still_unplaced}")
    else:
        still_unplaced = []
        report_lines.append("\n--- Stage 4: Backtracking Best-Effort ---")
        report_lines.append("Not needed -- Stages 2/3 already produced a complete schedule.")

    # ---------- Final schedule ----------
    report_lines.append("\n" + "=" * 70)
    report_lines.append("FINAL SCHEDULE")
    report_lines.append("=" * 70)
    class_name = {c["id"]: c.get("name", c["id"]) for c in classes}
    slot_order = {slot: index for index, slot in enumerate(time_slots)}
    for cid in sorted(
        final_assignments,
        key=lambda c: (slot_order.get(final_assignments[c]["slot"], len(slot_order)), c),
    ):
        info = final_assignments[cid]
        report_lines.append(f"{cid:6s} {class_name[cid]:24s} -> {info['slot']:10s} | {info['room']}")

    if still_unplaced:
        report_lines.append("\n--- CONFLICT REPORT: classes requiring manual intervention ---")
        for cid in still_unplaced:
            cls = next(c for c in classes if c["id"] == cid)
            report_lines.append(
                f"  {cid} ({cls.get('name', cid)}): {cls['students']} students, "
                f"professor {cls['professor']} -- no remaining (slot, room) pair "
                f"satisfies all hard constraints."
            )

    return "\n".join(report_lines), final_assignments, still_unplaced


def main():
    data = load_data()
    report, final_assignments, still_unplaced = run_pipeline(data)
    classes = data["classes"]
    rooms = data["rooms"]
    greedy_assignments, _ = greedy_schedule(classes, rooms, data["student_groups"], data["time_slots"])
    greedy_total = greedy_waste(greedy_assignments, classes, rooms)
    dp_total = total_wasted_capacity(final_assignments, classes, rooms)

    print(report)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(report)
    write_waste_comparison_chart(greedy_total, dp_total, CHART_PATH)
    print(f"\nFull report written to {OUTPUT_PATH}")
    print(f"Waste comparison chart written to {CHART_PATH}")


if __name__ == "__main__":
    main()
