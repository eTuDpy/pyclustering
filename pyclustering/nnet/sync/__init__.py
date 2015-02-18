'''

Neural Network: Oscillatory Neural Network based on Kuramoto model

Based on article description:
 - A.Arenas, Y.Moreno, C.Zhou. Synchronization in complex networks. 2008.
 - X.B.Lu. Adaptive Cluster Synchronization in Coupled Phase Oscillators. 2009.
 - X.Lou. Adaptive Synchronizability of Coupled Oscillators With Switching. 2012.
 - A.Novikov, E.Benderskaya. Oscillatory Neural Networks Based on the Kuramoto Model. 2014.

Copyright (C) 2015    Andrei Novikov (spb.andr@yandex.ru)

pyclustering is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyclustering is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''


import numpy;
import random;
import math;
import scipy.spatial;

import pyclustering.support;
import pyclustering.core.wrapper as wrapper;

import matplotlib.pyplot as plt;

from scipy import pi;
from scipy.integrate import odeint;
from scipy.integrate import ode;

from pyclustering.support import euclidean_distance;
from pyclustering.nnet import *;


class sync_network(network, network_interface):    
    "Model of oscillatory network that is based on the Kuramoto model of synchronization."
    
    # Protected members:
    _name = 'Phase Sync Network'
    _phases = None;                     # Current phases of oscillators.
    _freq = None;                       # Own frequencies of oscillators.
    _weight = 0;                        # Strength of connections between oscillators.
    
    _ccore_network_pointer = None;      # Pointer to CCORE Sync implementation of the network.
    
    # Properties of class that represents oscillatory neural network
    @property
    def name(self):
        "Returns title of the network."
        return self._name;
    
    @property
    def phases(self):
        "Returns list of phases of oscillators."
        return self._phases;


    def __init__(self, num_osc, weight = 1, frequency = 0, type_conn = conn_type.ALL_TO_ALL, conn_represent = conn_represent.MATRIX, initial_phases = initial_type.RANDOM_GAUSSIAN, ccore = False):
        "Constructor of oscillatory network is based on Kuramoto model."
        
        "(in) num_osc            - number of oscillators in the network."
        "(in) weight             - coupling strength of the links between oscillators."
        "(in) frequency          - multiplier of internal frequency of the oscillators."
        "(in) type_conn          - type of connection between oscillators in the network (all-to-all, grid, bidirectional list, etc.)."
        "(in) conn_represent     - internal representation of connection in the network: matrix or list."
        "(in) initial_phases     - type of initialization of initial phases of oscillators (random, uniformly distributed, etc.)."
        
        if (ccore is True):
            self._ccore_network_pointer = wrapper.create_sync_network(num_osc, weight, frequency, type_conn, initial_phases);
        else:   
            super().__init__(num_osc, type_conn, conn_represent);
            
            self._weight = weight;
            
            self._phases = list();
            self._freq = list();
            
            for index in range(0, num_osc, 1):    
                if (initial_phases == initial_type.RANDOM_GAUSSIAN):
                    self._phases.append(random.random() * 2.0 * pi);
                elif (initial_phases == initial_type.EQUIPARTITION):
                    self._phases.append( pi / num_osc * index);
                
                self._freq.append(random.random() * frequency);
    
    
    def __del__(self):
        "Destructor of oscillatory network is based on Kuramoto model."
        if (self._ccore_network_pointer is not None):
            wrapper.destroy_sync_network(self._ccore_network_pointer);
            self._ccore_network_pointer = None;
    
    
    def sync_order(self):
        "Returns level of global synchorization in the network."
        
        if (self._ccore_network_pointer is not None):
            return wrapper.sync_order(self._ccore_network_pointer);
        
        exp_amount = 0;
        average_phase = 0;
        
        for index in range(0, self.num_osc, 1):
            exp_amount += math.expm1( abs(1j * self._phases[index]) );
            average_phase += self._phases[index];
        
        exp_amount /= self.num_osc;
        average_phase = math.expm1( abs(1j * (average_phase / self.num_osc)) );
        
        return abs(average_phase) / abs(exp_amount);    
    
    
    def sync_local_order(self):
        "Returns level of local (partial) synchronization in the network."
        
        if (self._ccore_network_pointer is not None):
            return wrapper.sync_local_order(self._ccore_network_pointer);
        
        exp_amount = 0;
        num_neigh = 0;
        
        for i in range(0, self.num_osc, 1):
            for j in range(0, self.num_osc, 1):
                if (self.has_connection(i, j) == True):
                    exp_amount += math.exp(-abs(self._phases[j] - self._phases[i]));
                    num_neigh += 1;
        
        if (num_neigh == 0):
            num_neigh = 1;
        
        return exp_amount / num_neigh;        
    
    
    def phase_kuramoto(self, teta, t, argv):
        "Returns result of phase calculation for specified oscillator in the network."
        
        "(in) teta        - phase of the oscillator that is differentiated."
        "(in) t           - current time of simulation."
        "(in) argv        - index of the oscillator in the list."
        
        "Returns new phase for specified oscillator (don't assign here)."
        
        index = argv;
        phase = 0;
        for k in range(0, self.num_osc):
            if (self.has_connection(index, k) == True):
                phase += math.sin(self._phases[k] - teta);
            
        return ( self._freq[index] + (phase * self._weight / self.num_osc) );             
    
    
    def allocate_sync_ensembles(self, tolerance = 0.01):
        "Allocate clusters in line with ensembles of synchronous oscillators where each" 
        "synchronous ensemble corresponds to only one cluster."
        
        "(in) tolerance        - maximum error for allocation of synchronous ensemble oscillators."
        
        "Returns list of grours (lists) of indexes of synchronous oscillators."
        "For example [ [index_osc1, index_osc3], [index_osc2], [index_osc4, index_osc5] ]."
        
        if (self._ccore_network_pointer is not None):
            return wrapper.allocate_sync_ensembles_sync_network(self._ccore_network_pointer, tolerance);
        
        clusters = [];
        if (self._num_osc > 0):
            clusters.append([0]);
        
        for i in range(1, self._num_osc, 1):
            cluster_allocated = False;
            for cluster in clusters:
                for neuron_index in cluster:
                    if ( (self._phases[i] < (self._phases[neuron_index] + tolerance)) and (self._phases[i] > (self._phases[neuron_index] - tolerance)) ):
                        cluster_allocated = True;
                        cluster.append(i);
                        break;
                
                if (cluster_allocated == True):
                    break;
            
            if (cluster_allocated == False):
                clusters.append([i]);
        
        return clusters;
    
    
    def simulate(self, steps, time, solution = solve_type.FAST, collect_dynamic = True):
        "Performs static simulation of Sync oscillatory network."
        
        "(in) steps            - number steps of simulations during simulation."
        "(in) time             - time of simulation."
        "(in) solution         - type of solution (solving)."
        "(in) collect_dynamic  - if True - returns whole dynamic of oscillatory network, otherwise returns only last values of dynamics."
        
        "Returns dynamic of oscillatory network. If argument 'collect_dynamic' = True, than return dynamic for the whole simulation time,"
        "otherwise returns only last values (last step of simulation) of dynamic."
        
        return self.simulate_static(steps, time, solution, collect_dynamic);


    def simulate_dynamic(self, order = 0.998, solution = solve_type.FAST, collect_dynamic = False, step = 0.1, int_step = 0.01, threshold_changes = 0.0000001):
        "Performs dynamic simulation of the network until stop condition is not reached. Stop condition is defined by"
        "input argument 'order'."
        
        "(in) order              - order of process synchronization, destributed 0..1."
        "(in) solution           - type of solution (solving)."
        "(in) collect_dynamic    - if True - returns whole dynamic of oscillatory network, otherwise returns only last values of dynamics."
        "(in) step               - time step of one iteration of simulation."
        "(in) int_step           - integration step, should be less than step."
        "(in) threshold_changes  - additional stop condition that helps prevent infinite simulation, defines limit of changes of oscillators between current and previous steps."
        
        "Returns dynamic of oscillatory network. If argument 'collect_dynamic' = True, than return dynamic for the whole simulation time,"
        "otherwise returns only last values (last step of simulation) of dynamic."
        
        if (self._ccore_network_pointer is not None):
            return wrapper.simulate_dynamic_sync_network(self._ccore_network_pointer, order, solution, collect_dynamic, step, int_step, threshold_changes);
        
        # For statistics and integration
        time_counter = 0;
        
        # Prevent infinite loop. It's possible when required state cannot be reached.
        previous_order = 0;
        current_order = self.sync_local_order();
        
        # If requested input dynamics
        dyn_phase = [];
        dyn_time = [];
        if (collect_dynamic == True):
            dyn_phase.append(self._phases);
            dyn_time.append(0);
        
        # Execute until sync state will be reached
        while (current_order < order):                
            # update states of oscillators
            self._phases = self._calculate_phases(solution, time_counter, step, int_step);
            
            # update time
            time_counter += step;
            
            # if requested input dynamic
            if (collect_dynamic == True):
                dyn_phase.append(self._phases);
                dyn_time.append(time_counter);
            else:
                dyn_phase = self._phases;
                dyn_time = time_counter;
                
            # update orders
            previous_order = current_order;
            current_order = self.sync_local_order();
            
            # hang prevention
            if (abs(current_order - previous_order) < threshold_changes):
                print("Warning: sync_network::simulate_dynamic - simulation is aborted due to low level of convergence rate (order = " + str(current_order) + ").");
                break;
                
        return (dyn_time, dyn_phase);


    def simulate_static(self, steps, time, solution = solve_type.FAST, collect_dynamic = False):
        "Performs static simulation of oscillatory network."
        
        "(in) steps            - number steps of simulations during simulation."
        "(in) time             - time of simulation."
        "(in) solution         - type of solution (solving)."
        "(in) collect_dynamic  - if True - returns whole dynamic of oscillatory network, otherwise returns only last values of dynamics."
        
        "Returns dynamic of oscillatory network. If argument 'collect_dynamic' = True, than return dynamic for the whole simulation time,"
        "otherwise returns only last values (last step of simulation) of dynamic."  
        
        if (self._ccore_network_pointer is not None):
            return wrapper.simulate_sync_network(self._ccore_network_pointer, steps, time, solution, collect_dynamic);
        
        dyn_phase = None;
        dyn_time = None;
        
        if (collect_dynamic == True):
            dyn_phase = [];
            dyn_time = [];
            
            dyn_phase.append(self._phases);
            dyn_time.append(0);
        
        step = time / steps;
        int_step = step / 10.0;
        
        for t in numpy.arange(step, time + step, step):
            # update states of oscillators
            self._phases = self._calculate_phases(solution, t, step, int_step);
            
            # update states of oscillators
            if (collect_dynamic == True):
                dyn_phase.append(self._phases);
                dyn_time.append(t);
            else:
                dyn_phase = self._phases;
                dyn_time = t;
        
        return (dyn_time, dyn_phase);        


    def _calculate_phases(self, solution, t, step, int_step):
        "Calculates new phases for oscillators in the network in line with current step."
        
        "(in) solution        - type solver of the differential equation."
        "(in) t               - time of simulation."
        "(in) step            - step of solution at the end of which states of oscillators should be calculated."
        "(in) int_step        - step differentiation that is used for solving differential equation."
        
        "Returns list of new states (phases) for oscillators."
        
        next_phases = [0] * self.num_osc;    # new oscillator _phases
        
        for index in range (0, self.num_osc, 1):
            if (solution == solve_type.FAST):
                result = self._phases[index] + self.phase_kuramoto(self._phases[index], 0, index);
                next_phases[index] = phase_normalization(result);
                
            elif (solution == solve_type.RK4):
                result = odeint(self.phase_kuramoto, self._phases[index], numpy.arange(t - step, t, int_step), (index , ));
                next_phases[index] = phase_normalization(result[len(result) - 1][0]);
            
            else:
                raise NameError("Solver '" + solution + "' is not supported");
        
        return next_phases;
        

def phase_normalization(teta):
    "Normalization of phase of oscillator that should be placed between [0; 2 * pi]."
    
    "(in) teta        - phase of oscillator."
    
    "Returns normalized phase."
    
    norm_teta = teta;
    while (norm_teta > (2.0 * pi)) or (norm_teta < 0):
        if (norm_teta > (2.0 * pi)):
            norm_teta -= 2.0 * pi;
        else:
            norm_teta += 2.0 * pi;
    
    return norm_teta;