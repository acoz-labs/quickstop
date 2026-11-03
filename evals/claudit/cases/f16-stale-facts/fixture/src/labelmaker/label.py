RATES = {'standard': 395, 'express': 950}  # pence


def render(name, address, service='standard'):
    """A plain-text label."""
    width = max(len(name), len(address)) + 4
    rule = '+' + '-' * (width - 2) + '+'
    lines = [rule, '| ' + name.ljust(width - 4) + ' |', '| ' + address.ljust(width - 4) + ' |', rule]
    return '\n'.join(lines + ['%s: %d.%02d' % (service, *divmod(RATES[service], 100))])
