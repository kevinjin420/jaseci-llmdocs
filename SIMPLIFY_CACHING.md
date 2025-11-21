# Caching Simplification Proposal

## Current State (Over-engineered)

```python
# Complex: Fetch with caching
def get_variant(variant_name: str, force_refresh: bool = False):
    variant = query_db(variant_name)

    # Check cache validity
    if variant.content and variant.cached_at:
        if time.time() - variant.cached_at < variant.cache_ttl:
            return variant.content  # Return cached

    # Fetch from GitHub
    response = requests.get(variant.url)

    # Update cache
    variant.content = response.text
    variant.cached_at = time.time()
    db.commit()

    return variant.content
```

**Problems:**
- Database stores duplicate data (URL + content)
- Stale data risk (1 hour cache)
- Complexity for minimal benefit
- 100KB+ database bloat for 30ms savings

## Proposed: Simple Direct Fetch

```python
# Simple: Just fetch every time
def get_variant(variant_name: str):
    variant = query_db(variant_name)  # Just get URL
    response = requests.get(variant.url, timeout=10)
    return response.text
```

**Benefits:**
- Always fresh data
- 50% less code
- No cache management
- No stale data bugs
- Simpler to understand

**Cost:**
- 50-100ms extra per benchmark run
- Minimal (benchmark takes 10+ minutes anyway!)

## Database Schema Simplification

### Current:
```sql
CREATE TABLE documentation_variants (
    id SERIAL PRIMARY KEY,
    variant_name VARCHAR(128) UNIQUE,
    url VARCHAR(512),           -- URL to fetch from
    content TEXT,               -- ← Remove this (cached)
    size_bytes INTEGER,         -- ← Remove this (cached)
    cached_at FLOAT,            -- ← Remove this
    cache_ttl INTEGER,          -- ← Remove this
    version VARCHAR(32),
    created_at FLOAT,
    updated_at FLOAT
);
```

### Simplified:
```sql
CREATE TABLE documentation_variants (
    id SERIAL PRIMARY KEY,
    variant_name VARCHAR(128) UNIQUE,
    url VARCHAR(512),           -- Just the URL!
    version VARCHAR(32),
    description TEXT,
    created_at FLOAT,
    updated_at FLOAT
);
```

**Savings:**
- 4 fewer columns
- No TEXT column storing 32KB per variant
- Simpler queries
- Clearer intent

## Implementation

1. **Drop cache columns:**
   ```sql
   ALTER TABLE documentation_variants
       DROP COLUMN content,
       DROP COLUMN size_bytes,
       DROP COLUMN cached_at,
       DROP COLUMN cache_ttl;
   ```

2. **Simplify service:**
   ```python
   @staticmethod
   def get_variant(variant_name: str) -> Optional[str]:
       """Fetch documentation content from URL"""
       import requests

       with get_db() as session:
           variant = session.query(DocumentationVariant).filter_by(
               variant_name=variant_name,
               is_active=True
           ).first()

           if not variant:
               return None

           try:
               response = requests.get(variant.url, timeout=30)
               response.raise_for_status()
               return response.text
           except Exception as e:
               print(f"Error fetching {variant_name}: {e}")
               return None
   ```

3. **Remove cache from models too:**
   - `ModelAvailability` table has similar caching
   - Can simplify to just fetch from OpenRouter every time
   - Or keep if you want offline mode

## When to Keep Caching

Keep model availability cache IF:
- You want offline development mode
- OpenRouter API has rate limits
- Testing without API access

Otherwise, simplify that too!

## Summary

**Current:**
- Premature optimization
- Adds complexity for 30ms savings
- 100KB database bloat
- Stale data risk

**Simplified:**
- Direct fetch every time
- 50% less code
- Always fresh
- Benchmark is 10+ min anyway, 100ms doesn't matter!

**Recommendation:** Remove caching unless you plan to make this a multi-user production service.
