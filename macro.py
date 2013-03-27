import numpy

MAX_ROUNDS = 1000

NUM_PRICE_SIMULATIONS = 7
NUM_TRADE_ROUNDS = 3

GOODS = ["water", "wood", "stone", "food"]
WATER, WOOD, STONE, FOOD = xrange(len(GOODS))

COSTS_ONLY_MONEY = numpy.zeros(len(GOODS))
SPELLS = [(0.0, FOOD, 0.0, COSTS_ONLY_MONEY),
          (1.0, WATER, 3.0, COSTS_ONLY_MONEY),
          (6.0, WOOD, 10.0, COSTS_ONLY_MONEY),
          (5.0, FOOD, 2.0, numpy.array([0.0, 3.0, 0.0, 0.0])),
          (5.0, FOOD, 2.0, numpy.array([1.0, 1.0, 0.0, 0.0])),
          (3.0, FOOD, 2.0, numpy.array([3.0, 0.0, 0.0, 0.0])),
          (4.0, FOOD, 12.0, numpy.array([3.0, 0.0, 1.0, 0.0])),
          (5.0, STONE, 20.0, numpy.array([5.0, 6.0, 4.0, 0.0])),
          (7.0, WATER, 5.0, numpy.array([0.0, 1.0, 0.3, 0.0])),
          (30.0, FOOD, 200.0, numpy.array([3.0, 3.0, 0.0, 0.0]))]

INITIAL_SKILLS_LOC = 2.0
INITIAL_SKILLS_SCALE = 0.8
INITIAL_PRICES = numpy.ones(len(GOODS))

MINIMUM_PROFIT_COST_RATIO = 1.0 + 0.2
MINIMUM_PROFIT = 2.0
MAX_PRICE = 100.0
PRICE_INCREMENT = 1.0
FOOD_DEMAND = numpy.zeros(len(GOODS))
FOOD_DEMAND[FOOD] += 1.2


class Agent(object):
    def __init__(self, market):
        # this is the kind of thing programmers die a slow death
        # for... but it's the fault of the numpy API, not me
        self.profits = numpy.vectorize(self.profit)

        self.market = market

        self.magic = 30.0
        self.magic_regeneration = 10.0
        self.skills = numpy.random.normal(INITIAL_SKILLS_LOC,
                                          INITIAL_SKILLS_SCALE,
                                          size=len(SPELLS))
        self.todays_spell = None

    def sleep(self):
        self.magic += self.magic_regeneration

    def choose_work(self):
        if self.todays_spell is None or numpy.random.rand() > 0.8:
            profits = self.profits(numpy.arange(len(SPELLS)))
            self.todays_spell = None
            if any(profits > 0):
                self.todays_spell = numpy.random.choice(
                    len(SPELLS),
                    p=profits/profits.sum())

    def profit(self, spell):
        cost, produced_value = self.cost_value_analysis(spell)
        return max(0.0, (produced_value - cost) * MINIMUM_PROFIT_COST_RATIO)

    def cost_value_analysis(self, spell):
        amount, good, magic_cost, formula = SPELLS[spell]
        formula = formula + FOOD_DEMAND
        skill = self.skills[spell]
        produced_amount = amount * skill
        if good == FOOD:
            self_supplied_food = min(produced_amount, formula[FOOD])
            produced_amount -= self_supplied_food
            formula[FOOD] -= self_supplied_food
        cost = magic_cost + self.market.prices.dot(formula) - self.magic_regeneration
        produced_value = self.market.prices[good] * produced_amount
        return cost, produced_value

    def get_demand(self):
        if self.todays_spell:
            _amount, _good, _magic_cost, formula = SPELLS[self.todays_spell]
            return formula + FOOD_DEMAND
        return COSTS_ONLY_MONEY

    def get_supply(self):
        good = requested_price = amount = None
        if self.todays_spell is not None:
            amount, good, _magic_cost, _formula = SPELLS[self.todays_spell]
            cost, _value = self.cost_value_analysis(self.todays_spell)
            requested_price = max(MINIMUM_PROFIT,
                                  MINIMUM_PROFIT_COST_RATIO * cost)
        return good, requested_price, amount

    @property
    def occupation(self):
        return self.todays_spell or -1


