#!/usr/bin/env python3
"""Plot batch size vs score from exported CSV data."""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def load_data(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV data."""
    df = pd.read_csv(csv_path)
    required = ['batch_size', 'percentage']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df


def plot_batch_vs_score(
    df: pd.DataFrame,
    output: str = None,
    title: str = "Batch Size vs Score",
    group_by: str = None,
    aggregate: bool = True,
    show_points: bool = True,
    show_trend: bool = True,
    show_error_bars: bool = True,
):
    """
    Generate batch size vs score plot.

    Args:
        df: DataFrame with batch_size and percentage columns
        output: Output file path (shows interactive plot if None)
        title: Plot title
        group_by: Column to group/color by (e.g., 'model', 'variant')
        aggregate: If True, aggregate multiple runs per batch size
        show_points: Show individual data points
        show_trend: Show trend line
        show_error_bars: Show standard deviation error bars
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    if group_by and group_by in df.columns:
        groups = df[group_by].unique()
        colors = plt.cm.tab10(np.linspace(0, 1, len(groups)))

        for group, color in zip(groups, colors):
            group_df = df[df[group_by] == group]
            _plot_group(ax, group_df, color, str(group), aggregate, show_points, show_trend, show_error_bars)

        ax.legend(title=group_by.replace('_', ' ').title())
    else:
        _plot_group(ax, df, '#00cc00', None, aggregate, show_points, show_trend, show_error_bars)

    ax.set_xlabel('Batch Size', fontsize=12)
    ax.set_ylabel('Score (%)', fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=150, bbox_inches='tight')
        print(f"Saved plot to {output}")
    else:
        plt.show()


def _plot_group(ax, df, color, label, aggregate, show_points, show_trend, show_error_bars):
    """Plot a single group of data."""
    mean_color = '#e63946'
    trend_color = '#457b9d'

    if aggregate:
        agg = df.groupby('batch_size')['percentage'].agg(['mean', 'std', 'count']).reset_index()
        x = agg['batch_size']
        y = agg['mean']
        yerr = agg['std'].fillna(0)

        if show_points:
            ax.scatter(df['batch_size'], df['percentage'], color=color, alpha=0.4, s=40, label=f'{label} (runs)' if label else 'Individual runs')

        if show_error_bars and (agg['count'] > 1).any():
            ax.errorbar(x, y, yerr=yerr, fmt='s-', color=mean_color, label=f'{label} (mean)' if label else 'Mean',
                       capsize=4, capthick=1.5, markersize=8, linewidth=2, zorder=5)
        else:
            ax.plot(x, y, 's-', color=mean_color, label=f'{label} (mean)' if label else 'Mean', markersize=8, linewidth=2, zorder=5)
    else:
        if show_points:
            ax.scatter(df['batch_size'], df['percentage'], color=color, label=label, s=50, alpha=0.7)

    if show_trend and len(df) >= 2:
        z = np.polyfit(df['batch_size'], df['percentage'], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(df['batch_size'].min(), df['batch_size'].max(), 100)
        ax.plot(x_trend, p(x_trend), '--', color=trend_color, alpha=0.7, linewidth=2, label='Trend' if not label else None)


def print_summary(df: pd.DataFrame):
    """Print summary statistics."""
    print("\n=== Summary Statistics ===")
    agg = df.groupby('batch_size')['percentage'].agg(['mean', 'std', 'count'])
    print(agg.to_string())
    print(f"\nTotal runs: {len(df)}")
    print(f"Batch sizes tested: {sorted(df['batch_size'].unique())}")

    best_idx = agg['mean'].idxmax()
    print(f"Best batch size: {best_idx} (mean: {agg.loc[best_idx, 'mean']:.2f}%)")


def main():
    parser = argparse.ArgumentParser(description='Plot batch size vs score from CSV')
    parser.add_argument('csv', help='Path to CSV file')
    parser.add_argument('-o', '--output', help='Output image file (png, svg, pdf)')
    parser.add_argument('-t', '--title', default='Batch Size vs Score', help='Plot title')
    parser.add_argument('-g', '--group-by', help='Column to group by (e.g., model, variant)')
    parser.add_argument('--no-aggregate', action='store_true', help='Do not aggregate runs')
    parser.add_argument('--no-points', action='store_true', help='Hide individual points')
    parser.add_argument('--no-trend', action='store_true', help='Hide trend line')
    parser.add_argument('--no-error-bars', action='store_true', help='Hide error bars')
    parser.add_argument('-s', '--summary', action='store_true', help='Print summary statistics')

    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"Error: File not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    df = load_data(args.csv)

    if args.summary:
        print_summary(df)

    plot_batch_vs_score(
        df,
        output=args.output,
        title=args.title,
        group_by=args.group_by,
        aggregate=not args.no_aggregate,
        show_points=not args.no_points,
        show_trend=not args.no_trend,
        show_error_bars=not args.no_error_bars,
    )


if __name__ == '__main__':
    main()
