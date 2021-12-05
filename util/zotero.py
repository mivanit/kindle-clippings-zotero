"""

https://www.zotero.org/support/dev/web_api/v3/

"""

from typing import *
import json
import sys
import os
import pyzotero

import urllib3
from pyzotero import zotero
from pyzotero.zotero_errors import PyZoteroError

from util.clippingsitem import (
	ClippingsType, ClippingsItem,
)

from util.export import (
	grab_title_author, ClippingsItem_lst_md,ClippingsItem_to_filename,
	DATA_EXPORT_PATH,
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
		title : str = '<none>'
		author : str = '<none>'
		
		# getting title
		if ('title' in item_raw['meta']):
			title = item_raw['meta']['title'],
		elif ('title' in item_raw['data']):
			title = item_raw['data']['title'],

		# getting author
		if ('creatorSummary' in item_raw['meta']):
			author = item_raw['meta']['creatorSummary']
		elif ('creators' in item_raw['data']):
			author = ' '.join([
				a['firstName'] + ' ' + a['lastName']
				for a in item_raw['meta']['creators']
				if a['creatorType'] == 'author'
			])
		
		if isinstance(title, tuple):
			title = title[0]

		return ZKCacheKey(
			title = title,
			author = author,
		)
		
	except KeyError:
		print('!!! ERROR !!! could not find title/author in item:\n\n', json.dumps(item_raw, indent=2), file = sys.stderr)
		return ZKCacheKey(
			title = title,
			author = author,
		)

class ZoteroManager(object):
	def __init__(self) -> None:
		self.https = urllib3.PoolManager()
		with open(ZOTERO_API_DATA_FILE, 'r') as f:
			self.api_data : dict = json.load(f)
			self.api_key : str = self.api_data['key']
			self.url : str = self.api_data['url']
			self.pyzot : zotero.Zotero = zotero.Zotero(
				self.get_library_id(),
				self.get_library_type(),
				self.api_key,
			)
	
	def get_raw(self, item_key : ZoteroKey, top_only : bool = True) -> dict:
		"""get raw item info from zotero api"""
		
		# get the item
		r = self.https.request(
			'GET', self.url + ('/top' if top_only else ''),
			headers = {
				'Zotero-API-Key' : self.api_key,
				'itemKey' : item_key,
			},
		)

		data_str : str = r.data.decode('utf-8')
		if data_str.lower() == 'not found':
			raise KeyError(f'item {item_key} not found')
		data_lst : list = json.loads(data_str)

		# get the item with the correct key
		for item_raw in data_lst:
			if item_raw['data']['key'] == item_key:
				return item_raw
		
		# raise error if not found
		raise KeyError(f'item {item_key} returned results, but key not found in them:\n\n\n{data_lst}')

	def get_library_type(self) -> str:
		if 'users' in self.url:
			return 'user'
		elif 'groups' in self.url:
			return 'group'
		else:
			raise ValueError(f'could not determine library type from {self.url=}')
	
	def get_library_id(self) -> str:
		if 'users' in self.url:
			# find 'users' in the url and get the ID after the next slash
			idx : int = self.url.index('users')
			return self.url[idx+6:].split('/')[0]
		elif 'groups' in self.url:
			# find 'groups' in the url and get the ID after the next slash
			idx : int = self.url.index('groups')
			return self.url[idx+7:].split('/')[0]
		else:
			raise ValueError(f'could not determine library id from {self.url=}')

	def get_item_fmt_ZKCacheKey(self, item_key : ZoteroKey) -> ZKCacheKey:
		"""get a `ZKCacheKey` from a zotero item key"""
		item_raw = self.get_raw(item_key)
		return ZKCacheKey_from_item_raw(item_raw)

	def search_raw(self, query : str, top_only : bool = True) -> list:
		r = self.https.request(
			'GET', 
			self.url + ('/top' if top_only else ''), 
			headers = {'Zotero-API-Key': self.api_key, 'q' : query},
		)
		return json.loads(r.data.decode('utf-8'))

	def search_title_exact(self, title : str, top_only : bool = True) -> Optional[dict]:
		r = self.https.request(
			'GET', 
			self.url + ('/top' if top_only else ''), 
			headers = {'Zotero-API-Key': self.api_key, 'q' : title},
		)
		res = json.loads(r.data.decode('utf-8'))
		# print(json.dumps(res, indent=2))
		for item in res:
			if ('title' in item['data']) and (item['data']['title'] == title):
				return item
		return None


	def search_fmt_key(self, query : str) -> list:
		"""get a list of Zotero keys from a zotero search query"""
		return [
			( x['data']['key'], *ZKCacheKey_from_item_raw(x))
			for x in self.search_raw(query)
		]

	def search_fmt(self, query : str) -> list:
		r = self.search_raw(query)
		return [
			ZKCacheKey_from_item_raw(x)
			for x in r
		]

	def find_possible_keys(self, cache_key : ZKCacheKey) -> Dict[ZoteroKey,ZKCacheKey]:
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

	def upload_attachment(self, filepath : str, parentID : ZoteroKey) -> tuple:
		"""upload an attachment to zotero"""
		# TODO: this is really inefficient, but it works for now
		# OPTIMIZE: upload all attachments at once
		# OPTIMIZE: instead of always deleting file, hash both files and skip if identical

		metadata = self.pyzot._attachment_template("imported_file").copy()
		metadata["title"] = 'kindleclip_' + os.path.basename(filepath)
		metadata["filename"] = filepath

		# if file already exists, delete it first
		item_exists : Optional[dict] = self.search_title_exact(metadata["title"], top_only = False)
		try:
			if item_exists is not None:
				print(f"    deleting existing attachment {item_exists['key']}")
				self.pyzot.delete_item([item_exists])

			res = self.pyzot._attachment([metadata], parentID)
			
			res_key = [
				x 
				for x in ['success', 'failure', 'unchanged']
				if len(res[x]) > 0
			].pop()

			return ( res[res_key][0]['key'], res_key )
		except PyZoteroError as e:
			print(f"    error uploading attachment: {e}")
			return (None, 'error')


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

		# TODO: loop around the command if its invalid

		# if ignore, then save this to cache
		if action == 'ignore':
			zk_cache_set(cache_key, -1)
		# if postpone, then save this to cache
		elif action == 'postpone':
			zk_cache_set(cache_key, 0)
		# if add, then:
		elif action == 'add':
			# look in Zotero for items with matching author and title
			possible_keys : Dict[ZoteroKey,ZKCacheKey] = zotero_manager.find_possible_keys(cache_key)
			print('# possible Zotero keys:')
			for key,info in possible_keys.items():
				print(
					f'\t{key} : {info.title}' 
					+ f' by {info.author}' if info.author else ''
				)

			# ask the user which item to pair with
			print(f'# please select Zotero item to pair with "{title}" by "{author}", or selection action from {ZK_CACHE_ACTIONS} by prefixing with "!":')
			action_pair : str = input('  > ')

			# if command given, process
			# TODO: commands not detected here properly
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
					
				else:
					# if key is not in possible keys, then complain and then postpone
					print(f'WARNING: "{zotero_key}" is not a possible Zotero key for "{title}" by "{author}". postponing.')
					zk_cache_set(cache_key, 0)

		else:
			raise KeyError(f'unknown action "{action}"')
	else:
		if cache_value == -1:
			print(f'  ## ignoring "{title}" by "{author}", bibtex key is unknown')
		elif isinstance(cache_value, str):
			# and then upload the notes
			notes_export : str = export_func(data)
			fname_export : str = '../zotero_export/' + ClippingsItem_to_filename(cache_key) + '.md'
			with open(fname_export, 'w') as f:
				f.write(notes_export)
			res = zotero_manager.upload_attachment(fname_export, cache_value)
			print(f'  ## uploaded: {cache_key=} {fname_export=} {cache_value=} {res=}')

def zotero_upload_all(
		data_json_path : str = DATA_EXPORT_PATH,
		zotero_manager : ZoteroManager = None,
		export_func : Callable[[List[ClippingsItem]], str] = ClippingsItem_lst_md,
	) -> None:

	if zotero_manager is None:
		zotero_manager = ZoteroManager()

	with open(data_json_path, 'r') as f:
		data : Dict[str,List[ClippingsItem]] = json.load(f)
		data = {
			k : [ ClippingsItem(**x) for x in v ]
			for k,v in data.items()
		}

	for title,items in data.items():
		print(f'# uploading "{title}"')
		zotero_upload_notes(zotero_manager, items, export_func = export_func)

	return
