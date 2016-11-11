#!/usr/bin/env python3
import ctypes
import datetime
import logging
import multiprocessing
import random
import string
import parser
import sys

from collections import OrderedDict
from typing import Tuple, Set, List, Dict

# Convert to set for O(1) lookup
LOWERCASE = set(string.ascii_lowercase)
UPPERCASE = set(string.ascii_uppercase)
ASCII_LETTERS = LOWERCASE | UPPERCASE

log = logging.getLogger(__name__)


LEN_TS = None
NUM_SOLS = None
LOCAL_NUM_SOLS = 0


class ResultFound(Exception):
    def __init__(self, replacements):
        self.replacements = replacements


def findall(string, sub, offset=0):
    i = string.find(sub, offset)
    while i >= 0:
        yield i
        i = string.find(sub, i+1)


def get_num_solutions(s, ts, expansions):
    solutions = LEN_TS - len(ts)
    for t in ts:
        ss = "".join(expansions.get(l, l) for l in t)
        if ss.islower() and ss in s:
            solutions += 1
    return solutions


def print_map(s, ts, expansions):
    global NUM_SOLS
    global LOCAL_NUM_SOLS

    if random.random() < 0.9999:
        return

    n_solutions_found = get_num_solutions(s, ts, expansions)

    if n_solutions_found <= LOCAL_NUM_SOLS:
        return

    with NUM_SOLS.get_lock():
        if n_solutions_found <= NUM_SOLS.value:
            LOCAL_NUM_SOLS = NUM_SOLS.value
            return

        if NUM_SOLS.value:
            print("---".format(n_solutions_found, LEN_TS))

        for key, expansion in sorted(expansions.items()):
            if key.isupper():
                print(key, end="")
                print(":", end="")
                print(expansion)

        sys.stdout.flush()

        NUM_SOLS.value = n_solutions_found

    LOCAL_NUM_SOLS = n_solutions_found


def _init_process(num_sols):
    global NUM_SOLS
    NUM_SOLS = num_sols


def __A(args):
    global LEN_TS
    s, ts, rs, expansions, positions = args
    LEN_TS = len(ts)
    return _A(s, ts, rs, expansions, positions)


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
                print_map(s, ts, expansions)
                return False

            # We see a small letter
            if position >= 0:
                # ..if its position is known, just check it and move on to next letter in clause
                # Please not that 'letter' can also be more than one character if it a replacement
                if not s[position:].startswith(letter_or_expansion):
                    # Expansion does not fit here in this string. Invalid branch!
                    print_map(s, ts, expansions)
                    return False

                position += len(letter_or_expansion)
            else:
                # .. its position is not known. Find all suitable starting places.
                for i in findall(s, letter_or_expansion):
                    _positions = positions.copy()
                    _positions[0] = i
                    _A(s, ts, rs, expansions, _positions)
                print_map(s, ts, expansions)
                return False

        # We have finished a clause, lets move on to the next
        ts = ts[1:]
        positions = positions[1:]

    # We've passed all the clauses without encountering an error. Result found!
    print_map(s, ts, expansions)
    raise ResultFound(OrderedDict(sorted((k, v) for k, v in expansions.items() if k.isupper())))


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

    num_sols = multiprocessing.Value(ctypes.c_int)
    pool = multiprocessing.Pool(initializer=_init_process, initargs=(num_sols,))
    var = next(filter(str.isupper, "".join(ts)))
    expansions = {l: l for l in LOWERCASE}
    arguments = [(s, ts.copy(), rs.copy(), dict(**expansions, **{var: x}), [-1]*len(ts)) for x in rs[var]]

    log.info("Starting {} threads over {} starting points:".format(len(pool._pool), len(arguments)))

    # Cleanup done, start real algorithm
    try:
        for n, _ in enumerate(pool.imap_unordered(__A, arguments)):
            log.info("  Starting point {}/{} lead to a dead end".format(n+1, len(arguments)))
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

