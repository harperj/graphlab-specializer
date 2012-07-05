import types
import ast
from asp.tree_grammar import *

parse('''
GraphUpdate(body=VarDecl*)

VarDecl(name=Identifier, type=types.StringType, initialValue=Constant)

InEdgeIter(body=AccumOp*)

AccumOp(left=Identifier. op=(ast.Add|ast.Mul)

Identifier(name)

Constant(value = (types.IntType | types.LongType | types.FloatType))

''', globals(), checker='GraphModelChecker')
