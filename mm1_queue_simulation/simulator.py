#!/usr/bin/python2

import math
import random
import bisect
import json


class Event:
    """
    class for enter/exit events
    """

    def __init__(self, time, etype):
        self.time = time
        self.etype = etype

    """operator overloading"""
    def __lt__(self, other):
        return self.time < other.time

    def __eq__(self, other):
        return self.time == other.time

    def get_time(self):
        return self.time

    def get_type(self):
        return self.etype


class Simulator:
    """
    main simulation class
    """

    """how many probabilities (PN, where N is integer) should be calculated"""
    prob_num = 0

    """offset is fraction of the time when program starts collecting statistics"""
    OFFSET = 0.01

    def __init__(self, incoming_distr_param, mi, time, distr):
        """

        :param la: lambda
        :param mi: u
        :param time: simulation time
        """

        self.incoming_distr_param = incoming_distr_param
        self.service_distr_param = service_distr_param

        self.time = time

        """array which stores enter/exit events"""
        self.events = []
        self.clients_times = []

        """total waiting time of every client"""
        self.delay = 0

        """number of events, which occurred after offset*sim_time"""
        self.events_after_offset = 0
        self.requests = 0

        if distr == 'pareto':
            self.distr = self.pareto_distr
        else:
            self.distr = self.exponent_distr
            self.la = self.incoming_distr_param
            self.mi = self.service_distr_param

            """lambda should be bigger than u"""
            assert self.la < self.mi
            self.ro = self.la / self.mi

    @staticmethod
    def exponent_distr(param):
        """
        :param param: lambda or u
        :return: random time from exponent distribution
        """
        return -math.log(1.0 - random.random()) / param

    @staticmethod
    def pareto_distr(xm):
        """
        :param xm: distribution parameter
        :return: random time from pareto distribution
        """
        return xm * pow(1 - random.random(), -1.0 / (1 + math.sqrt(2)))

    def generate_events(self):
        """
        generate random events array
        """
        curr_time = 0
        while True:
            next_event = self.distr(self.incoming_distr_param)
            if curr_time + next_event >= self.time:
                break
            if curr_time > self.time * Simulator.OFFSET:
                self.events_after_offset += 1
            self.events.append(Event(next_event + curr_time, 'enter'))
            curr_time += next_event
        self.requests = len(self.events)

    def update_stats(self, time, clients):
        """
        updates time which certain number of clients spent in system
        :param time: time between last event and current event
        :param clients: number of clients in system
        """
        while len(self.clients_times) <= clients:
            self.clients_times.append(0)
        self.clients_times[clients] += time

    def simulate(self):
        """
        start simulation, main loop of program
        """
        clients = 0
        i = 0
        curr_time = 0

        exit_event = self.events[0]
        while len(self.events) > i:
            event = self.events[i]

            if curr_time >= self.time * Simulator.OFFSET:
                self.update_stats(event.get_time() - curr_time, clients)

            if event.get_type() == 'enter':
                if clients == 0:

                    """process request immediately. if no clients in system"""
                    serv_time = event.get_time()
                    exit_event = self.process_request(serv_time)

                elif exit_event:
                    """start processing request when previous request is served"""
                    serv_time = exit_event.get_time()
                    exit_event = self.process_request(serv_time)

                if exit_event:

                    """search for index and insert an event"""
                    bisect.insort_right(self.events, exit_event)

                    if curr_time > self.time * Simulator.OFFSET:
                        self.delay += serv_time - event.get_time()

                clients += 1

            elif event.get_type() == 'exit':
                clients -= 1

            curr_time = event.get_time()
            i += 1

        self.update_stats(self.time - curr_time, clients)

    def process_request(self, serv_start):
        """
        :param serv_start: time when the request starts to be processed
        :return: event or None if exit time exceeds simulation time
        """
        exit_time = serv_start + self.exponent_distr(self.service_distr_param)
        if exit_time <= self.time:
            return Event(exit_time, 'exit')
        return None

    def make_stats(self):
        """
        function loads statistics from previous simulations,
        calculates statistics for current one and
        saves them to file
        """
        with open('stats') as f:
            stats = json.load(f)

        """to make sure statistics were collected"""
        if not self.clients_times:
            raise Exception('Empty clients times!')

        if not stats:
            for i, t in enumerate(self.clients_times):

                """consider probability of given state (PN), only if it is greater than 0.001"""
                if (t / (self.time * (1.0 - Simulator.OFFSET))) < 0.001:
                    break

            Simulator.prob_num = i - 1

            for i in range(Simulator.prob_num):
                stats['p' + str(i)] = []
            stats['avg_delay'] = []
            stats['avg_clients'] = []

        for k, t in enumerate(self.clients_times[:Simulator.prob_num]):
            stats['p' + str(k)].append(t / (self.time * (1.0 - Simulator.OFFSET)))

        avg_delay = self.delay / self.events_after_offset
        stats['avg_delay'].append(avg_delay)

        clients_weigh = 0
        for clients, clients_time in enumerate(self.clients_times):
            clients_weigh += clients * clients_time

        avg_clients = clients_weigh / (self.time * (1.0 - Simulator.OFFSET))
        stats['avg_clients'].append(avg_clients)

        with open('stats', 'w') as f:
            json.dump(stats, f)

    def print_stats(self, R):
        """
        compare measured statistics with theoretical ones

        :param R: the number of total simulations
        """
        with open('stats') as f:
            stats = json.load(f)

        for k, t in enumerate(self.clients_times[:Simulator.prob_num]):
            print 'P' + str(k)
            my_p = sum(stats['p' + str(k)]) / R
            if self.distr == self.exponent_distr:
                calc_p = (1 - self.ro)*self.ro**k
                print "{:.10f}".format(calc_p)
            print "{:.10f}\n".format(my_p)

        print 'Average delay:\n'
        if self.distr == self.exponent_distr:
            print self.ro / (self.mi * (1 - self.ro))
        avg_delay = sum(stats['avg_delay']) / R
        print '{}\n'.format(avg_delay)

        avg_clients = sum(stats['avg_clients']) / R

        print 'Average clients:\n'
        if self.distr == self.exponent_distr:
            print self.la / (self.mi - self.la)
        print '{}\n'.format(avg_clients)


if __name__ == '__main__':

    """stats file stores statistics between simulations"""
    with open('stats', 'w') as f:
        json.dump({}, f)

    """simulation parameters"""
    incoming_distr_param = 1.0 / 4  # la or xm
    service_distr_param = 1.0 / 3   # mi
    sim_time = 10e4

    simulations_num = 30
    distr = 'poisson'

    sim = None
    for i in range(simulations_num):
        print "Iteration nr {0}...".format(i)
        sim = Simulator(incoming_distr_param, service_distr_param, sim_time, distr)
        sim.generate_events()
        sim.simulate()
        sim.make_stats()

    print
    sim.print_stats(simulations_num)
