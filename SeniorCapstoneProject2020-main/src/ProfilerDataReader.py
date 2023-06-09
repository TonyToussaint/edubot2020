import pstats
p = pstats.Stats('profilingResults')
p.sort_stats('cumulative').print_stats('ServerAdminCog.py')