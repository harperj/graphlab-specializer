import types
import ast
from asp.tree_grammar import *

parse('''
Graph(vertex=VertexType, edge=EdgeType)

VertexType(members=TypeDecl*)

EdgeType(members=TypeDecl*)

TypeDecl(name=types.StringType, type=types.TypeType, initialValue=Value)

Value = types.NoneType
      | types.IntType
      | types.DoubleType
      | types.StringType

''', globals(), checker='GraphModelChecker')
