import types
import ast
from asp.tree_grammar import *

parse('''
VertexType(members=TypeDecl*)

EdgeType(members=TypeDecl*)

TypeDecl(name=types.StringType, type=types.StringType, 
	initialValue=(types.IntType|types.StringType|types.FloatType))

''', globals(), checker='GraphModelChecker')
