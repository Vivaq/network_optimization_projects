import itertools
import copy
import time
import random
import math


def read_MP2K(filename):
    with open(filename) as f:
        data = f.read()

    links_raw, demands_raw = data.split('-1')
    links_raw = links_raw.strip().split('\n')

    i = 0
    links = []
    for line in links_raw[1:]:
        (
            start_node,
            end_node,
            fiber_pairs,
            fiber_cost,
            lambdas
        ) = [int(l) for l in line.split(' ')]

        links.append(Link(
            i + 1,
            lambdas,
            start_node,
            end_node,
            fiber_cost,
            fiber_pairs
        ))

        i += 1

    demands_raw = demands_raw.strip().split('\n\n')

    demands = []

    i = 0
    j = 0
    paths = []
    for demand in demands_raw[1:]:

        demand = demand.split('\n')
        (
            start_node,
            end_node,
            demand_volume
        ) = [int(d) for d in demand[0].split(' ')]

        paths_num = int(demand[1])

        demands.append(Demand(demand_volume, start_node, end_node, paths_num))

        path = []
        for demand_path in demand[2:]:
            demand_path = demand_path.strip()

            path.append(Path([int(d) for d in demand_path.split(' ')[1:]]))

            j += 1

        paths.append(path)
        i += 1
    return Manager(links, demands, paths)


class Demand:
    def __init__(self, demand_volume, start_node, end_node, paths_num):
        self.demand_volume = demand_volume
        self.start_node = start_node
        self.end_node = end_node
        self.paths_num = paths_num


class Link:

    def __init__(self, link_id, lambdas, start_node, end_node, fiber_cost, all_fiber_pairs):
        self.link_id = link_id
        self.lambdas = lambdas
        self.start_node = start_node
        self.end_node = end_node
        self.fiber_cost = fiber_cost
        self.all_fiber_pairs = all_fiber_pairs

        self.used_fibers = 0

    def __str__(self):
        return 'id={0}, lambdas={1}, cost={2}, pairs={3}, used_pairs={4}\n{5}--{6}\n'.format(
            self.link_id,
            self.lambdas,
            self.fiber_cost,
            self.all_fiber_pairs,
            self.used_fibers,
            self.start_node,
            self.end_node
        )


class Path:

    def __init__(self, links, links_load=0):
        self.links = links
        self.links_load = links_load

    def __str__(self):
        return '{0}:{1}'.format(self.links, self.links_load)

    def __repr__(self):
        return str(self)


