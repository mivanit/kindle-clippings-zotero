from typing import *
import inspect


def isinstance_namedtuple(x):
	"""checks if `x` is a `namedtuple`"""
	t = type(x)
	b = t.__bases__
	if len(b) != 1 or b[0] != tuple:
		return False
	f = getattr(t, '_fields', None)
	if not isinstance(f, tuple):
		return False
	return all(type(n)==str for n in f)


SERIALIZER_SPECIAL_KEYS : List[str] = [
	'__name__',
	'__doc__',
	'__module__',
	'__class__',
]

SERIALIZER_SPECIAL_FUNCS : Dict[str,Callable] = {
	'str' : str,
	'type' : lambda x : type(x).__name__,
	'repr' : lambda x : repr(x),
	'code' : lambda x : inspect.getsource(x),
	'sourcefile' : lambda x : inspect.getsourcefile(x),
}

def arbit_json_serialize(obj : Any, depth : int = -1 ) -> Any:
	
	try:
		# if None, return None
		if obj is None:
			return None
		
		# if primitive type, just add it
		if isinstance(obj, (bool,int,float,str)):
			return obj

		# if max depth is reached, return the object as a string and dont recurse
		if depth == 0:
			return str(obj)
		
		if isinstance(obj, dict):
			# if dict, recurse
			out_dict : Dict[str,Any] = dict()
			for k,v in obj.items():
				out_dict[str(k)] = arbit_json_serialize(v, depth-1)
			return out_dict

		elif isinstance_namedtuple(obj):
			# if namedtuple, treat as dict
			return arbit_json_serialize(dict(obj._asdict()))

		elif isinstance(obj, (set,list,tuple)):
			# if iterable, recurse
			return [
				arbit_json_serialize(x, depth-1) for x in obj
			]

		else:
			# if not basic type, serialize it
			return {
				**{
					k : str(getattr(obj, k, None))
					for k in SERIALIZER_SPECIAL_KEYS
				},
				**{
					k : str(f(obj))
					for k,f in SERIALIZER_SPECIAL_FUNCS.items()
				},
			}
	except Exception as e:
		# print(f'error serializing {obj}')
		return str(obj)