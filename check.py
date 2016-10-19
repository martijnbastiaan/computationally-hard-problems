#!/usr/bin/env python3
from typing import Iterable, Tuple, Set, List, Dict

import json
import string
import sys

# Convert to set for O(1) lookup
LOWERCASE = set(string.ascii_lowercase)
UPPERCASE = set(string.ascii_uppercase)
ASCII_LETTERS = LOWERCASE | UPPERCASE


class ResultFound(Exception):
    def __init__(self, replacements):
        self.replacements = replacements


def findall(string, sub, offset=0):
    i = string.find(sub, offset)
    while i >= 0:
        yield i
        i = string.find(sub, i+1)


def _A(s: str, ts: List[str], rs: Dict[str, Set[str]], chosen_replacements, starts) -> bool:
    # Positions indicate where we are when searching a 
    for clausenr, (position, clause) in enumerate(zip(starts, ts)):
        if position == -1:
            # We need to determine where we start reading this clause in the substr
            letter = clause[0]
            if letter.isupper():
                if letter in chosen_replacements:
                    letter = chosen_replacements[letter]
                else:
                    # Iterate over all possibilities!
                    for replacement in rs[letter]:
                        _chosen_replacement = dict(chosen_replacements)
                        _chosen_replacement[letter] = replacement
                        _A(s, ts, rs, _chosen_replacement, starts)
                    # We didn't find any possible results (no exception yielded), so we
                    # we return False as going on is pointless.
                    return False

            # We arrive at this point if we either encountered a small letter at
            # our first read of the clause, or if we found a replacement where we
            # need a start position for.
            for i in findall(s, letter):
                _starts = list(starts)
                _starts[clausenr] = i
                _A(s, ts, rs, chosen_replacements, _starts)
            # We didn't find any possible results (no exception yielded), so we
            # we return False as going on is pointless.
            return False
        else:
            # We arrive here if we start scanning a clause and a start has already
            # been defined. 
            for letter in clause:
                letter = chosen_replacements.get(letter, letter)
                if letter.isupper():
                    # Found a uppercase letter not yet chosen
                    for replacement in rs[letter]:
                        _chosen_replacement = dict(chosen_replacements)
                        _chosen_replacement[letter] = replacement
                        _A(s, ts, rs, _chosen_replacement, starts)
                    # We didn't find any possible results (no exception yielded), so we
                    # we return False as going on is pointless.
                    return False
                else:
                    # Replacement either already defined or we found a lowercase letter
                    if not s[position:].startswith(letter):
                        # Non-suitable replacement found
                        return False
                    else:
                        position += len(letter)



    # We've passed all the clauses without encountering an error. Result found!
    raise ResultFound(dict(chosen_replacements))


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

    # Cleanup done, start real algorithm
    try:
        return _A(s, ts, rs, {}, [-1]*len(ts)), None
    except ResultFound as e:
        return True, e.replacements
    

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
    return A(s, ts, rs)


if __name__ == '__main__':
    filename = sys.argv[1]
    result, replacements = main(l.strip() for l in open(filename))

    if result is True:
        print("YES:")
        print(json.dumps(replacements))
    elif result is False:
        print("NO")
    else:
        print("No answer found. A returned: {}. Bug?".format(result))
    
