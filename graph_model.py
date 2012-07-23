import types
import ast
from asp.tree_grammar import *

parse('''
GraphUpdate(body=(GatherNode|ast.Assign)*)

GatherNode(total_var=Identifier, map=GatherMap, reduce=GatherReduce)

GatherMap(var=Identifier, body=(Accessor|ast.BinOp))

GatherReduce(var1=Identifier, var2=Identifier, body=ast.BinOp)

Accessor(names=Identifier*)

Identifier(name)

Constant(value = (types.IntType | types.LongType | types.FloatType))

''', globals(), checker='GraphModelChecker')
