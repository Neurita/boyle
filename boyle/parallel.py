# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# Alexandre Manhaes Savio <alexsavio@gmail.com>
# Grupo de Inteligencia Computational <www.ehu.es/ccwintco>
#
# BSD 3-Clause License
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

from functools       import partial
from multiprocessing import Pool


def parallel_function(f, n_cpus=4):

    def easy_parallize(sequence, f, n_cpus):
        """ assumes f takes sequence as input, easy w/ Python's scope """
        pool    = Pool(processes=n_cpus) # depends on available cores
        result  = pool.map(f, sequence) # for i in sequence: result[i] = f(i)
        cleaned = [x for x in result if x is not None] # getting results
        pool.close() # not optimal! but safe
        pool.join()
        return cleaned

    return partial(easy_parallize, f=f, n_cpus=n_cpus)

# function.parallel = parallel_function(test_primes)
