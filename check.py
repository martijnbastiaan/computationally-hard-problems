#!/usr/bin/env python3
from collections import OrderedDict

import datetime

import multiprocessing

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


def _A(s: str, ts: List[str], rs: Dict[str, Set[str]], chosen_replacements, starts) -> bool:
    # Positions indicate where we are when searching a

    while ts:
        position = starts[0]
        clause = ts[0]

        for letter in clause:
            letter_or_expansion = chosen_replacements.get(letter, letter)

            # CASE 1
            if letter_or_expansion.isupper():
                # We found a capital letter, meaning we should choose a replacement for it: so
                # we branch off with all possible replacements
                for replacement in rs[letter_or_expansion]:
                    _chosen_replacement = chosen_replacements.copy()
                    _chosen_replacement[letter_or_expansion] = replacement
                    _A(s, ts, rs, _chosen_replacement, starts)
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
                    _starts = starts.copy()
                    _starts[0] = i
                    _A(s, ts, rs, chosen_replacements, _starts)
                return False

        # We have finished a clause, lets move on to the next
        ts = ts[1:]
        starts = starts[1:]

    # We've passed all the clauses without encountering an error. Result found!
    raise ResultFound(OrderedDict(sorted(chosen_replacements.items())))


def A(s: str, ts: List[str], rs: Dict[str, Set[str]]) -> Tuple[bool, Dict]:
    """
    Decision algorithm for the problem specified in the project assignment.

    @param s: string which must contain substrings
    @param ts: k strings t1,t2...tk \in (E U T)*
    @param rs: mapping from element in T -> [expansion]
    """
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

    # If any of the RHS's is now empty, we're requesting something impossible
    if not all(rs.values()):
        return False

    difficulty = 1
    for v in rs.values():
        difficulty *= len(v)

    log.info("Simplified to {k} clauses and {x} variables.".format(k=len(ts), x=len(rs)))
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
    

def get_rs(rs: Iterable[str]) -> Iterable[Tuple[str, Set[str]]]:
    """Decode lines SWE lines containing the replacement mappings"""
    for r in rs:
        upper, lowers = r.split(":")
        lowers = lowers.split(",")

        if len(upper) != 1 or upper not in UPPERCASE:
            raise ValueError("First character of R should be uppercase")
        
        for lower in lowers:
            if not lower or not all(l in LOWERCASE for l in lower):
                raise ValueError("All characters on RHS of R line should be lowercase")

        yield upper, set(lowers)


def main(swe_lines: Iterable[str]) -> Tuple[bool, Dict]:
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
    for t in ts:
        if not t or not all(l in ASCII_LETTERS for l in t):
            raise ValueError("{} contained non-ascii chars".format(t))

    # Get the collection of r's. The variable rs will contain a mapping
    # from uppercase to the substitutions. For example: 'A' -> {'b', 'c'}.
    rs = dict(get_rs(swe_lines))

    # Check for illegal substitues
    for letter in "".join(ts):
        if letter in LOWERCASE:
            continue
        if letter not in rs:
            raise ValueError("{} not found in replacement mapping".format(letter))

    # We're checked and ready!
    log.info("Checking {s} with {k} clauses and {x} variables.".format(s=s, k=k, x=len(rs)))
    return A(s, ts, rs)


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(format='[%(asctime)s] %(message)s')
    logging.getLogger().setLevel(logging.DEBUG)

    # Get file from command line
    start = datetime.datetime.now()
    filename = sys.argv[1]
    result, replacements = main(l.strip() for l in open(filename))
    end = datetime.datetime.now()

    if result is True:
        solution_filename = sys.argv[1].replace(".SWE", ".SOL")
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