class Market(object):
    def __init__(self, num_agents):
        self.agents = [Agent(self) for _i in xrange(num_agents)]
        self.prices = numpy.array(INITIAL_PRICES)

        self.iteration = -1
        self.history = History(num_agents)


    def day(self):
        for agent in self.agents:
            agent.sleep()
        for _i in xrange(NUM_PRICE_SIMULATIONS):
            self.choose_prices()
        supplies, demands, prices = [], [], []
        for _i in xrange(NUM_TRADE_ROUNDS):
            supply, demand = self.choose_prices()
            prices.append(self.prices)
            supplies.append(supply)
            demands.append(demand)
            self.trade()
        
        self.iteration += 1
        self.history.record(self.iteration, self.agents, prices, supplies, demands)

    def choose_prices(self):
        demand_met_by_supply = True

        demands = numpy.zeros(len(GOODS))
        # extra items to ensure we have at least one empty "offer" per good
        offers = numpy.zeros(len(self.agents) + len(GOODS),
                             dtype=[('good', int),
                                    ('price', 'f8'),
                                    ('amount', 'f8')])
        for i, agent in enumerate(self.agents):
            agent.choose_work()
            demands += agent.get_demand()
            supply = agent.get_supply()
            if supply[0] is None:
                supply = (0, 0, 0)
            offers[i] = supply
        for g in xrange(len(GOODS)):
            offers[-g - 1] = (g, 0.5, 0)
        # sort first by good, then by price (amount sort order doesn't matter)
        offers.sort(order=('good', 'price'))
        # separate into different arrays for different goods (a bit of
        # magic, try it in ipython to figure out how it works)
        supplies = numpy.split(offers,
                               numpy.where(numpy.diff(offers['good']) != 0)[0] + 1)
        for good in xrange(len(GOODS)):
            is_supply_above_demand = \
                len(supplies[good][supplies[good]['amount'].cumsum() >= demands[good]]) > 0
#            print good, supplies[good]['amount'].sum(), demand[good]
            # supply_above_demand is an array of the rows in
            # supplies[good] where the condition holds
            if is_supply_above_demand:
                supply_up_to_demand = supplies[good][supplies[good]['amount'].cumsum() <= demands[good]]
                price_at_demand = numpy.average(supply_up_to_demand['price'])
#                print "price", good, price_at_demand
                self.change_price(good, price_at_demand)
            else:
                # demand cannot be met by supply. raise price and try again

                # lower all prices a bit, compensates for some of the prices artificially rising
                self.prices /= 1.2
                self.change_price(good, self.prices[good] + PRICE_INCREMENT)
#                self.prices[good] = min(self.prices[good] * 1.4 + 3.0, 100.0)  # * HIGH_DEMAND_PRICE_FACTOR
#                print "demand not met by supply"
                demand_met_by_supply = False

        if not demand_met_by_supply:
#            print "demand not met by supply, trying again"
#            print self.prices
            return self.choose_prices()

        return [s['amount'].sum() for s in supplies], demands

    def change_price(self, good, target):
        target = min(target, MAX_PRICE)
        current = self.prices[good]
        increment = PRICE_INCREMENT
        self.prices[good] = min(current + increment, max(current - increment, target))

    def trade(self):
        # TODO: move to agent
        for agent in self.agents:
            bought = agent.get_demand()
            cost = self.prices.dot(bought)
            good, _requested_price, amount_sold = agent.get_supply()
            if good is not None:
                profit = self.prices[good] * amount_sold
                agent.magic += profit - cost
                agent.skills[good] = numpy.sqrt(agent.skills[good] ** 2 + 0.05)


class History(object):
    def __init__(self, num_agents):
        self.goods = numpy.zeros((MAX_ROUNDS, len(GOODS)),
                                 dtype=[('price', 'f4'),
                                        ('supply', 'f4'),
                                        ('demand', 'f4')])
        self.skills = numpy.zeros((MAX_ROUNDS, num_agents, len(SPELLS)),
                                  dtype=numpy.float32)
        self.occupations = numpy.zeros((MAX_ROUNDS, num_agents))

    def record(self, iteration, agents, prices, supplies, demands):
        self.skills[iteration] = [agent.skills for agent in agents]
        self.occupations[iteration] = [agent.occupation for agent in agents]
        self.goods[iteration]['price'] = numpy.average(prices, axis=0)
        self.goods[iteration]['supply'] = numpy.average(supplies, axis=0)
        self.goods[iteration]['demand'] = numpy.average(demands, axis=0)


def run():
    market = Market(100)

    import matplotlib.pyplot as plt

    market.day()

    plt.figure()
    plt.hist(market.history.skills[market.iteration], 20, label=map(str, SPELLS))
    plt.legend()

    for _i in xrange(30):
        print
        print market.iteration
        print
        market.day()

    plt.figure()
    plt.hist(market.history.skills[market.iteration], 20, label=map(str, SPELLS))
    plt.legend()

    plt.figure()
    for i in xrange(len(GOODS)):
        plt.plot(market.history.goods[:market.iteration + 1, i]['price'],
                 label=GOODS[i] + " p")
    plt.legend()

    plt.figure()
    for i in xrange(len(GOODS)):
        plt.plot(market.history.goods[:market.iteration + 1, i]['supply'] / 5.0,
                 label=GOODS[i] + " s")
        plt.plot(market.history.goods[:market.iteration + 1, i]['demand'],
                 label=GOODS[i] + " d")
    plt.legend()

    plt.figure()
    for spell in xrange(-1, len(SPELLS)):
        label = ""
        if spell >= 0:
            label = str(SPELLS[spell])
        plt.plot(xrange(market.iteration),
                 [(market.history.occupations[i] == spell).sum()
                  for i in xrange(market.iteration)], label=label)
        plt.legend()

    print market.prices
    plt.show()
    #plt.waitforbuttonpress()

run()
