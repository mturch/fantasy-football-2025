#!/usr/bin/env python3
"""
Test script to examine weather data files before import.
"""

import os
import sys

import pandas as pd


def examine_csv_file(file_path: str, max_rows: int = 5):
    """Examine a CSV file and show its structure."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print(f"\n📁 Examining: {file_path}")
    print(f"📊 File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")

    try:
        # Read first few rows
        df = pd.read_csv(file_path, nrows=max_rows)

        print(f"📋 Columns ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")

        print(f"\n📈 Sample data (first {max_rows} rows):")
        print(df.to_string(index=False))

        # Get file info
        total_rows = sum(1 for _ in open(file_path)) - 1  # Subtract header
        print(f"\n📊 Total rows: {total_rows:,}")

    except Exception as e:
        print(f"❌ Error reading file: {e}")


def main():
    """Main function."""
    data_dir = "data/external/weather"

    print("🌤️  Weather Data File Examination")
    print("=" * 50)

    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        sys.exit(1)

    # List all CSV files
    csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    print(f"📂 Found {len(csv_files)} CSV files in {data_dir}:")

    for file in csv_files:
        print(f"  • {file}")

    # Examine each file
    for file in csv_files:
        file_path = os.path.join(data_dir, file)
        examine_csv_file(file_path)

    print("\n✅ Weather data examination completed!")


if __name__ == "__main__":
    main()
