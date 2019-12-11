# coding: utf-8

import numpy as np
from copy import copy, deepcopy
from datetime import datetime, timedelta
from ....types.orbitalstate import TLEOrbitalState, OrbitalState
from ..orbital.orbit import SimpleMeanMotionTransitionModel, CartesianTransitionModel


# Define some orbital states to test
ini_cart = np.array([[7000], [-12124], [0], [2.6679], [4.621], [0]])
out_tle = np.array([[2.674], [4.456], [0.1712], [0.3503], [0.3504],
                    [0.0007662]])

# Set the times
time1 = datetime(2011, 11, 12, 13, 45, 31) # Just a time
time2 = datetime(2011, 11, 12, 14, 45, 31) # An hour later
deltat = time2-time1

# Different types of propagator
propagator_sm = SimpleMeanMotionTransitionModel()
propagator_c = CartesianTransitionModel()

# Test the class SimpleMeanMotionTransitionModel class
def test_meanmotion_transition():
    """Tests SimpleMeanMotionTransitionModel()"""

    initial_state = TLEOrbitalState(out_tle, timestamp=time1)
    final_state = propagator_sm.transition(initial_state, deltat)

    # Check something's happened
    assert not np.all(initial_state.two_line_element == final_state.two_line_element)

    # Check the final state is correct
    final_meananomaly = np.remainder(out_tle[4][0] + 3600*out_tle[5][0],
                                     2*np.pi)
    assert np.isclose(initial_state.mean_anomaly, out_tle[4][0], rtol=1e-8)
    assert np.isclose(final_state.mean_anomaly, final_meananomaly, rtol=1e-8)


def test_cartesiantransitionmodel():
    """Tests the CartesianTransitionModel():

    Example 3.7 in [1]

    """
    # The book tells me the answer is:
    fin_cart = np.array([[-3296.8], [7413.9], [0], [-8.2977], [-0.96309], [0]])
    # But that appears only to be accurate to 1 part in 1000. (Due to rounding in
    # the examples)
    # I think the answer is more like (but not sure how rounding done in book!)
    #fin_cart = np.array([[-3297.2], [7414.2], [0], [-8.2974], [-0.96295], [0]])

    initial_state = OrbitalState(ini_cart, coordinates="Cartesian", timestamp=time1)
    initial_state.grav_parameter = 398600

    final_state = propagator_c.transition(initial_state, deltat)

    # Check something's happened
    assert not np.all(initial_state.keplerian_elements == final_state.keplerian_elements)

    # Check the elements match the book. But beware rounding
    assert np.allclose(final_state.cartesian_state_vector, fin_cart, rtol=1e-3)


def test_meanm_cart_ransition():
    """Test two transition models against each other"""

    # Set the times up
    time = time1
    dt = timedelta(minutes=3)

    # Initialise the state vector
    initial_state = OrbitalState(ini_cart, coordinates="Cartesian", timestamp=time)
    initial_state.grav_parameter = 398600

    # Make state copies to recurse
    state1 = initial_state
    state2 = deepcopy(state1)

    assert (np.allclose(state1.cartesian_state_vector, state2.cartesian_state_vector, rtol=1e-8))

    # Dumb way to do things
    while time < datetime(2011, 11, 12, 13, 45, 31) + timedelta(hours=10):
        state1 = propagator_c.transition(state1, dt)
        state2 = propagator_sm.transition(state2, dt)
        assert (np.allclose(state1.cartesian_state_vector, state2.cartesian_state_vector, rtol=1e-8))
        time = time + dt


def test_sampling():
    """test the sampling functions work"""

    # Initialise the state vector
    initial_state = OrbitalState(ini_cart, coordinates="Cartesian",
                                 timestamp=time1)
    initial_state.grav_parameter = 398600

    # noise it up
    propagator_sm.transition_noise = 1
    # take some samples
    samp_states_sm = propagator_sm.rvs(10, initial_state, deltat)

    # Do it in Cartesian
    propagator_c.noise = np.diag([10, 10, 10, 10e-3, 10e-3, 10e-3])
    samp_states_c = propagator_c.rvs(100, initial_state, deltat)

    for state in samp_states_c:
        assert(propagator_c.pdf(state, initial_state, deltat) >= 0) # PDF must be positive

    for state in samp_states_sm:
        assert(propagator_sm.pdf(state, initial_state, deltat) >= 0)

