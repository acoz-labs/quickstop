def level(movements):
    """The current stock level: the sum of integer movements."""
    total = 0
    for quantity in movements:
        if not isinstance(quantity, int):
            raise TypeError('quantities are integer counts')
        total += quantity
    return total
