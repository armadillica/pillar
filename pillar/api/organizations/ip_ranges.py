"""IP range support for Organizations."""

from IPy import IP

# 128 bits all set to 1
ONES_128 = 2 ** 128 - 1


def doc(iprange: str, min_prefixlen6: int=0, min_prefixlen4: int=0) -> dict:
    """Convert a human-readable string like '1.2.3.4/24' to a Mongo document.

    This converts the address to IPv6 and computes the start/end addresses
    of the range. The address, its prefix size, and start and end address,
    are returned as a dict.

    Addresses are stored as big-endian binary data because MongoDB doesn't
    support 128 bits integers.

    :param iprange: the IP address and mask size, can be IPv6 or IPv4.
    :param min_prefixlen6: if given, causes a ValuError when the mask size
                           is too low. Note that the mask size is always
                           evaluated only for IPv6 addresses.
    :param min_prefixlen4: if given, causes a ValuError when the mask size
                           is too low. Note that the mask size is always
                           evaluated only for IPv4 addresses.
    :returns: a dict like: {
        'start': b'xxxxx' with the lowest IP address in the range.
        'end': b'yyyyy' with the highest IP address in the range.
        'human': 'aaaa:bbbb::cc00/120' with the human-readable representation.
        'prefix': 120, the prefix length of the netmask in bits.
    }
    """

    ip = IP(iprange, make_net=True)
    prefixlen = ip.prefixlen()
    if ip.version() == 4:
        if prefixlen < min_prefixlen4:
            raise ValueError(f'Prefix length {prefixlen} smaller than allowed {min_prefixlen4}')
        ip = ip.v46map()
    else:
        if prefixlen < min_prefixlen6:
            raise ValueError(f'Prefix length {prefixlen} smaller than allowed {min_prefixlen6}')

    addr = ip.int()

    # Set all address bits to 1 where the mask is 0 to obtain the largest address.
    end = addr | (ONES_128 % ip.netmask().int())

    # This ensures that even a single host is represented as /128 in the human-readable form.
    ip.NoPrefixForSingleIp = False

    return {
        'start': addr.to_bytes(16, 'big'),
        'end': end.to_bytes(16, 'big'),
        'human': ip.strCompressed(),
        'prefix': ip.prefixlen(),
    }


def query(address: str) -> dict:
    """Return a dict usable for querying all organizations whose IP range matches the given one.

    :returns: a dict like:
        {$elemMatch: {'start': {$lte: b'xxxxx'}, 'end': {$gte: b'xxxxx'}}}
    """

    ip = IP(address)
    if ip.version() == 4:
        ip = ip.v46map()
    for_mongo = ip.ip.to_bytes(16, 'big')

    return {'$elemMatch': {
        'start': {'$lte': for_mongo},
        'end': {'$gte': for_mongo},
    }}
