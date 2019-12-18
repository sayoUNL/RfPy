# Copyright 2019 Pascal Audet
#
# This file is part of RfPy.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""

:mod:`~rfpy` defines the following base classes:

- :class:`~rfpy.calc.classes.RFData`

The class :class:`~rfpy.calc.classes.RFData` contains attributes
and methods for the analysis of teleseismic receiver functions
from three-component seismograms.

"""

# -*- coding: utf-8 -*-
import numpy as np
from obspy.core import Trace, Stream
from rfpy.calc import options


class Meta(object):
    """
    A Meta object contains attributes associated with the metadata
    for a single receiver function analysis.

    Parameters
    ----------
    time : :class:`~obspy.core.UTCDateTime`
        Origin time of earthquake
    dep : float
        Depth of hypocenter (km)
    lon : float
        Longitude coordinate of epicenter
    lat : float
        Latitude coordinate of epicenter
    mag : float
        Magnitude of earthquake
    gac : float
        Great arc circle between station and epicenter (degrees)
    epi_dist : float
        Epicentral distance between station and epicenter (km)
    baz : float
        Back-azimuth - pointing to earthquake from station (degrees)
    az : float
        Azimuth - pointing to station from earthquake (degrees)
    ttime : float
        Predicted arrival time (sec) 
    ph : str
        Phase name 
    slow : float
        Horizontal slowness of phase 
    inc : float
        Incidence angle of phase at surface 
    vp : float
        P-wave velocity at surface (km/s)
    vs : float
        S-wave velocity at surface (km/s)
    align : str
        Alignment of coordinate system for rotation
        ('ZRT', 'LQT', or 'PVH')
    rotated : bool
        Whether or not data have been rotated to ``align``
        coordinate system

    """

    def __init__(self, sta, event, vp=6.0, vs=3.6, align='ZRT', rotated=False):

        from obspy.geodetics.base import gps2dist_azimuth as epi
        from obspy.geodetics import kilometer2degrees as k2d
        from obspy.taup import TauPyModel

        # Extract event 4D parameters
        self.time = event.origins[0].time
        self.dep = event.origins[0].depth
        self.lon = event.origins[0].longitude
        self.lat = event.origins[0].latitude

        # Magnitude
        self.mag = event.magnitudes[0].mag
        if self.mag is None:
            self.mag = -9.

        # Calculate epicentral distance
        self.epi_dist, self.az, self.baz = epi(
            self.lat, self.lon, sta.latitude, sta.longitude)
        self.epi_dist /= 1000
        self.gac = k2d(self.epi_dist)

        # Get travel time info
        tpmodel = TauPyModel()

        # Get Travel times (Careful: here dep is in meters)
        try:
            arrivals = tpmodel.get_travel_times(
                distance_in_degree=self.gac,
                source_depth_in_km=self.dep/1000.,
                phase_list=["P"])
            if len(arrivals) > 1:
                print("arrival has many entries:"+arrivals)
            arrival = arrivals[0]

            # Attributes from parameters
            self.ttime = arrival.time
            self.ph = arrival.name
            self.slow = arrival.ray_param_sec_degree/111.
            self.inc = arrival.incident_angle
        except:
            self.ttime = None
            self.ph = None
            self.slow = None
            self.inc = None

        self.vp = vp
        self.vs = vs
        self.align = align
        self.rotated = rotated


class RFData(object):
    """
    A RFData object contains Class attributes that associate
    station information with a single event (i.e., earthquake) 
    metadata, corresponding raw and rotated seismograms and 
    receiver functions.

    Note
    ----
    The object is initialized with the ``sta`` field only, and
    other attributes are added to the object as the analysis proceeds.

    Parameters
    ----------
    sta : object
        Object containing station information - from :mod:`~stdb` database.
    meta : :class:`~rfpy.calc.classes.Meta`
        Object of metadata information for single event (initially set to None)
    data : :class:`~obspy.core.Stream`
        Stream object containing the three-component seismograms (either
        un-rotated or rotated by the method `~rfpy.calc.calc.classes.rotate`)

    Examples
    --------

    Get demo RFData object

    >>> from rfpy import RFData
    >>> rfdata = RFData('demo')
    Uploading demo station data - station NY.MMPY

    Check out its attributes (initialization only stores the ``sta`` attribute)

    >>> rfdata.__dict__
    {'sta': {'station': 'MMPY',
      'network': 'NY',
      'altnet': [],
      'channel': 'HH',
      'location': ['--'],
      'latitude': 62.618919,
      'longitude': -131.262466,
      'elevation': 0.0,
      'startdate': 2013-07-01T00:00:00.000000Z,
      'enddate': 2599-12-31T23:59:59.000000Z,
      'polarity': 1.0,
      'azcorr': 0.0,
      'status': 'open'},
     'meta': None,
     'data': None}

    """

    def __init__(self, sta):

        # Load example data if initializing empty object
        if sta == 'demo' or sta == 'Demo':
            print("Uploading demo data - station NY.MMPY")
            import os
            import pickle
            sta = pickle.load(
                open(os.path.join(
                    os.path.dirname(__file__),
                    "../examples/data", "MMPY.pkl"), 'rb'))['NY.MMPY']

        # Attributes from parameters
        self.sta = sta

        # Initialize meta and data objects as None
        self.meta = None
        self.data = None

    def add_event(self, event):
        """
        Adds event metadata to RFData object, including travel time info 
        of P wave. 

        Parameters
        ----------
        event : :class:`~obspy.core.event`
            Event XML object

        Returns
        -------
        accept : bool
            Whether or not the event is accepted for analysis. 
            This variable is used to check whether or not the analysis should 
            continue.

        Examples
        --------

        Get demo event info

        >>> from rfpy import RFData
        >>> rfdata = RFData('demo')
        Uploading demo data - station NY.MMPY
        >>> rfdata.add_event('demo')
        2015-02-02T08:25:51.300000Z |  -1.583, +145.315 | 6.0 MW
        True

        Print content of object meta data

        >>> rfdata.meta.__dict__
        {'time': 2015-02-02T08:25:51.300000Z,
         'dep': 34000.0,
         'lon': 145.3149,
         'lat': -1.5827,
         'mag': 6.0,
         'epi_dist': 9823.972036840038,
         'az': 27.282925592822235,
         'baz': 263.555086495223,
         'gac': 88.34910308671685,
         'ttime': 768.19792906912335,
         'ph': 'P',
         'slow': 0.042684575337198057,
         'inc': 14.839216790091562,
         'vp': 6.0,
         'vs': 3.6,
         'align': 'ZRT',
         'rotated': False}

        Once the meta data is loaded, it's possible to edit attributes,
        although we recommend only editing `vp`, `vs` or `align`, and
        avoid editing any of the station-event attributes

        >>> rfdata.meta.vp = 5.5
        >>> rfdata.meta.vs = 3.3
        >>> rfdata.meta.vp, rfdata.meta.vs
        (5.5, 3.3)

        """
        from obspy.geodetics.base import gps2dist_azimuth as epi
        from obspy.geodetics import kilometer2degrees as k2d
        from obspy.taup import TauPyModel
        from obspy.core.event.event import Event

        if event == 'demo' or event == 'Demo':
            from obspy.clients.fdsn import Client
            from obspy.core import UTCDateTime
            client = Client()
            # Get catalogue using deployment start and end
            event = client.get_events(
                starttime=UTCDateTime('2015-02-02T08:00:00'),
                endtime=UTCDateTime('2015-02-02T09:00:00'),
                minmagnitude=6.0,
                maxmagnitude=7.0)[0]
            print(event.short_str())

        if not isinstance(event, Event):
            raise(Exception("Event has incorrect type"))

        # Store as object attributes
        self.meta = Meta(sta=self.sta, event=event)
        if self.meta.ttime is None:
            self.meta.accept = False
            return False
        else:
            self.meta.accept = True
            return True


    def add_NEZ(self, stream):
        """
        Adds stream as object attribute

        Parameters
        ----------
        stream : :class:`~obspy.core.Stream`
            Stream container for NEZ seismograms

        Attribute
        ---------
        zne_data : :class:`~obspy.core.Stream`
            Stream container for NEZ seismograms

        Examples
        --------

        Get demo Stream data

        >>> from rfpy import RFData
        >>> rfdata = RFData('demo')
        Uploading demo data - station NY.MMPY
        >>> rfdata.add_NEZ('demo')
        3 Trace(s) in Stream:
        NY.MMPY..HHN | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHE | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHZ | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples

        """

        # Load demo data
        if stream == 'demo' or stream == 'Demo':
            import os
            from obspy.core import read
            stream = read(os.path.join(os.path.dirname(__file__),
                                       "../examples/data", "2015*.mseed"))
            print(stream)

        if not self.meta.accept:
            return

        if not isinstance(stream, Stream):
            raise(Exception("Event has incorrect type"))

        try:
            trE = stream.select(component='E')[0]
            trN = stream.select(component='N')[0]
            trZ = stream.select(component='Z')[0]
            self.data = stream
        except:
            raise(Exception("Error: Not all channels are available"))


    def download_NEZ(self, client, ndval=np.nan, new_sr=5., dts=120.):
        """
        Downloads seismograms based on event origin time and
        P phase arrival.

        Parameters
        ----------
        client : :class:`~obspy.client.fdsn.Client`
            Client object
        ndval : float
            Fill in value for missing data
        new_sr : float
            New sampling rate (Hz)
        dts : float
            Time duration (sec)

        Attributes
        ----------

        data : :class:`~obspy.core.Stream`
            Stream containing :class:`~obspy.core.Trace` objects

        """

        if self.meta is None:
            raise(Exception("Requires event data as attribute - aborting"))

        if not self.meta.accept:
            return

        # Define start and end times for requests
        tstart = self.meta.time + self.meta.ttime - dts
        tend = self.meta.time + self.meta.ttime + dts

        # Get waveforms
        print("* Requesting Waveforms: ")
        print("*    Startime: " + tstart.strftime("%Y-%m-%d %H:%M:%S"))
        print("*    Endtime:  " + tend.strftime("%Y-%m-%d %H:%M:%S"))

        err, trN, trE, trZ = options.download_data(
            client=client, sta=self.sta, start=tstart, end=tend,
            stdata=self.sta.station, ndval=ndval, new_sr=new_sr)

        # Store as attributes with traces in dictionay
        self.err = err
        self.data = Stream(traces=[trZ, trN, trE])

    def rotate(self, vp=None, vs=None, align=None):
        """
        Rotates 3-component seismograms from vertical (Z),
        east (E) and north (N) to longitudinal (L), 
        radial (Q) and tangential (T) components of motion.
        Note that the method 'rotate' from ``obspy.core.stream.Stream``
        is used for the rotation ``'ZNE->ZRT'`` and ``'ZNE->LQT'``.
        Rotation ``'ZNE->PVH'`` is implemented separately here 
        due to different conventions.

        Parameters
        ----------
        vp : float
            P-wave velocity at surface (km/s)
        vs : float
            S-wave velocity at surface (km/s)
        align : str
            Alignment of coordinate system for rotation
            ('ZRT', 'LQT', or 'PVH')


        Examples
        --------
        Continuing with the demo

        >>> from rfpy import RFData
        >>> rfdata = RFData('demo')
        Uploading demo data - station NY.MMPY
        >>> rfdata.add_event('demo')
        2015-02-02T08:25:51.300000Z |  -1.583, +145.315 | 6.0 MW
        >>> rfdata.add_NEZ('demo')
        3 Trace(s) in Stream:
        NY.MMPY..HHN | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHE | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHZ | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        >>> rfdata.rotate()        
        >>> rfdata.meta.rotated
        True
        >>> rfdata.rotate(align='PVH')
        ...
        Exception: Data are already rotated - aborting

        Re-do previous example with different alignment

        >>> from rfpy import RFData
        >>> rfdata = RFData('demo')
        Uploading demo data - station NY.MMPY
        >>> rfdata.add_event('demo')
        2015-02-02T08:25:51.300000Z |  -1.583, +145.315 | 6.0 MW
        >>> rfdata.add_NEZ('demo')
        3 Trace(s) in Stream:
        NY.MMPY..HHN | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHE | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHZ | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        >>> rfdata.rotate(align='PVH')
        >>> rfdata.meta.align
        'PVH'

        """

        if not self.meta.accept:
            return
        if self.err:
            return

        if self.meta.rotated:
            raise(Exception("Data are already rotated - aborting"))

        if not align:
            align = self.meta.align

        if not self.data:
            raise(Exception("ZNE data are not available - aborting"))

        if align == 'ZRT':
            self.data.rotate('NE->RT', 
                back_azimuth=self.meta.baz)
            self.meta.align = align
            self.meta.rotated = True

        elif align == 'LQT':
            self.data.rotate('ZNE->LQT', 
                back_azimuth=self.meta.baz,
                inclination=self.meta.inc)
            for tr in self.data:
                if tr.stats.channel.endswith('Q'):
                    tr.data = -tr.data
            self.meta.align = align
            self.meta.rotated = True

        elif align == 'PVH':

            # Use default values
            if not vp or not vs:
                vp = self.meta.vp
                vs = self.meta.vs

            # First rotate to ZRT
            self.data.rotate('NE->RT', back_azimuth=self.meta.baz)

            # Copy traces
            trP = self.data.select(component='Z')[0].copy()
            trV = self.data.select(component='R')[0].copy()
            trH = self.data.select(component='T')[0].copy()

            # Vertical slownesses
            # P vertical slowness
            qp = np.sqrt(1./vp/vp-self.meta.slow*self.meta.slow)
            # S vertical slowness
            qs = np.sqrt(1./vs/vs-self.meta.slow*self.meta.slow)

            # Elements of rotation matrix
            m11 = self.meta.slow*vs*vs/vp
            m12 = -(1.-2.*vs*vs*self.meta.slow*self.meta.slow)/(2.*vp*qp)
            m21 = (1.-2.*vs*vs*self.meta.slow*self.meta.slow)/(2.*vs*qs)
            m22 = self.meta.slow*vs

            # Rotation matrix
            rot = np.array([[-m11, m12], [-m21, m22]])

            # Vector of Radial and Vertical
            r_z = np.array([trV.data, trH.data])

            # Rotation
            vec = np.dot(rot, r_z)

            # Extract P and SV, SH components
            trP.data = vec[0, :]
            trV.data = vec[1, :]
            trH.data = -trH.data/2.

            # Update stats of streams
            trP.stats.channel = trP.stats.channel[:-1] + 'P'
            trV.stats.channel = trV.stats.channel[:-1] + 'V'
            trH.stats.channel = trH.stats.channel[:-1] + 'H'

            # Over-write data attribute
            self.data = Stream(traces=[trP, trV, trH])
            self.meta.align = align
            self.meta.rotated = True

        else:
            raise(Exception("incorrect 'align' argument"))

    def calc_snr(self, dt=30., fmin=0.1, fmax=1.):
        """
        Calculates signal-to-noise ratio on either Z, L or P component

        Parameters
        ----------
        dt : float
            Duration (sec)

        Attributes
        ----------
        snr : float
            Signal-to-noise ratio  (dB)

        Examples
        --------
        Continuing with the demo

        >>> from rfpy import RFData
        >>> rfdata = RFData('demo')
        Uploading demo data - station NY.MMPY
        >>> rfdata.add_event('demo')
        2015-02-02T08:25:51.300000Z |  -1.583, +145.315 | 6.0 MW
        >>> rfdata.add_NEZ('demo')
        3 Trace(s) in Stream:
        NY.MMPY..HHN | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHE | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHZ | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        >>> rfdata.calc_snr()
        >>> rfdata.meta.snr
        XXXX

        """

        if not self.meta.accept:
            return
        if self.err:
            return

        if not self.data:
            raise(Exception("ZNE data are not available - aborting"))

        t1 = self.meta.time + self.meta.ttime - 5.

        comp = self.meta.align[0]

        # Copy trace to signal and noise traces
        trSig = self.data.select(component=comp)[0].copy()
        trNze = self.data.select(component=comp)[0].copy()

        # Filter between 0.1 and 1.0 (dominant P wave frequencies)
        trSig.filter('bandpass', freqmin=fmin, freqmax=fmax,
                     corners=2, zerophase=True)
        trNze.filter('bandpass', freqmin=fmin, freqmax=fmax,
                     corners=2, zerophase=True)

        # Trim twin seconds around P-wave arrival
        trSig.trim(t1, t1 + dt)
        trNze.trim(t1 - dt, t1)

        # Calculate root mean square (RMS)
        srms = np.sqrt(np.mean(np.square(trSig.data)))
        nrms = np.sqrt(np.mean(np.square(trNze.data)))

        # Calculate signal/noise ratio in dB
        self.meta.snr = 10*np.log10(srms*srms/nrms/nrms)

    def deconvolve(self, twin=30., align=None):
        """

        Parameters
        ----------

        """

        if not self.meta.accept:
            return
        if self.err:
            return

        def _taper(nt, ns):
            tap = np.ones(nt)
            win = np.hanning(2*ns)
            tap[0:ns] = win[0:ns]
            tap[nt-ns:nt] = win[ns:2*ns]
            return tap

        if not self.meta.rotated:
            print("Warning: Data have not been rotated yet - rotating now")
            self.rotate(align=align)

        if not hasattr(self.meta, 'snr'):
            print("Warning: snr has not been calculated - calculating now")
            self.calc_snr()         

        if hasattr(self, 'rf'):
            print("Warning: Data have been deconvolved already")

        cL = self.meta.align[0]
        cQ = self.meta.align[1]
        cT = self.meta.align[2]

        # Define source and noise
        trL = self.data.select(component=cL)[0].copy()
        trQ = self.data.select(component=cQ)[0].copy()
        trT = self.data.select(component=cT)[0].copy()
        trS = self.data.select(component=cL)[0].copy()  # Source
        trNl = self.data.select(component=cL)[0].copy()  # Noise on L
        trNq = self.data.select(component=cQ)[0].copy()  # Noise on Q

        # trim traces 115 sec in each direction
        trL.trim(self.meta.time+self.meta.ttime-5.,
                 self.meta.time+self.meta.ttime+110.)
        trQ.trim(self.meta.time+self.meta.ttime-5.,
                 self.meta.time+self.meta.ttime+110.)
        trT.trim(self.meta.time+self.meta.ttime-5.,
                 self.meta.time+self.meta.ttime+110.)
        trS.trim(self.meta.time+self.meta.ttime-5.,
                 self.meta.time+self.meta.ttime+110.)
        trNl.trim(self.meta.time+self.meta.ttime-120.,
                  self.meta.time+self.meta.ttime-5.)
        trNq.trim(self.meta.time+self.meta.ttime-120.,
                  self.meta.time+self.meta.ttime-5.)

        # Taper trS
        window = np.zeros(len(trS.data))
        tap = _taper(int(twin/trS.stats.delta), int(2./trS.stats.delta))
        window[0:int(twin/trS.stats.delta)] = tap
        trS.data *= window

        # Taper other traces
        window = np.zeros(len(trL.data))
        tap = _taper(len(trL.data), int(2./trL.stats.delta))
        window[0:len(trL.data)] = tap

        # Some checks
        lwin = len(window)
        if not (lwin == len(trL.data) and lwin == len(trQ.data)
                and lwin == len(trT.data) and lwin == len(trNl.data)
                and lwin == len(trNq.data)):
            print('problem with lwin')
            self.rf = Stream(traces=[Trace(), Trace(), Trace()])

        # Apply taper
        trL.data *= window
        trQ.data *= window
        trT.data *= window
        trNl.data *= window
        trNq.data *= window

        # Fourier transform
        Fl = np.fft.fft(trL.data)
        Fq = np.fft.fft(trQ.data)
        Ft = np.fft.fft(trT.data)
        Fs = np.fft.fft(trS.data)
        Fnl = np.fft.fft(trNl.data)
        Fnq = np.fft.fft(trNq.data)

        # Auto and cross spectra
        Sl = Fl*np.conjugate(Fs)
        Sq = Fq*np.conjugate(Fs)
        St = Ft*np.conjugate(Fs)
        Ss = Fs*np.conjugate(Fs)
        Snl = Fnl*np.conjugate(Fnl)
        Snq = Fnq*np.conjugate(Fnq)
        Snlq = Fnq*np.conjugate(Fnl)

        # Denominator
        Sdenom = 0.25*(Snl+Snq)+0.5*np.abs(Snlq)

        # Copy traces
        rfL = trL.copy()
        rfQ = trQ.copy()
        rfT = trT.copy()

        # Spectral division and inverse transform
        rfL.data = np.real(np.fft.ifft(Sl/(Ss+Sdenom)))
        rfQ.data = np.real(np.fft.ifft(Sq/(Ss+Sdenom))/np.amax(rfL.data))
        rfT.data = np.real(np.fft.ifft(St/(Ss+Sdenom))/np.amax(rfL.data))

        # Update stats of streams
        rfL.stats.channel = 'RF' + self.meta.align[0]
        rfQ.stats.channel = 'RF' + self.meta.align[1]
        rfT.stats.channel = 'RF' + self.meta.align[2]

        self.rf = Stream(traces=[rfL, rfQ, rfT])

    def to_stream(self):
        """
        Method to move back from RFData object to Stream object.
        This allows easier manipulation of the stream object
        for post-processing.

        Example
        -------
        Complete demo example and convert object to stream

        >>> from rfpy import RFData 
        >>> rfdata = RFData('demo')
        Uploading demo data - station NY.MMPY
        >>> rfdata.add_event('demo')
        2015-02-02T08:25:51.300000Z |  -1.583, +145.315 | 6.0 MW
        >>> rfdata.add_NEZ('demo')
        3 Trace(s) in Stream:
        NY.MMPY..HHN | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHE | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples
        NY.MMPY..HHZ | 2015-02-02T08:36:39.500000Z - 2015-02-02T08:40:39.300000Z | 5.0 Hz, 1200 samples

        Process the data for receiver functions using default options.
        Note the new channel names in the final ``stream`` object

        >>> rfdata.deconvolve()
        Warning: Data have not been rotated yet - rotating now
        >>> rfstream = rfdata.to_stream()
        Warning: snr has not been calculated - calculating now
        >>> rfstream
        3 Trace(s) in Stream:
        NY.MMPY..RFZ | 2015-02-02T08:38:34.500000Z - 2015-02-02T08:40:29.500000Z | 5.0 Hz, 576 samples
        NY.MMPY..RFR | 2015-02-02T08:38:34.500000Z - 2015-02-02T08:40:29.500000Z | 5.0 Hz, 576 samples
        NY.MMPY..RFT | 2015-02-02T08:38:34.500000Z - 2015-02-02T08:40:29.500000Z | 5.0 Hz, 576 samples

        Check out new stats in traces

        >>> rfstream[0].stats.snr
        XXXX
        >>> rfstream[0].stats.slow
        YYYY
        >>> rfstream[0].stats.baz
        ZZZZ
        >>> rfstream[0].stats.is_rf
        True

        """

        if not self.meta.accept:
            return 
        if self.err:
            return 

        def _add_rfstats(trace):
            trace.stats.snr = self.meta.snr
            trace.stats.slow = self.meta.slow
            trace.stats.baz = self.meta.baz
            trace.stats.is_rf = True
            return trace

        if not hasattr(self, 'rf'):
            raise(Exception("Warning: Receiver functions are not available"))
        if not hasattr(self.meta, 'snr'):
            print("Warning: snr has not been calculated - calculating now")
            self.calc_snr()

        stream = self.rf
        for tr in stream:
            tr = _add_rfstats(tr)

        return stream

    def save(self, file):
        """
        Saves Split object to file

        Parameters
        ----------
        file : str
            File name for split object

        """

        import pickle
        output = open(file, 'wb')
        pickle.dump(self, output)
        output.close()
