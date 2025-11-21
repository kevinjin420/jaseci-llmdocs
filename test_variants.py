#!/usr/bin/env python3
"""
Test fetching documentation variants from URLs
"""

from database import DocumentationService

def test_variants():
    """Test fetching variant content from URLs"""

    print("Testing documentation variant fetching...\n")

    variants = DocumentationService.get_all_variants()

    for variant in variants:
        print(f"Fetching: {variant['name']}")
        print(f"  URL: {variant['url']}")

        content = DocumentationService.get_variant(variant['name'])

        if content:
            size_kb = len(content.encode('utf-8')) / 1024
            lines = len(content.split('\n'))
            print(f"  ✓ Success! Size: {size_kb:.2f} KB, Lines: {lines}")
        else:
            print(f"  ✗ Failed to fetch content")

        print()

    # Check cache
    print("\nVerifying cache...")
    import psycopg2
    import os

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute("SELECT variant_name, size_bytes, cached_at FROM documentation_variants")
    rows = cur.fetchall()

    for name, size, cached_at in rows:
        cache_status = "✓ Cached" if cached_at else "✗ Not cached"
        print(f"  {name}: {cache_status} (size: {size or 0} bytes)")

    cur.close()
    conn.close()

if __name__ == '__main__':
    test_variants()
