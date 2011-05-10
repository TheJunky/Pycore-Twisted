'''
Created on Sep 24, 2010

@author: s
'''
import pstats

		
if __name__ == '__main__':
	filename="bot-Wed-22-Sep-2010-21-27-46.profile"
	p = pstats.Stats(filename)
	p.print_stats()
	#p.strip_dirs().sort_stats(-1).print_stats()