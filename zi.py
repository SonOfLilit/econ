"""Zero Intelligence Agents simulation study.

Based on "Simulated Double Auction-markets with production and
storage" by Johan Dahlin, 2011 at
http://users.isy.liu.se/rt/johda87/publications/Dahlin2011-ABM.pdf.

"""

from random import uniform, choice, sample

NUM_SELLERS = 50
NUM_BUYERS = 100

GOODS = ["food"]

MAX_COST = 2.0
MAX_REDEMPTION = 2.0

TURNS = 6
MAX_ACTS = 10000

#INITIAL_MONEY = 10.0


class Agent(object):
    def __init__(self, goods, max_value):
        self.goods = goods
        self.max_value = max_value
        self.values = dict((name, uniform(0, max_value)) for name in goods)
#        self.money = INITIAL_MONEY


class Seller(Agent):
    def act(self, book):
        good = choice(self.goods)
        offer = uniform(0, self.values[good])
        return book.ask(self, good, offer)


class Buyer(Agent):
    def act(self, book):
        good = choice(self.goods)
        offer = uniform(self.values[good], self.max_value)
#        if offer <= self.money:
        return book.bid(self, good, offer)
        # if bankrupt, can't trade again
        return [self]


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
#        assert buyer.money >= price

#        buyer.money -= price
#        seller.money += price

        del self.max_asks[good]
        del self.max_askers[good]
        del self.max_bids[good]
        del self.max_bidders[good]

        return seller, buyer


def run(num_sellers, num_buyers):
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

import matplotlib.pyplot as plt
import numpy


def run_graphically(num_sellers, num_buyers):
    global prices
    prices = {"food": []}
    run(num_sellers, num_buyers)
    plot = numpy.array(prices["food"])
    plt.plot(plot)
    print numpy.average(plot), numpy.std(plot)
    plt.show()

run_graphically(50, 50)
run_graphically(50, 100)
run_graphically(100, 50)