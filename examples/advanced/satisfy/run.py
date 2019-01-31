#!/usr/bin/env python2.7

from __future__ import print_function

import argparse

from pddlstream.algorithms.satisfaction import dump_assignment, solve_pddlstream_satisfaction
from pddlstream.algorithms.satisfaction2 import constraint_satisfaction
from pddlstream.language.generator import from_test, from_gen_fn
from pddlstream.language.stream import StreamInfo
from pddlstream.utils import INF


def problem1(n=5):
    stream_pddl = """
    (define (stream satisfy)
      (:stream positive
        :outputs (?x)
        :certified (Integer ?x)
      )
      (:stream negative
        :outputs (?x)
        :certified (Integer ?x)
      )
      (:stream test-large
        :inputs (?x)
        :domain (Integer ?x)
        :certified (Large ?x)
      )
      (:function (Cost ?x) 
                 (Integer ?x)
      )
    )
    """

    #constant_map = {} # TODO: constant_map
    stream_map = {
        'positive': from_gen_fn(lambda: ((x,) for x in range(100000))),
        'negative': from_gen_fn(lambda: ((-x,) for x in range(100000))),
        'test-large': from_test(lambda x: n <= x),
        'cost': lambda x: 1./(abs(x) + 1),
    }
    init = []
    terms = [('Integer', '?x1'), ('Large', '?x1'), ('Integer', '?x2'),
             ('minimize', ('Cost', '?x1')), ('minimize', ('Cost', '?x2'))]

    return stream_pddl, stream_map, init, terms

##################################################

def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument('-p', '--problem', default='problem1', help='The name of the problem to solve')
    parser.add_argument('-a', '--algorithm', default=None, help='Specifies the algorithm')
    parser.add_argument('-o', '--optimal', action='store_true', help='Runs in an anytime mode')
    parser.add_argument('-t', '--max_time', default=2, type=int, help='The max time')
    args = parser.parse_args()
    print('Arguments:', args)

    problem_fn = problem1 # get_problem1 | get_problem2
    stream_pddl, stream_map, INIT, terms = problem_fn()
    #print('Init:', pddlstream_problem.init)
    #print('Goal:', pddlstream_problem.goal)

    info = {
        # Intentionally, misleading the stream
        'positive': StreamInfo(overhead=2),
        'negative': StreamInfo(overhead=1),
        # Alternatively, can make the second stream called work
    }
    success_cost = 0 if args.optimal else INF
    if args.algorithm == 'focused':
        solution = solve_pddlstream_satisfaction(stream_pddl, stream_map, INIT, terms, incremental=False,
                                                 stream_info=info, max_time=args.max_time, success_cost=success_cost)
    elif args.algorithm == 'incremental':
        solution = solve_pddlstream_satisfaction(stream_pddl, stream_map, INIT, terms, incremental=True,
                                                 max_time=args.max_time, success_cost=success_cost)
    else:
        solution = constraint_satisfaction(stream_pddl, stream_map, INIT, terms, stream_info=info,
                                           max_time=args.max_time, success_cost=success_cost)
    dump_assignment(solution)

if __name__ == '__main__':
    main()