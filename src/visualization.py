"""Small, dependency-free visualizations for generated scheduling results."""

import os


def write_waste_comparison_chart(greedy_waste, dp_waste, output_path):
    """Write an SVG bar chart comparing wasted room capacity."""
    width, height = 760, 460
    plot_left, plot_top = 115, 105
    plot_width, plot_height = 560, 235
    max_value = max(greedy_waste, dp_waste, 1)
    tick_step = 500
    chart_max = ((max_value + tick_step - 1) // tick_step) * tick_step
    reduction = greedy_waste - dp_waste
    reduction_percent = reduction / greedy_waste * 100 if greedy_waste else 0
    bars = [("Greedy", greedy_waste, "#E76F51"), ("DP optimizer", dp_waste, "#2A9D8F")]
    positions, bar_width = [210, 445], 150
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Wasted room capacity: Greedy versus DP optimizer</title>',
        f'<desc id="desc">The greedy baseline wastes {greedy_waste:,} seats, while the dynamic-programming optimizer wastes {dp_waste:,} seats.</desc>',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        '<text x="380" y="42" text-anchor="middle" font-family="Arial, sans-serif" font-size="25" font-weight="700" fill="#17324D">Room-capacity waste comparison</text>',
        '<text x="380" y="70" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="#52616B">Lower is better · wasted seats across the full schedule</text>',
    ]
    for value in range(0, chart_max + 1, tick_step):
        y = plot_top + plot_height - (value / chart_max * plot_height)
        elements.append(f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_left + plot_width}" y2="{y:.1f}" stroke="#D9E1E7" stroke-width="1"/>')
        elements.append(f'<text x="{plot_left - 14}" y="{y + 5:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="#52616B">{value:,}</text>')
    elements.append(f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_top + plot_height}" stroke="#52616B" stroke-width="1.5"/>')
    elements.append(f'<line x1="{plot_left}" y1="{plot_top + plot_height}" x2="{plot_left + plot_width}" y2="{plot_top + plot_height}" stroke="#52616B" stroke-width="1.5"/>')
    for (label, value, color), x in zip(bars, positions):
        bar_height = value / chart_max * plot_height
        y, center = plot_top + plot_height - bar_height, x + bar_width / 2
        elements.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="5" fill="{color}"/>')
        elements.append(f'<text x="{center}" y="{y - 12:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#17324D">{value:,}</text>')
        elements.append(f'<text x="{center}" y="{plot_top + plot_height + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="600" fill="#17324D">{label}</text>')
    elements.extend([
        '<rect x="175" y="383" width="410" height="45" rx="8" fill="#E5F4F1"/>',
        f'<text x="380" y="412" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#16756A">{reduction:,} fewer wasted seats ({reduction_percent:.1f}% reduction)</text>',
        '</svg>',
    ])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as chart_file:
        chart_file.write("\n".join(elements))
