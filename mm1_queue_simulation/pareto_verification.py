import random
import math

print sum((8 - 4 * math.sqrt(2)) * pow(1 - random.random(), -1.0 / (1 + math.sqrt(2))) 
for _ in xrange(int(10e6))) / int(10e6)
print sum((4 - 2 * math.sqrt(2)) * pow(1 - random.random(), -1.0 / (1 + math.sqrt(2))) for _ in xrange(int(10e6))) / int(10e6)
