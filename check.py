#!/usr/bin/env python3
from collections import OrderedDict

import datetime

import multiprocessing

import parser

from typing import Iterable, Tuple, Set, List, Dict

import logging
import string
import sys

# Convert to set for O(1) lookup
LOWERCASE = set(string.ascii_lowercase)
UPPERCASE = set(string.ascii_uppercase)
ASCII_LETTERS = LOWERCASE | UPPERCASE

log = logging.getLogger(__name__)


class ResultFound(Exception):
    def __init__(self, replacements):
        self.replacements = replacements


def findall(string, sub, offset=0):
    i = string.find(sub, offset)
    while i >= 0:
        yield i
        i = string.find(sub, i+1)


def __A(args):
    return _A(*args)


def _A(s: str, ts: List[str], rs: Dict[str, Set[str]], expansions, positions) -> bool:
    # Positions indicate where we are when searching a

    while ts:
        position = positions[0]
        clause = ts[0]

        for letter in clause:
            letter_or_expansion = expansions.get(letter, letter)

            # CASE 1
            if letter_or_expansion.isupper():
                # We found a capital letter, meaning we should choose a replacement for it: so
                # we branch off with all possible replacements
                for replacement in rs[letter_or_expansion]:
                    _expansions = expansions.copy()
                    _expansions[letter_or_expansion] = replacement
                    _A(s, ts, rs, _expansions, positions)
                return False

            # We see a small letter
            if position >= 0:
                # ..if its position is known, just check it and move on to next letter in clause
                # Please not that 'letter' can also be more than one character if it a replacement
                if not s[position:].startswith(letter_or_expansion):
                    # Expansion does not fit here in this string. Invalid branch!
                    return False

                position += len(letter_or_expansion)
            else:
                # .. its position is not known. Find all suitable starting places.
                for i in findall(s, letter_or_expansion):
                    _positions = positions.copy()
                    _positions[0] = i
                    _A(s, ts, rs, expansions, _positions)
                return False

        # We have finished a clause, lets move on to the next
        ts = ts[1:]
        positions = positions[1:]

    # We've passed all the clauses without encountering an error. Result found!
    raise ResultFound(OrderedDict(sorted(expansions.items())))


def A(s: str, ts: List[str], rs: Dict[str, Set[str]]) -> Tuple[bool, Dict]:
    """
    Decision algorithm for the problem specified in the project assignment.

    @param s: string which must contain substrings
    @param ts: k strings t1,t2...tk \in (E U T)*
    @param rs: mapping from element in T -> [expansion]
    """
    log.info("Checking {s} with {k} clauses and {x} variables.".format(s=s, k=len(ts), x=len(rs)))

    # If any of the RHS's is now empty, we're requesting something impossible
    if not all(rs.values()):
        return False

    difficulty = 1
    for v in rs.values():
        difficulty *= len(v)

    log.info("Difficulty: {} options.".format(difficulty))

    pool = multiprocessing.Pool()
    var = next(filter(str.isupper, "".join(ts)))
    arguments = [(s, ts.copy(), rs.copy(), {var: x}, [-1]*len(ts)) for x in rs[var]]

    log.info("Starting {} threads over {} starting points:".format(len(pool._pool), len(arguments)))

    # Cleanup done, start real algorithm
    try:
        for n, _ in enumerate(pool.imap_unordered(__A, arguments)):
            log.info("  Starting point {}/{} lead to a dead end".format(n+1, len(arguments)))
        #return _A(s, ts, rs, {}, [-1]*len(ts)), None
    except ResultFound as e:
        log.info("Solution found. Checking..")
        for old_clause in ts:
            new_clause = old_clause
            for var, replacement in e.replacements.items():
                new_clause = new_clause.replace(var, replacement)
            if new_clause in s:
                log.info("  substring found: {} -> {}".format(old_clause, new_clause))
            else:
                log.error("  substring found: {} -> {}".format(old_clause, new_clause))
                raise ValueError("substring not found, but A determined it valid. Bug!")
        return True, e.replacements
    else:
        return False, None
    finally:
        pool.terminate()
        pool.join()
    

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(format='[%(asctime)s] %(message)s')
    logging.getLogger().setLevel(logging.DEBUG)

    # Get file from command line
    filename = sys.argv[1]
    start = datetime.datetime.now()
    swe_lines = (l.strip() for l in open(filename))
    s, ts, rs = parser.parse(swe_lines)
    result, replacements = A(s, ts, rs)
    end = datetime.datetime.now()

    if result is True:
        solution_filename = filename.replace(".SWE", ".SOL")
        solution_file = open(solution_filename, "w")

        log.info("Solution:")
        for k, v in replacements.items():
            log.info("  {} -> {}".format(k, v))
            solution_file.write("{}: {}\n".format(k, v))
        log.info("Solution written to: {}".format(solution_filename))
        solution_file.close()
    else:
        log.info("No solution found")

    log.info("Time taken: {}".format(end - start))

