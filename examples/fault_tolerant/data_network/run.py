#!/usr/bin/env python2.7

from __future__ import print_function

import argparse

from pddlstream.algorithms.focused import solve_focused
from pddlstream.language.generator import from_test
from pddlstream.language.stream import StreamInfo, DEBUG
from pddlstream.utils import read, get_file_path
from pddlstream.language.constants import print_solution, PDDLProblem, And, dump_pddlstream, is_plan, Fact
from pddlstream.algorithms.search import solve_from_pddl
from examples.fault_tolerant.logistics.run import test_from_bernoulli_fn, CachedFn
from examples.blocksworld.run import read_pddl

from pddlstream.algorithms.downward import parse_sequential_domain, parse_problem, \
    task_from_domain_problem, get_conjunctive_parts, TEMP_DIR, set_cost_scale

P_SUCCESS = 1.

# TODO: parse problem.pddl directly

OBJECTS = """
data-0-3 data-0-5 data-1-2 data-1-4 data-2-1 - data
script1 script2 script3 script4 script5 script6 script7 script8 script9 script10 - script
server1 server2 server3 - server
number0 number1 number2 number3 number4 number5 number6 number7 number8 number9 number10 number11 number12 number13 number14 number15 number16 - numbers
"""

INIT = """
(SCRIPT-IO script1 data-0-3 data-0-5 data-1-4)
(SCRIPT-IO script2 data-0-5 data-0-3 data-1-2)
(SCRIPT-IO script3 data-1-4 data-0-5 data-2-1)
(SCRIPT-IO script4 data-0-3 data-0-5 data-1-4)
(SCRIPT-IO script5 data-1-2 data-0-5 data-2-1)
(SCRIPT-IO script6 data-1-2 data-0-3 data-2-1)
(SCRIPT-IO script7 data-0-5 data-0-3 data-1-2)
(SCRIPT-IO script8 data-1-4 data-1-2 data-2-1)
(SCRIPT-IO script9 data-0-3 data-0-5 data-1-4)
(SCRIPT-IO script10 data-1-2 data-1-4 data-2-1)
(CONNECTED server1 server2)
(CONNECTED server2 server1)
(CONNECTED server1 server3)
(CONNECTED server3 server1)
(DATA-SIZE data-0-3 number4)
(DATA-SIZE data-0-5 number5)
(DATA-SIZE data-1-2 number4)
(DATA-SIZE data-1-4 number1)
(DATA-SIZE data-2-1 number4)
(CAPACITY server1 number16)
(CAPACITY server2 number8)
(CAPACITY server3 number8)
(saved data-0-3 server3)
(saved data-0-5 server1)
(usage server1 number0)
(usage server2 number0)
(usage server3 number0)
"""
# Removed functions for now

def object_facts_from_str(s):
    objs, ty = s.strip().rsplit(' - ', 1)
    return [(ty, obj) for obj in objs.split(' ')]

def fact_from_str(s):
    return tuple(s.strip('( )').split(' '))

def int_from_str(s):
    return int(s.replace('number', ''))

# TODO: I need the streams in order to do this

def get_problem():
    domain_pddl = read(get_file_path(__file__, 'domain.pddl'))
    constant_map = {}
    stream_pddl = read(get_file_path(__file__, 'stream.pddl'))

    # TODO: compare statistical success and the actual success
    bernoulli_fns = {
        #'test-open': fn_from_constant(P_SUCCESS),
    }

    # universe_test | empty_test
    stream_map = {
        'test-less_equal': from_test(lambda x, y: int_from_str(x) <= int_from_str(y)),
        'test-sum': from_test(lambda x, y, z: int_from_str(x) + int_from_str(y) == int_from_str(z)),
    }
    stream_map.update({name: from_test(CachedFn(test_from_bernoulli_fn(fn)))
                       for name, fn in bernoulli_fns.items()})

    init = [fact_from_str(s) for s in INIT.split('\n') if s]
    for line in OBJECTS.split('\n'):
        if line:
            init.extend(object_facts_from_str(line))

    goal_literals = [
        'saved data-2-1 server2',
    ]

    goal = And(*map(fact_from_str, goal_literals))

    return PDDLProblem(domain_pddl, constant_map, stream_pddl, stream_map, init, goal)

