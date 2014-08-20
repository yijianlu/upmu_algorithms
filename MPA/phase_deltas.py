__author__ = 'immesys'

import numpy as np
import qdf
from twisted.internet import defer
import itertools

class DistillateDriver(qdf.QuasarDistillate):

    def setup(self, opts):
        """
        This constructs your distillate algorithm
        """
        #This is the first level in the distillate tree
        self.set_author("MPA")

        #This is the second level. This name should be unique for every algorithm you write
        self.set_name("PhaseDeltas")

        #This is just a variable custom to this distillate, it is not part of the framework
        targets = [
            ("switch_a6_L1", "adf13e17-44b7-4ef6-ae3f-fde8a9152ab7", 0),
            ("switch_a6_L2", "4f56a8f1-f3ca-4684-930e-1b4d9955f72c", 0),
            ("switch_a6_L3", "2c07ccef-20c5-4971-87cf-2c187ce5f722", 0),
            ("soda_b_L1", "98435be7-7341-4661-b104-16af89e0333d", 0),
            ("soda_a_L1", "4d6525a9-b8ad-48a4-ae98-b171562cf817", 0),
        ]

        for stream in targets:
            self.use_stream(stream[0], stream[1])

        self.pairs = list(itertools.combinations(targets, 2))
        for p in self.pairs:
            streamname = p[0][0] + "-" + p[1][0]
            self.add_stream(streamname, unit="degrees")

        #If this is incremented, it is assumed that the whole distillate is invalidated, and it
        #will be deleted and discarded. In addition all 'persist' data will be removed
        self.set_version(4)

    @defer.inlineCallbacks
    def compute(self):
        """
        This is called to compute your algorithm.

        This example generates the difference between two streams
        """

        for pair in self.pairs:
            streamname = pair[0][0] + "-" + pair[1][0]

            changed_ranges = yield self.get_changed_ranges([pair[0][0], pair[1][0]], "auto")
            print "got changed ranges"
            for start, end in changed_ranges:
                print ("Computing for pair %s/%s from time %d to %d" % (pair[0][0],pair[1][0], start, end))
                #delete whatever data we had generated for that range
                yield self.stream_delete_range(streamname, start, end)

                current = start
                while current < end:
                    #we only want to do 15 minutes at a time
                    window_end = current + 15 * qdf.MINUTE
                    if window_end > end:
                        window_end = end
                    _, vals_a = yield self.stream_get(pair[0][0], current, window_end)
                    if len(vals_a) == 0:
                        current += 15*qdf.MINUTE
                        continue
                    _, vals_b = yield self.stream_get(pair[1][0], current, window_end)
                    if len(vals_b) == 0:
                        current += 15*qdf.MINUTE
                        continue
                    
                    delta_values = []

                    idx1 = 0
                    idx2 = 0
                    while idx1 < len(vals_a) and idx2 < len(vals_b):
                        if vals_a[idx1].time < vals_b[idx2].time:
                            idx1 += 1
                            continue
                        if vals_a[idx1].time > vals_b[idx2].time:
                            idx2 += 1
                            continue
                        delta = vals_a[idx1].value - vals_b[idx2].value + pair[0][2] + pair[1][2]
                        if delta < -180:
                            delta += 360
                        elif delta >= 180:
                            delta -= 360

                        delta_values.append((vals_a[idx1].time, delta))
                        idx1 += 1
                        idx2 += 1

                    print "Inserting values: ", len(delta_values)
                    yield self.stream_insert_multiple(streamname, delta_values)

                    current += 15 * qdf.MINUTE

        # we don't need to use any persistence, because the latest versions we used are stored in the metadata

qdf.register(DistillateDriver())
qdf.begin()
