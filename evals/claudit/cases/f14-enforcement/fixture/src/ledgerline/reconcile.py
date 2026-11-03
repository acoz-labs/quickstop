def reconcile(left, right):
    """Entries (id, cents) present in one ledger only, or with different amounts."""
    a, b = dict(left), dict(right)
    return sorted((key, a.get(key), b.get(key)) for key in a.keys() | b.keys() if a.get(key) != b.get(key))
