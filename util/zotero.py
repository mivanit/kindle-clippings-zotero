"""

https://www.zotero.org/support/dev/web_api/v3/

"""

from typing import *
import json
import sys
import os

import urllib3

from util.clippingsitem import (
	ClippingsType, ClippingsItem,
)

from util.export import (
	grab_title_author, ClippingsItem_lst_md,
)

ZOTERO_KINDLE_CACHE_FILE : str = '../zotero_kindle_cache.json'
ZOTERO_API_DATA_FILE : str = '__zotero_api__.json'




ZKCacheKey = NamedTuple('ZKCacheKey', [
	('title', str),
	('author', str),
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

def validate_zk_cache() -> bool:
	"""
	validate the zotero-kindle cache

	(create it if the file does not exist)
	"""
	if not os.path.exists(ZOTERO_KINDLE_CACHE_FILE):
		print(f'!!! WARNING !!! zotero-kindle cache file does not exist, creating it at {ZOTERO_KINDLE_CACHE_FILE}')
		with open(ZOTERO_KINDLE_CACHE_FILE, 'w') as f:
			json.dump(dict(), f)
		return False

	try:
		with open(ZOTERO_KINDLE_CACHE_FILE, 'r') as f:
			cache : dict = json.load(f)
	except (
		FileNotFoundError,
		json.decoder.JSONDecodeError,
		UnicodeDecodeError,
		ValueError,
	) as e:
		print(f'!!! ERROR !!! could not load zotero-kindle cache at {ZOTERO_KINDLE_CACHE_FILE}:\n', e, file = sys.stderr)
		return False
	
	return True

# validate the cache at runtime
validate_zk_cache()

def string_minimize(s : str) -> str:
	s_trim : str = (
		s
		.strip()
		.replace('\r', '')
		.replace('\n', ' ')
		.replace('\t', ' ')
		.replace('-', ' ')
		.replace('_', ' ')
		.replace('  ', ' ').replace('  ', ' ').replace('  ', ' ')
		.lower()
		.strip()
	)

	return (
		''.join([
			c for c in s_trim
			if c in 'abcdefghijklmnopqrstuvwxyz '
		])
	)


# def fuzzy_match_ZK_keys(a : ZKCacheKey, b : ZKCacheKey) -> bool:
# 	return string_minimize(a.title) == string_minimize(b.title)


def ZKCacheKey_from_item_raw(item_raw : dict) -> ZKCacheKey:
	"""
	extract the cache key from the response
	"""
	try:
		if ('title' in item_raw['meta']) and ('creators' in item_raw['meta']):
			return ZKCacheKey(
				title = item_raw['meta']['title'],
				author = ' '.join([
					a['firstName'] + ' ' + a['lastName']
					for a in item_raw['meta']['creators']
					if a['creatorType'] == 'author'
				]),
			)
		else:
			return ZKCacheKey(
				title = item_raw['data']['title'],
				author = '',
			)
	except KeyError:
		print('!!! ERROR !!! could not find title/author in item:\n\n', json.dumps(item_raw, indent=2), out = sys.stderr)
		return ZKCacheKey(
			title = '',
			author = '',
		)

class ZoteroManager(object):
	def __init__(self) -> None:
		self.https = urllib3.PoolManager()
		with open(ZOTERO_API_DATA_FILE, 'r') as f:
			self.api_data = json.load(f)
			self.api_key = self.api_data['key']
			self.url = self.api_data['url']
	
	def get_raw(self, item_key : ZoteroKey) -> dict:
		"""get raw item info from zotero api"""
		url = self.url + item_key
		r = self.https.request('GET', url, headers = {'Zotero-API-Key': self.api_key})
		return json.loads(r.data.decode('utf-8'))

	def get_item_fmt_ZKCacheKey(self, item_key : ZoteroKey) -> ZKCacheKey:
		"""get a `ZKCacheKey` from a zotero item key"""
		item_raw = self.get_raw(item_key)
		return ZKCacheKey_from_item_raw(item_raw)

	def search_raw(self, query : str) -> list:
		r = self.https.request(
			'GET', 
			self.url, 
			headers = {'Zotero-API-Key': self.api_key, 'q' : query},
		)
		return json.loads(r.data.decode('utf-8'))

	def search_fmt(self, query : str) -> list:
		r = self.search_raw(query)
		return [
			ZKCacheKey_from_item_raw(x)
			for x in r
		]

	def find_possible_keys(self, cache_key : ZKCacheKey) -> Dict[ZoteroKey,str]:
		"""
		find possible keys for a given cache key
		"""
		zot_keys : Dict[ZoteroKey,str] = {}
		query_results = self.search_raw(string_minimize(cache_key.title))
		for item_raw in query_results:
			key = ZoteroKey(item_raw['key'])
			if key not in zot_keys:
				zot_keys[key] = ZKCacheKey_from_item_raw(item_raw)
		return zot_keys


def zotero_upload_notes(
		zotero_manager : ZoteroManager,
		data : List[ClippingsItem], 
		title : Optional[str] = None, author : Optional[str] = None,
		export_func : Callable[[List[ClippingsItem]], str] = ClippingsItem_lst_md,
	) -> None:
	
	# get the title and author
	title,author = grab_title_author(data)

	# check a cache for what to do with notes for this book
	cache_key : ZKCacheKey = ZKCacheKey(title, author)
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
			possible_keys : Dict[ZoteroKey,str] = zotero_manager.find_possible_keys(cache_key)
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


