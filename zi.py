"""Zero Intelligence Agents simulation study.

Based on "Simulated Double Auction-markets with production and
storage" by Johan Dahlin, 2011 at
http://users.isy.liu.se/rt/johda87/publications/Dahlin2011-ABM.pdf.

"""

from random import uniform, choice, sample

GOODS = ["food"]

MAX_COST = 2.0
MAX_REDEMPTION = 2.0

MAX_LEARNING = 0.1
MIN_MOMENTUM = 0.1
MAX_MOMENTUM = MIN_MOMENTUM + 0.3

TURNS = 6
MAX_ACTS = 10000

INITIAL_MONEY = 10.0

prices = {}


class Agent(object):
    def __init__(self, goods, max_value):
        self.goods = goods
        self.max_value = max_value
        self.values = self.uniform_parameter(0, max_value)
        self.money = INITIAL_MONEY

    def uniform_parameter(self, a, b):
        return dict((name, uniform(a, b)) for name in self.goods)


class Seller(Agent):
    def act(self, book):
        good = choice(self.goods)
        offer = uniform(0, self.values[good])
        return book.ask(self, good, offer)


class Buyer(Agent):
    def act(self, book):
        good = choice(self.goods)
        offer = uniform(self.values[good], self.max_value)
        if offer <= self.money:
            return book.bid(self, good, offer)
        return []


class AgentPlus(Agent):
    def __init__(self, goods, max_value):
        Agent.__init__(self, goods, max_value)
        self.learning_coefficient = self.uniform_parameter(0, MAX_LEARNING)
        self.momentum_coefficient = \
            self.uniform_parameter(MIN_MOMENTUM, MAX_MOMENTUM)
        self.initial_markup = 1 # TODO

class Book(object):
    def __init__(self, goods):
        self.goods = goods
        self.max_asks = {}
        self.max_askers = {}
        self.max_bids = {}
        self.max_bidders = {}

    def ask(self, agent, good, offer):
        if not good in self.max_asks or offer < self.max_asks[good]:
            self.max_asks[good] = offer
            self.max_askers[good] = agent
        if good in self.max_bids and offer < self.max_bids[good]:
            return self.trade(good, self.max_bids[good])
        return []

    def bid(self, agent, good, offer):
        if not good in self.max_bids or offer > self.max_bids[good]:
            self.max_bids[good] = offer
            self.max_bidders[good] = agent
        if good in self.max_asks and offer > self.max_asks[good]:
            return self.trade(good, self.max_asks[good])
        return []

    def trade(self, good, price):
        prices[good].append(price)

        seller = self.max_askers[good]
        buyer = self.max_bidders[good]
        assert buyer.money >= price

        buyer.money -= price
        seller.money += price

        del self.max_asks[good]
        del self.max_askers[good]
        del self.max_bids[good]
        del self.max_bidders[good]

        return seller, buyer


def run(num_sellers, num_buyers):
    global prices
    prices = {"food": []}

    sellers = set(Seller(GOODS, MAX_COST) for _ in xrange(num_sellers))
    buyers = set(Buyer(GOODS, MAX_REDEMPTION) for _ in xrange(num_buyers))

    for _turn in xrange(TURNS):
        available = set()
        available.update(sellers)
        available.update(buyers)
        book = Book(GOODS)
        i = 0
        while i < MAX_ACTS and available:
            i += 1
            # sample is a bit like choice but works for sets
            agent = sample(available, 1)[0]
            for agent_to_remove in agent.act(book):
                available.remove(agent_to_remove)

    return sellers, buyers


import matplotlib.pyplot as plt
import numpy


def run_graphically(num_sellers, num_buyers):
    sellers, buyers = run(num_sellers, num_buyers)

    plot = numpy.array(prices["food"])

    plt.figure(1)
    plt.subplot(131)
    plt.plot(plot)

    plt.subplot(132)
    sellers = numpy.array([s.values["food"] for s in sellers])
    sellers.sort()
    plt.plot(sellers)
    buyers = numpy.array([b.values["food"] for b in buyers])
    buyers.sort()
    buyers = buyers[::-1]
    plt.plot(buyers)
    theoretical = sellers[(buyers < sellers).nonzero()[0][0]]
    average = numpy.average(plot)
    std = numpy.std(plot)

    ones = numpy.ones_like(sellers)
    plt.plot(ones * (average - std), 'r--')
    plt.plot(ones * average, 'r--')
    plt.plot(ones * (average + std), 'r--')
    plt.plot(ones * theoretical, 'b--')

    indices = numpy.arange(1, TURNS) * int(1 + len(plot) / TURNS)
    plots = numpy.split(plot, indices)
    rmse = [numpy.sqrt(numpy.sum((p - theoretical) ** 2) / len(p))
            for p in plots]

    plt.subplot(133)
    plt.axis([0, 5, 0, 1])
    plt.plot(rmse)

    plt.show()

run_graphically(50, 50)
#run_graphically(50, 100)
#run_graphically(100, 50)
