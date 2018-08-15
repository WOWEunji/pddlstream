#!/usr/bin/env python

from __future__ import print_function

from pddlstream.algorithms.focused import solve_focused
from pddlstream.language.generator import from_test
from pddlstream.utils import print_solution, read, get_file_path

def test_feasible(o, fluents=set()):
    for fact in fluents:
        if fact[0] == 'ontable':
            o2, = fact[1:]
            if (o != o2) and (o2 == 'b2'):
                return False
    return True


def pddlstream_from_belief():
    domain_pddl = read(get_file_path(__file__, 'domain.pddl'))
    constant_map = {}
    stream_pddl = read(get_file_path(__file__, 'stream.pddl'))
    stream_map = {
        'test-feasible': from_test(test_feasible),
    }

    init = [
        ('OnTable', 'b1'),
        ('OnTable', 'b2'),
    ]

    goal = ('Holding', 'b1')

    return domain_pddl, constant_map, stream_pddl, stream_map, init, goal

##################################################

def main():
    # TODO: maybe load problems as a domain explicitly
    pddlstream_problem = pddlstream_from_belief()
    solution = solve_focused(pddlstream_problem, unit_costs=False)
    print_solution(solution)

if __name__ == '__main__':
    main()