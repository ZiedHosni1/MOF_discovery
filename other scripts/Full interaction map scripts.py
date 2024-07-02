from ccdc import io
from ccdc.interaction import InteractionMapAnalysis
#then load a crystal structure (from this example they use paracetamol (HXACAN), so we can change it to others.
csd = io.EntryReader('csd')
paracetamol = csd.crystal('HXACAN')
#instantiate a ccdc.interaction.InteractionMapAnalysis.SmallMoleculeSettings to control the analysis and do the setting of probe
settings = InteractionMapAnalysis.SmallMoleculeSettings()
print('\n'.join(settings.probe_names))
Uncharged NH Nitrogen
Carbonyl Oxygen
Aromatic CH Carbon
#Then we are ready to calculate the intaraction maps:
analyser = InteractionMapAnalysis(settings=settings)
results = analyser.analyse_small_molecule(paracetamol.molecule)
#The calculated grid of the analysis may be accessed by dictionary-like methods, keyed by the probe names of the analysis: (I don't understand this step...)
for k in sorted(results.keys()):
    grid = results[k]
    print('%s: %.2f, %.2f' % (k, grid.extrema[0], grid.extrema[1]))
Aromatic_CH_Carbon: 0.00, 4.03
Carbonyl_Oxygen: 0.00, 38.71
Uncharged_NH_Nitrogen: 0.00, 10.44
#then do the hotspot detection
hs = results.hotspots('Carbonyl_Oxygen')
print(len(hs))
11
print(hs[0])
Hotspot(Coordinates(x=4.408, y=-0.035, z=2.151), 38.71)
#A similar set of results may be obtained by directly inspecting the grids (what does the number 11 or 19 mean?)
co_grid = results['Carbonyl_Oxygen']
islands = co_grid.islands(2.0)
print(len(islands))
19
#We can check that the hottest hotspot does indeed correspond with the island containing the highest value:
l = list(sorted(islands, key=lambda x: x.extrema[1], reverse=True))
origin, far_corner = l[0].bounding_box
assert all(origin[i] <= hs[0][0][i] <= far_corner[i] for i in range(3))
#define of hotspots setting (we only need default settings)
settings.detect_hotspots
True
settings.hotspots_refine
False
settings.hotspots_min_value
1.01
settings.hotspots_ncycles
1
#We can check that the analysis worked correctly and extract more details of its operation by inspecting the error and log files:
print(results.error_file('Uncharged NH Nitrogen'))
print(results.log_file('Aromatic CH Carbon'))
#finished in the instruction there are also some scripts about the surface maps, but maybe we don;t need that.