class Manager:

    def __init__(self, links, demands, paths):
        self.links = links
        self.demands = demands
        self.paths = paths

        self.population = 0

        self.reproduction_list = []
        self.population_list = []
        self.reproduction_pairs = []

        self.paths_possible_loads = []
        for demand in demands:
            self.paths_possible_loads.append(list(self.generate_possible_loads(*(demand.demand_volume, demand.paths_num))))
        self.solution_possible_loads = itertools.product(*self.paths_possible_loads)

        self.best_links = []
        self.best_paths = []
        self.best_cost = None
        self.best_paths_history = []

        self.stop_param = None
        self.mutations = 0
        self.no_improve_iterations = 0
        self.start_time = 0
        self.generations = 0

    def brute_force(self):
        best_cost = 0
        for solution_loads in self.solution_possible_loads:
            for i, loads in enumerate(solution_loads):
                for j, load in enumerate(loads):
                    self.paths[i][j].links_load = load
            self.set_link_fibres()
            cost = self.get_cost()
            if best_cost > cost:
                self.best_links = copy.deepcopy(self.links)
                self.best_paths = copy.deepcopy(self.paths)
                best_cost = cost
        self.best_cost = best_cost

    def evolution_solve(self, N, p_cross, p_mut, stop_fn, stop_param):
        self.stop_param = stop_param
        self.start_time = time.time()

        self.init_population(N)
        while stop_fn():
            self.generations += 1
            self.reproduct(N/10)

            for chrom1, chrom2 in self.reproduction_pairs:
                if p_cross > random.random():
                    new_chrom = []
                    for j in range(len(chrom1)):
                        new_chrom.append(chrom1[j] if random.random() > 0.5 else chrom2[j])
                    self.reproduction_list.append(new_chrom)

            for k in range(len(self.reproduction_list)):
                if p_mut > random.random():
                    random_demand_index = random.randint(0, len(self.reproduction_list[k]) - 1)
                    random_demand = self.reproduction_list[k][random_demand_index]
                    non_zero_indexes = [i for i, j in enumerate(random_demand) if j != 0]
                    if len(non_zero_indexes) > 1:
                        self.mutations += 1
                        lower = random.choice(non_zero_indexes)
                        greater = random.randint(0, len(random_demand) - 1)
                        random_demand[lower] -= 1
                        random_demand[greater] += 1

            possible_solutions = self.population_list + self.reproduction_list
            self.population_list = self.choose_best_N(possible_solutions, N)

    def choose_best_N(self, candidates, N):
        best_N = []
        for solution_loads in candidates:
            for i, loads in enumerate(solution_loads):
                for j, load in enumerate(loads):
                    self.paths[i][j].links_load = load
            self.set_link_fibres()
            cost = self.get_cost()
            best_N_len = len(best_N)
            if best_N_len < N:
                best_N.append((cost, solution_loads))
            elif cost < best_N[-1][0]:
                if best_N_len == N:
                    best_N = sorted(best_N)
                best_N[-1] = (cost, solution_loads)
                best_N = sorted(best_N)

        for i, loads in enumerate(best_N[0][1]):
            for j, load in enumerate(loads):
                self.paths[i][j].links_load = load

        self.best_paths = copy.deepcopy(self.paths)

        self.set_link_fibres()
        self.best_links = copy.deepcopy(self.links)

        cost = self.get_cost()
        if self.best_cost == cost:
            self.no_improve_iterations += 1
        else:
            self.no_improve_iterations = 0
        self.best_cost = cost

        self.best_paths_history.append(best_N[0][1])
        return [x[1] for x in best_N]

    def reproduct(self, la):
        samples = random.sample(self.population_list, la)
        self.reproduction_list = copy.deepcopy(samples)
        random.shuffle(self.reproduction_list)
        it = iter(self.reproduction_list)
        self.reproduction_pairs = itertools.izip(it, it)

    def init_population(self, N):
        for i in xrange(N):
            self.population_list.append([])
            for path_loads in self.paths_possible_loads:
                random_path_load = random.choice(path_loads)
                self.population_list[i].append(random_path_load)

    def set_link_fibres(self):
        for i in range(len(self.links)):
            self.links[i].used_fibers = 0
        for demand_paths in self.paths:
            for path in demand_paths:
                for link_id in path.links:
                    if link_id != self.links[link_id - 1].link_id:
                        raise Exception("Error. Invalid link id")
                    self.links[link_id - 1].used_fibers += \
                        int(math.ceil(float(path.links_load) / self.links[link_id - 1].lambdas))

    def get_cost(self):
        return max(link.used_fibers - link.all_fiber_pairs for link in self.links)

    def generate_possible_loads(self, demand_volume, paths_num):
        if paths_num == 1:
            yield [demand_volume]
        else:
            for i in xrange(demand_volume + 1):
                for j in self.generate_possible_loads(demand_volume - i, paths_num - 1):
                    yield [i] + j

    def save(self, fname):
        with open(fname, 'w') as f:
            f.write(str(len(self.best_links)) + '\n')
            for link in self.best_links:
                f.write('{0} {1} {2}\n'.format(
                    link.link_id,
                    link.lambdas,
                    link.used_fibers
                ))
            f.write('\n')
            f.write(str(len(self.demands)) + '\n')
            for i in range(len(self.demands)):
                f.write('{0} {1}\n'.format(i + 1, self.demands[i].paths_num))
                for j, path in enumerate(self.best_paths[i]):
                    f.write('{0} {1}\n'.format(j + 1, path.links_load))
                f.write('\n')

    def time_stop(self):
        return time.time() < self.start_time + self.stop_param

    def generation_stop(self):
        return self.generations < self.stop_param

    def mutation_stop(self):
        return self.mutations < self.stop_param

    def improve_stop(self):
        return self.no_improve_iterations < self.stop_param


def main():
    manager = read_MP2K('net12_1.txt')
    mode = 'evolution'

    if mode == 'brute':
        manager.brute_force()
        manager.save('brute-out.txt')

        print manager.best_cost

    elif mode == 'evolution':
        random.seed(300)
        population = 100

        p_cross = 0.9
        p_mut = 0.5

        stop_function = manager.improve_stop
        stop_parameter = 20

        manager.evolution_solve(
            population,
            p_cross,
            p_mut,
            stop_function,
            stop_parameter
        )

        print manager.best_cost

        with open('best_chromosomes_history', 'w') as f:
            for record in manager.best_paths_history:
                f.write(repr(record) + '\n')

        manager.save('evo-out.txt')


if __name__ == '__main__':
    main()
