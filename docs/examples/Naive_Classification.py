#!/usr/bin/env python
# coding: utf-8

"""
Forward Algorithm
=================
An example of the forward algorithm using Stone Soup components.
"""

# %%
# Modelling the state space
# -------------------------
# We model a target that can be one of three categories: Bicycle, Car or Bus.
# In this simple instance, the target does not switch between these categories (ie. if it is a bus,
# it stays a bus).
# This is modelled in the state space by 3 state vector elements. The first component indicates
# the probability that the target is a bicycle, the second that it is a car, and the third that it
# is a bus.
# For this model, it will remain a bus, therefore the 3rd state vector component will be
# :math:`1` throughout, with the other components remaining :math:`0`.

import numpy as np
from stonesoup.types.state import State, StateVector

np.random.seed(1991)

gt = []
nsteps=100

for step in range(nsteps):
    gt.append(State(StateVector([0, 0, 1])))  # bicycle, car, bus


# %%
# Modelling state transition
# --------------------------
# We require a model of the state transition in order to track the target's classification.
# This will be a simple linear map, represented by a :math:`3\times 3` matrix with no noise added.
# We might not know that the target does not switch classification, so the matrix should not simply
# be the identity matrix.
#
# .. math::
#       T = \begin{bmatrix}
#  		P(Bicycle_{t}|Bicycle_{t-1}) & P(Bicycle_{t}|Car_{t-1}) & P(Bicycle_{t}|Bus_{t-1}) \\
#  		P(Car_{t}|Bicycle_{t-1}) & P(Car_{t}|Car_{t-1}) & P(Car_{t}|Bus_{t-1}) \\
#  		P(Bus_{t}|Bicycle_{t-1}) & P(Bus_{t}|Car_{t-1}) & P(Bus_{t}|Bus_{t-1})
#  	    \end{bmatrix}
#
# The transitioned state is given by
# :math:`f(X_{t-1})_{j} = T_{ij}{X_{t-1}}_{i} = T^T_{ji}{X_{t-1}}_{i}`.
# Therefore, we take the transpose :math:`f(X_{t-1}) = T^{T}X_{t-1}` when transitioning the state.

F = np.array([[0.8, 0.1, 0.1],
              [0.1, 0.8, 0.1],
              [0, 0.1, 0.9]])


def transit(state):
    return F.T @ state.state_vector


# %%
# Modelling observations
# ----------------------
# Observations of the target may be incorrect, and affected by various input from a sensor.
# We simply model an observer of the target's size, with an understanding of the underlying
# distribution of bicycle, car and bus targets that are/could be small, medium or large.
# This is defined in the emission matrix, utilised by the observer model to determine a measurement
# which just says whether the target is small, medium or large. Similar to the state space
# categories, this is represented by a detection state vector with 3 components, either 0 or 1.
# To determine which classification is observed, we randomly sample from the multinomial
# distribution defined by the row of the emission matrix corresponding to the most likely state of
# the target.
#
# .. math::
#       E = \begin{bmatrix}
# 		P(Small | Bicycle) & P(Medium | Bicycle) & P(Large | Bicycle)\\
# 		P(Small | Car) & P(Medium | Car) & P(Large | Car)\\
# 		P(Small | Bus) & P(Medium | Bus) & P(Large | Bus)
# 	    \end{bmatrix}
#

import scipy

E = np.array([[0.89, 0.1, 0.01],
              [0.3, 0.3, 0.4],
              [0.1, 0.3, 0.6]])

# ie. 89% of bicycles are small, 10% are medium, 1% are large.


def observe(state):
    x = state.state_vector

    row_num = np.argmax(x)

    row = E[row_num]

    sample = _sample(row)

    return StateVector(sample)


def _sample(row):
    rv = scipy.stats.multinomial(n=1, p=row)
    return rv.rvs(size=1, random_state=None)


# %%

from stonesoup.types.detection import Detection

observations = []
for i in range(0, nsteps):
    observations.append(Detection(observe(gt[i])))


# %%
# Tracking classification
# -----------------------
# Posterior state is given by :math:`X_{t} = EZ_{t} * T^T X_{t-1}`, where :math:`X_{t}` is the
# state estimate at time :math:`t`, :math:`E` the emission matrix, :math:`Z_{t}` an observation at
# time :math:`t` and :math:`T` the transition model matrix, where :math:`*` notates piecewise
# vector multiplication.
# We begin with a prior state guess, whereby we have no knowledge of the target's classifcaiton,
# and therefore appoint equal probability to each category.

prior = State(StateVector([1/3, 1/3, 1/3]))

# %%
# Next, we carry-out the tracking loop, making sure to normalise the posterior estimate at each
# iteration, as track state vector components represent a categorical distribution (they must
# therefore sum to 1).

from stonesoup.types.track import Track

track = Track()
for observation in observations:
    TX = transit(prior)
    EY = E @ observation.state_vector

    prenormalise = np.multiply(TX, EY)

    normalise = prenormalise / np.sum(prenormalise)

    track.append(State(normalise))
    prior = track[-1]


# %%
# Plotting
# --------
# We plot the track classification as a stacked bar graph. Green indicates bicycle, white car, and
# red bus. The larger a particular bar, the greater the probability that the track at that time
# is of the corresponding classification.
# Observations are plotted underneath this graph. Light blue indicates an observation that the
# target is small, blue that it is medium, and dark blue that it is large.

import matplotlib.pyplot as plt

t_a, t_n, t_e = np.array([list(state.state_vector) for state in track]).T
d_s, d_m, d_l = np.array([list(state.state_vector) for state in observations]).T

d_colours = []
for s in observations:
    sv = s.state_vector
    if sv[0]:
        d_colours.append('lightblue')
    elif sv[1]:
        d_colours.append('blue')
    else:
        d_colours.append('darkblue')
d = len(t_a) * [-0.05]

ind = np.arange(nsteps)
width = 1
p1 = plt.bar(ind, t_a, width, color='g')
p2 = plt.bar(ind, t_n, width, bottom=t_a, color='w')
p3 = plt.bar(ind, t_e, width, bottom=[t_a[i] + t_n[i] for i in range(len(t_a))], color='r')
p4 = plt.bar(ind, d, width, color=d_colours)

truth_index = np.argmax(gt[0].state_vector)
category = ['bicycle', 'car', 'bus'][truth_index]
emit = str(E[truth_index])
title = 'GT: ' + category + ', E: ' + emit

plt.title(title)
plt.legend((p1[0], p2[0], p3[0]), ('Bicycle', 'Car', 'Bus'))