'''
Created on Sep 24, 2010

@author: s
'''
import pstats

		
if __name__ == '__main__':
	filename="bots_python/bot-Tue-31-May-2011-18-13-22.profile"
	p = pstats.Stats(filename)
	p.sort_stats('cumulative')
	p.print_stats(.1)
	#p.strip_dirs().sort_stats(-1).print_stats()