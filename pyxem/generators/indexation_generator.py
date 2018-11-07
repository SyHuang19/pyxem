# -*- coding: utf-8 -*-
# Copyright 2017-2018 The pyXem developers
#
# This file is part of pyXem.
#
# pyXem is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyXem is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyXem.  If not, see <http://www.gnu.org/licenses/>.

"""Indexation generator and associated tools.
"""

import numpy as np
import hyperspy.api as hs
from math import acos, cos, sin, pi, radians, degrees
import itertools

from pyxem.signals.indexation_results import TemplateMatchingResults

from pyxem.utils.sim_utils import transfer_navigation_axes

from pyxem.utils.indexation_utils import correlate_library
from pyxem.utils.indexation_utils import index_magnitudes
from pyxem.utils.indexation_utils import match_vectors

import hyperspy.api as hs


class IndexationGenerator():
    """Generates an indexer for data using a number of methods.

    Parameters
    ----------
    signal : ElectronDiffraction
        The signal of electron diffraction patterns to be indexed.
    diffraction_library : DiffractionLibrary
        The library of simulated diffraction patterns for indexation.
    """

    def __init__(self,
                 signal,
                 diffraction_library):
        self.signal = signal
        self.library = diffraction_library

    def correlate(self,
                  n_largest=5,
                  keys=[],
                  mask=None,
                  *args,
                  **kwargs):
        """Correlates the library of simulated diffraction patterns with the
        electron diffraction signal.

        Parameters
        ----------
        n_largest : int
            The n orientations with the highest correlation values are returned.
        keys : list
            If more than one phase present in library it is recommended that
            these are submitted. This allows a mapping from the number to the
            phase.  For example, keys = ['si','ga'] will have an output with 0
            for 'si' and 1 for 'ga'.
        mask : Array
            Array with the same size as signal (in navigation) True False
        *args : arguments
            Arguments passed to map().
        **kwargs : arguments
            Keyword arguments passed map().

        Returns
        -------
        matching_results : TemplateMatchingResults
            Navigation axes of the electron diffraction signal containing
            correlation results for each diffraction pattern. As an example, the
            signal in Euler reads:
                    ( Library Number , Z , X , Z , Correlation Score)

        """
        signal = self.signal
        library = self.library
        if mask is None:
            # index at all real space pixels
            sig_shape = signal.axes_manager.navigation_shape
            mask = hs.signals.Signal1D(np.ones((sig_shape[0], sig_shape[1], 1)))

        matches = signal.map(correlate_library,
                             library=library,
                             n_largest=n_largest,
                             keys=keys,
                             mask=mask,
                             inplace=False,
                             **kwargs)
        matching_results = TemplateMatchingResults(matches)

        matching_results = transfer_navigation_axes(matching_results, signal)

        return matching_results


class ProfileIndexationGenerator():
    """Generates an indexer for data using a number of methods.

    Parameters
    ----------
    profile : ElectronDiffractionProfile
        The signal of diffraction profiles to be indexed.
    library : ProfileSimulation
        The simulated profile data.

    """

    def __init__(self, magnitudes, simulation, mapping=True):
        self.map = mapping
        self.magnitudes = magnitudes
        self.simulation = simulation

    def index_peaks(self,
                    tolerance=0.1,
                    *args,
                    **kwargs):
        """Assigns hkl indices to peaks in the diffraction profile.

        Parameters
        ----------
        tolerance : float
            The n orientations with the highest correlation values are returned.
        keys : list
            If more than one phase present in library it is recommended that
            these are submitted. This allows a mapping from the number to the
            phase.  For example, keys = ['si','ga'] will have an output with 0
            for 'si' and 1 for 'ga'.
        *args : arguments
            Arguments passed to the map() function.
        **kwargs : arguments
            Keyword arguments passed to the map() function.

        Returns
        -------
        matching_results : pyxem.signals.indexation_results.TemplateMatchingResults
            Navigation axes of the electron diffraction signal containing
            correlation results for each diffraction pattern. As an example, the
            signal in Euler reads:
                    ( Library Number , Z , X , Z , Correlation Score)

        """
        mapping = self.map
        mags = self.magnitudes
        simulation = self.simulation

        mags = np.array(mags)
        sim_mags = np.array(simulation.magnitudes)
        sim_hkls = np.array(simulation.hkls)
        indexation = np.zeros(len(mags), dtype=object)

        for i in np.arange(len(mags)):
            diff = np.absolute((sim_mags - mags.data[i]) / mags.data[i] * 100)

            hkls = sim_hkls[np.where(diff < tolerance)]
            diffs = diff[np.where(diff < tolerance)]

            indices = np.array((hkls, diffs))
            indexation[i] = np.array((mags.data[i], indices))

        return indexation


class VectorIndexationGenerator():
    """Generates an indexer for DiffractionVectors using a number of methods.

    Parameters
    ----------
    vectors : DiffractionVectors
        DiffractionVectors to be indexed.
    vector_library : DiffractionVectorLibrary
        Library of theoretical diffraction vector magnitudes and inter-vector
        angles for indexation.
    """

    def __init__(self,
                 vectors,
                 vector_library):
        self.vectors = vectors
        self.library = vector_library

    def index_vectors(self,
                      mag_threshold,
                      angle_threshold,
                      keys=[],
                      *args,
                      **kwargs):
        """Assigns hkl indices to diffraction vectors.

        Parameters
        ----------
        mag_threshold : float
            The maximum absolute error in diffraction vector magnitude, in units
            of reciprocal Angstroms, allowed for indexation.
        angle_threshold : float
            The maximum absolute error in inter-vector angle, in units of
            degrees, allowed for indexation.
        keys : list
            If more than one phase present in library it is recommended that
            these are submitted. This allows a mapping from the number to the
            phase.  For example, keys = ['si','ga'] will have an output with 0
            for 'si' and 1 for 'ga'.
        *args : arguments
            Arguments passed to the map() function.
        **kwargs : arguments
            Keyword arguments passed to the map() function.

        Returns
        -------
        indexation_results : TemplateMatchingResults
            Navigation axes of the diffraction vectors signal containing vector
            indexation results for each probe position.
        """
        vectors = self.vectors
        library = self.library

        indexation = vectors.map(match_vectors,
                                 library=library,
                                 mag_threshold=mag_threshold,
                                 angle_threshold=angle_threshold,
                                 keys=keys,
                                 inplace=False,
                                 *args,
                                 **kwargs)

        indexation_results = VectorMatchingResults(indexation)

        indexation_results = transfer_navigation_axes(indexation_results,
                                                      vectors)

        return indexation_results