##################################################

def get_stuff():
    from examples.fault_tolerant.risk_management.run import fact_from_fd

    #safe_rm_dir(TEMP_DIR) # TODO: fix re-running bug
    domain_pddl = read(get_file_path(__file__, 'domain.pddl'))
    domain = parse_sequential_domain(domain_pddl)
    #print(domain)

    assert not domain.constants
    constant_map = {}

    problem_pddl = read(get_file_path(__file__, 'problem.pddl'))
    problem = parse_problem(domain, problem_pddl)
    #task = task_from_domain_problem(domain, problem) # Uses Object

    #stream_pddl = read(get_file_path(__file__, 'stream.pddl'))
    stream_pddl = None
    stream_map = DEBUG

    init = [Fact(obj.type_name, [obj.name]) for obj in problem.objects] + \
           list(map(fact_from_fd, problem.init))
    goal = And(*map(fact_from_fd, get_conjunctive_parts(problem.goal)))
    # TODO: throw error is not a conjunction

    return PDDLProblem(domain_pddl, constant_map, stream_pddl, stream_map, init, goal)

##################################################

def solve_pddlstream(n_trials=1):
    # TODO: make a simulator that randomizes these probabilities
    # TODO: include local correlation

    planner = 'forbid' # forbid | kstar
    diverse = {'selector': 'greedy', 'metric': 'p_success', 'k': 5}  # , 'max_time': 30

    stream_info = {
        'test-less_equal': StreamInfo(eager=True, p_success=0),
        'test-sum': StreamInfo(eager=True, p_success=0), # TODO: p_success=lambda x: 0.5
        #'test-open': StreamInfo(p_success=P_SUCCESS),
    }
    #problem = get_problem()
    problem = get_stuff()
    dump_pddlstream(problem)

    successes = 0.
    for _ in range(n_trials):
        print('\n'+'-'*5+'\n')
        #problem = get_problem(**kwargs)
        #solution = solve_incremental(problem, unit_costs=True, debug=True)
        solutions = solve_focused(problem, stream_info=stream_info, # planner='forbid'
                                  unit_costs=True, unit_efforts=False, debug=True,
                                  planner=planner, max_planner_time=10, diverse=diverse,
                                  #initial_complexity=1, max_iterations=1, max_skeletons=1
                                  )
        for solution in solutions:
            print_solution(solution)
            #plan, cost, certificate = solution
            #successes += is_plan(plan)
        successes += bool(solutions)
    print('Fraction {:.3f}'.format(successes / n_trials))

##################################################

def solve_pddl():
    domain_pddl = read_pddl('domain.pddl')
    problem_pddl = read_pddl('problem.pddl')

    plan, cost = solve_from_pddl(domain_pddl, problem_pddl)
    print('Plan:', plan)
    print('Cost:', cost)

def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument('-v', '--visualize', action='store_true')
    args = parser.parse_args()
    solve_pddlstream()

if __name__ == '__main__':
    main()
    #solve_pddl()


# https://github.com/AI-Planning/classical-domains/tree/master/classical/data-network-opt18
# TODO: load the initial state from a problem file
# Packet sizes
# https://github.com/tomsilver/pddlgym/blob/master/rendering/tsp.py
# https://networkx.github.io/
# https://pypi.org/project/graphviz/

# ./FastDownward/fast-downward.py --show-aliases
# ./FastDownward/fast-downward.py --build release64 --alias lama examples/fault_tolerant/data_network/domain.pddl examples/fault_tolerant/data_network/problem.pddl