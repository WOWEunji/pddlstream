#!/usr/bin/env python2.7

from __future__ import print_function

import os
import time

from collections import defaultdict
from itertools import permutations

from pddlstream.algorithms.search import solve_from_pddl
from pddlstream.algorithms.focused import solve_focused

from pddlstream.algorithms.incremental import solve_incremental
from pddlstream.algorithms.focused import solve_focused
from pddlstream.utils import read, elapsed_time, get_mapping
from pddlstream.language.constants import print_solution
#from pddlstream.language.optimizer import add_result_inputs, add_result_outputs

from pddlstream.language.generator import from_test, universe_test, from_gen_fn, from_gen
from pddlstream.language.constants import print_solution, PDDLProblem, And, Fact, get_args, get_prefix
from pddlstream.language.conversion import list_from_conjunction
from pddlstream.language.stream import WildOutput, StreamInfo, Stream
from pddlstream.algorithms.search import solve_from_pddl
from pddlstream.algorithms.downward import parse_sequential_domain, parse_problem, get_conjunctive_parts, get_literals


def read_pddl(filename):
    directory = os.path.dirname(os.path.abspath(__file__))
    return read(os.path.join(directory, filename))

##################################################

def solve_pddl():
    domain_pddl = read_pddl('domain.pddl')
    problem_pddl = read_pddl('problem.pddl')

    plan, cost = solve_from_pddl(domain_pddl, problem_pddl)
    print('Plan:', plan)
    print('Cost:', cost)

##################################################

def get_problem(num=3):
    domain_pddl = read_pddl('domain.pddl')
    constant_map = {}
    stream_pddl = None
    stream_map = {}
    others = ['b{}'.format(i) for i in range(num)]

    init = [
        ('on', 'b', 'a'),
        ('on-table', 'a'),
        ('on-table', 'c'),
        ('clear', 'b'),
        ('clear', 'c'),
        ('arm-empty',),
        ('isblock', 'a'),
        ('isblock', 'b'),
        ('isblock', 'c'),
    ]
    for block in others:
        init.extend([
            ('on-table', block),
            ('clear', block),
            ('isblock', block),
        ])

    goal = ('on', 'a', 'c')
    #goal = ('clear', 'a')

    return PDDLProblem(domain_pddl, constant_map, stream_pddl, stream_map, init, goal)

def solve_pddlstream(focused=False):
    pddlstream_problem = get_problem()
    if focused:
        solution = solve_focused(pddlstream_problem, unit_costs=True)
    else:
        solution = solve_incremental(pddlstream_problem, unit_costs=True, debug=True)
    print_solution(solution)

def extract_facts(facts, objects):
    filtered_facts = []
    for fact in facts:
        #if set(get_args(fact)) & objects:
        if set(get_args(fact)) <= objects:
            filtered_facts.append(fact)
    return filtered_facts

def reduce_initial(replace=True):
    problem = get_problem()
    #stream_pddl = None
    stream_pddl = read_pddl('stream.pddl')

    # TODO: what if there are a bunch of predicates that aren't in the goal
    all_objects = {o for fact in problem.init for o in get_args(fact)}
    goal_objects = set()
    for fact in list_from_conjunction(problem.goal):
        goal_objects.update(get_args(fact))
    unused_objects = all_objects - goal_objects
    active_objects = set(goal_objects)

    print(problem.init)
    init = problem.init
    if replace:
        init = extract_facts(problem.init, goal_objects)
        print(init)
        unused_facts = set(problem.init) - set(init)
        print(unused_facts)

        facts_from_predicate = defaultdict(set)
        for fact in unused_facts:
            facts_from_predicate[get_prefix(fact)].add(fact)

        potential_streams = defaultdict(set)
        for fact in unused_facts:
            predicate = get_prefix(fact)
            used_indices = tuple(i for i, v in enumerate(get_args(fact)) if v in active_objects)
            unused_indices = tuple(i for i in range(len(get_args(fact))) if i not in used_indices)
            potential_streams[predicate, used_indices, unused_indices].add(fact)
        print(potential_streams.keys())

        for (predicate, used_indices, unused_indices), facts in potential_streams.items(): # Can always test on subsets
            # Set of values at each index
            # All mappings from the inputs to the used_indices of the input
            print(predicate, used_indices)
            inputs = {i: 'i{}'.format(i) for i in used_indices}
            outputs = {i: 'o{}'.format(i) for i in unused_indices}
            print(inputs, outputs)
            for other in facts_from_predicate:
                example = list(facts_from_predicate[other])[0]
                # len(get_args(example)) <= len(used_indices)
                domain = []
                for assignment in permutations(used_indices, r=len(get_args(example))):
                    good = True
                    for fact in facts:
                        args = get_args(fact)
                        domain_fact = (other,) + tuple(args[i] for i in assignment)
                        good &= (domain_fact in problem.init)
                    if good:
                        domain_predicate = (other,) + tuple(inputs[i] for i in assignment)
                        domain.append(domain_predicate)
                    print(other, assignment, good)


            print()


        # for predicate, facts in facts_from_predicate.items():
        #     print(predicate)
        #     print(fact, used_indices)

            #stream = Stream()
            # Input types, typing in general?
    quit()

    def test_clear(block):
        fact = ('clear', block)
        return fact in problem.init

    # TODO: the constraint satisfaction world that I did for TLPK that automatically creates streams (hpncsp)
    def sample_on(b1):
        # TODO: return all other facts that are contained just to speed up the process
        for b2 in sorted(all_objects, reverse=True):
            fact = ('on', b2, b1)
            print(fact)
            if fact in problem.init:
                active_objects.add(b2)
                new_facts = list(extract_facts(problem.init, active_objects))
                # TODO: needs to be a sequence (i.e. no sets)
                yield WildOutput(values=[(b2,)], facts=new_facts)

    stream_map = {
        'sample-block': from_gen((o,) for o in unused_objects),
        'test-block': from_test(universe_test),
        'test-arm-empty': from_test(universe_test),
        'test-clear': from_test(test_clear),
        'sample-on': sample_on,
    }
    stream_info = {
        'sample-on': StreamInfo(eager=False), #, opt_gen_fn=from_gen_fn(lambda x: [(False,)])),
    }

    start_time = time.time()
    pddlstream = PDDLProblem(problem.domain_pddl, problem.constant_map, stream_pddl, stream_map, init, problem.goal)
    #solution = solve_incremental(pddlstream, unit_costs=True, verbose=True, debug=False)
    solution = solve_focused(pddlstream, stream_info=stream_info, unit_costs=True, verbose=True, debug=False)
    print_solution(solution)
    print(elapsed_time(start_time))

##################################################

def main():
    #solve_pddl()
    #solve_pddlstream()
    reduce_initial()

if __name__ == '__main__':
    main()
