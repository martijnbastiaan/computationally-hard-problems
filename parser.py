#!/usr/bin/env python3
import logging
import string
import sys
from collections import OrderedDict

from typing import Iterable, Tuple, Dict, List, Set

log = logging.getLogger(__name__)

LOWERCASE = set(string.ascii_lowercase)
UPPERCASE = set(string.ascii_uppercase)
ASCII_LETTERS = LOWERCASE | UPPERCASE


def get_rs(rs: Iterable[str]) -> Iterable[Tuple[str, Set[str]]]:
    """Decode lines SWE lines containing the replacement mappings"""
    for r in rs:
        upper, lowers = r.split(":")
        lowers = set(lowers.split(","))

        if len(upper) != 1 or upper not in UPPERCASE:
            raise ValueError("First character of R should be uppercase")

        for lower in lowers:
            if not lower or not all(l in LOWERCASE for l in lower):
                raise ValueError("All characters on RHS of R line should be lowercase")

        yield upper, set(lowers)


def simplify_problem(s, ts, rs):
    # We first simplify the solution somewhat. If something maps to a letter
    # not present in s it will never be a suitable replacement.
    remove = set()
    for replacements in rs.values():
        for replacement in replacements:
            if replacement not in s:
                remove.add(replacement)
        replacements -= remove

    # Remove all replacements not mentioned. For example, C is never mentioned
    # in first example so it's a needless burden.
    keep = set(filter(str.isupper, "".join(ts)))
    remove = set(rs.keys()) - keep
    for r in remove:
        del rs[r]

    for k in list(rs.keys()):
        rs[k] = sorted(rs[k], key=lambda c: (-len(c), c))

    log.info("Simplified to {k} clauses and {x} variables.".format(k=len(ts), x=len(rs)))
    return s, ts, rs


def parse(swe_lines: Iterable[str]) -> Tuple[str, List[str], Dict[str, Set[str]]]:
    """Decode given SWE file and run the decision algorithm"""
    log.info("Parsing file..")

    try:
        k = int(next(swe_lines))
    except (ValueError, StopIteration):
        raise ValueError("First line must contain an integer")

    # Get string which has to contain all substrings
    s = next(swe_lines)
    if not s or not all(l in LOWERCASE for l in s):
        raise ValueError("String s should only contain lowercase letters")

    # Get the collection of t's
    ts = [next(swe_lines) for _ in range(k)]
    ts_dedup = sorted(set(ts), key=lambda c: (-len(c), c)) # <- For the sake of being deterministic with no. threads spawned

    log.info("Found {} double clauses, removing duplicates..".format(len(ts) - len(ts_dedup)))
    ts = ts_dedup

    for t in ts:
        if not t or not all(l in ASCII_LETTERS for l in t):
            raise ValueError("{} contained non-ascii chars".format(t))

    # Get the collection of r's. The variable rs will contain a mapping
    # from uppercase to the substitutions. For example: 'A' -> {'b', 'c'}.
    rs = OrderedDict(sorted(get_rs(swe_lines)))

    # Check for illegal substitues
    for letter in "".join(ts):
        if letter in LOWERCASE:
            continue
        if letter not in rs:
            raise ValueError("{} not found in replacement mapping".format(letter))

    return simplify_problem(s, ts, rs)


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(format='[%(asctime)s] %(message)s')
    logging.getLogger().setLevel(logging.DEBUG)

    swe_lines = (l.strip() for l in open(sys.argv[1]))
    s, ts, rs = parse(swe_lines)

    log.info("String found: {}".format(s))
    log.info("Clauses found:")
    for clause in ts:
        log.info("  {}".format(clause))

    log.info("Possible expansions:")
    for k, expansions in rs.items():
        log.info("  {} -> {}".format(k, expansions))

