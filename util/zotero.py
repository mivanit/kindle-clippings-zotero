from typing import *
import json

from util.clippingsitem import (
	ClippingsType, ClippingsItem,
)

from util.export import (
	grab_title_author, ClippingsItem_lst_md,
)

ZOTERO_KINDLE_CACHE_FILE : str = '../zotero_kindle_cache.json'

ZKCacheKey = NamedTuple('ZKCacheKey', [
	('author', str),
	('title', str),
])

ZoteroKey = str


# if None, then not in cache
# if -1, then ignore
# if 0, then prompt
# if it is a string, then that string is the zotero key
ZKCacheValue = Union[None, Literal[-1, 0], str]

ZK_CACHE_ACTIONS : Dict[str,str] = {
	'i': 'ignore',
	'p': 'postpone',
	'a': 'add',
}

def ZKCacheKey_fromstr(s : str) -> ZKCacheKey:
	"""convert string to `ZKCacheKey`"""
	return tuple(x.strip() for x in s.split('|'))

def ZKCacheKey_tostr(key : ZKCacheKey) -> str:
	"""convert `ZKCacheKey` to string"""
	return ' | '.join(key)

def zk_cache_get(key : ZKCacheKey) -> Optional[str]:
	"""get a value from the zotero kindle cache"""
	with open(ZOTERO_KINDLE_CACHE_FILE, 'r') as f:
		cache : dict = json.load(f)
	return cache.get(ZKCacheKey_tostr(key), None)

def zk_cache_set(key : ZKCacheKey, value : str) -> None:
	"""set a value in the zotero kindle cache"""
	with open(ZOTERO_KINDLE_CACHE_FILE, 'r') as f:
		cache : dict = json.load(f)
	cache[ZKCacheKey_tostr(key)] = value
	with open(ZOTERO_KINDLE_CACHE_FILE, 'w') as f:
		json.dump(cache, f)


def zotero_find_possible_keys(cache_key : ZKCacheKey) -> Dict[ZoteroKey,str]:
	raise NotImplementedError('not implemented')


def zotero_upload_notes(
		data : List[ClippingsItem], 
		title : Optional[str] = None, author : Optional[str] = None,
		export_func : Callable[[List[ClippingsItem]], str] = ClippingsItem_lst_md,
	) -> None:
	
	# get the title and author
	title,author = grab_title_author(data)

	# check a cache for what to do with notes for this book
	cache_key : ZKCacheKey = ZKCacheKey(author, title)
	cache_value : Optional[str] = zk_cache_get(cache_key)

	# if bibtex key is unknown, or key is postponed, ask user what to do
	if (cache_value is None) or (cache_value == 0):
		print(f'  unknown bibtex key for "{title}" by "{author}", please select action from {ZK_CACHE_ACTIONS}:')
		action : str = input('  > ')
		if action in ZK_CACHE_ACTIONS:
			action = ZK_CACHE_ACTIONS[action]

		# if ignore, then save this to cache
		if action == 'ignore':
			zk_cache_set(cache_key, -1)
		# if postpone, then save this to cache
		elif action == 'postpone':
			zk_cache_set(cache_key, 0)
		# if add, then:
		elif action == 'add':
			# look in Zotero for items with matching author and title
			possible_keys : Dict[ZoteroKey,str] = zotero_find_possible_keys(cache_key)
			print('# possible Zotero keys:')
			for key,info in possible_keys.items():
				print(f'\t{key} : {info}')

			# ask the user which item to pair with
			print(f'# please select Zotero item to pair with "{title}" by "{author}", or selection action from {ZK_CACHE_ACTIONS} by prefixing with "!":')
			action_pair : str = input('  > ')

			# if command given, process
			if action_pair.startswith('!'):
				# match command to action
				if action_pair[1:] in ZK_CACHE_ACTIONS:
					action_pair = ZK_CACHE_ACTIONS[action_pair[1:]]
				# if ignore, then save this to cache
				if action == 'ignore':
					zk_cache_set(cache_key, -1)
				# if postpone, then save this to cache
				elif action == 'postpone':
					zk_cache_set(cache_key, 0)
				# if add, then complain and then postpone
				elif action == 'add':
					print('WARNING: we have already shown all possible Zotero items, and the user has not selected an action. postponing.')
					zk_cache_set(cache_key, 0)
				else:
					raise KeyError(f'unknown action "{action_pair}"')
			
			else:
				# if not command, then assume it is a key
				zotero_key : ZoteroKey = action_pair
				
				if zotero_key in possible_keys:
					# if key is in possible keys, then save this to cache
					zk_cache_set(cache_key, zotero_key)
					# and then upload the notes
					notes_export : str = export_func(data)
					raise NotImplementedError('uploading of notes given zotero key not implemented')
				else:
					# if key is not in possible keys, then complain and then postpone
					print(f'WARNING: "{zotero_key}" is not a possible Zotero key for "{title}" by "{author}". postponing.')
					zk_cache_set(cache_key, 0)

		else:
			raise KeyError(f'unknown action "{action}"')	


