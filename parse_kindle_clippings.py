from typing import *

import json
import datetime

from typing import *
from collections import namedtuple
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





ClippingsType = Literal["Highlight", "Note", "Note_Merged"]
ClippingsItem = NamedTuple('ClippingsItem', [
	('title', str),
	('author', str),
	('location', str),
	('clip_type', ClippingsType),
	('date', str),
	('date_unix', int),
	('text_highlight', Optional[str]),
	('text_note', Optional[str]),
])

CLIPPINGS_FILENAME : str = "My Clippings.txt"
MARKERS : Dict[str,str] = {
	'meta_split' : '|',
	'meta_type_prefix' : '- Your ',
	'meta_date_prefix' : 'Added on ',
	'item_split' : '==========',
}



def parse_ClippingsItem(item_raw : str) -> ClippingsItem:
	"""parses a single clippings item into a named tuple

	example clipping text:
	```
	*How We Learn (Stanislas Dehaene)
	- Your Highlight on Location 3824-3826 | Added on Wednesday, December 2, 2021 10:05:32 PM

	The new idea is that during sleep, our brain works in the opposite direction: from top to bottom. During the night, we use our generative models to synthesize new, unanticipated images, and part of our brain trains itself on this array of images created from scratch.
	```

	- the first line is title and author (`*` is a 3-byte sequence that we ignore, idk what it does)
	- the second line is the type, location, and date of highlight
	- the third line is empty
	- the fourth line is the text
	- the fifth line is empty
	
	### Parameters:
	 - `item_raw : str`   
	
	### Returns:
	 - `ClippingsItem` 
	"""

	line_titleauthor, line_meta, line_text = [ line.strip() for line in item_raw.split("\n") if line.strip() != '' ]

	# check validity of the item
	assert line_meta.startswith(MARKERS['meta_type_prefix']), f"`line_meta` should start with `- Your `, got {line_meta}"

	# remove weird bytes at the begginning of `line_titleauthor`
	line_titleauthor = line_titleauthor[3:]

	# find the title by getting all the text before the last '('
	index_title_end : str = line_titleauthor.rindex('(')
	title : str = line_titleauthor[:index_title_end].strip()
	# and the author(s) by stripping the text after the last '('
	author : str = line_titleauthor[index_title_end:].strip(' \t\n()').strip()

	# find the type 
	clip_type : ClippingsType = (
		line_meta[len(MARKERS['meta_type_prefix']):]
		.split(' ')[0]
		.strip()
	)

	# find the clipping location
	location : str = (
		line_meta.split(MARKERS['meta_split'])[0]
		.strip()
		.split(' ')[-1]
		.strip()
	)

	# find the date
	date : str = (
		line_meta
		.split(MARKERS['meta_split'])[1]
		.strip()[len(MARKERS['meta_date_prefix']):]
		.strip()
	)

	# convert the date to unix timestamp
	# note that the format is 
	# `<weekday>, <month> <day>, <year> <hour>:<minute>:<second> <AM/PM>`
	# example date:
	# "Wednesday, December 2, 2021 10:05:32 PM"
	date_unix : int = int(
		datetime.datetime.strptime(date, "%A, %B %d, %Y %I:%M:%S %p").timestamp()
	)

	# find the text
	text_highlight : Optional[str] = None
	text_note : Optional[str] = None
	if clip_type == 'Highlight':
		text_highlight = line_text.strip()
	elif clip_type == 'Note':
		text_note = line_text.strip()
	else:
		raise KeyError(f'unknown clip type {clip_type}')

	return ClippingsItem(
		title = title,
		author = author,
		location = location,
		clip_type = clip_type,
		date = date,
		date_unix = date_unix,
		text_highlight = text_highlight,
		text_note = text_note,
	)


def check_can_merge(itm_note : ClippingsItem, itm_highlight : ClippingsItem) -> bool:
	loc_note_end : int = int(itm_note.location.split('-')[-1])
	loc_hl_end : int = int(itm_note.location.split('-')[-1])

	return all([
		# check types correct
		itm_note.clip_type == 'Note',
		itm_highlight.clip_type == 'Highlight',
		# check locations match
		loc_note_end == loc_hl_end,
		# check dates match
		itm_note.date_unix == itm_highlight.date_unix,
	])


def merge_note_highlight(itm_note : ClippingsItem, itm_highlight : ClippingsItem) -> ClippingsItem:
	"""merges a note and a highlight into a single item. performs no checks

	### Parameters:
	 - `itm_note : ClippingsItem`   
	 - `itm_highlight : ClippingsItem`   
	
	### Returns:
	 - `ClippingsItem` 
	"""

	# merge, with highlight taking precedence
	return ClippingsItem(
		title = itm_highlight.title,
		author = itm_highlight.author,
		location = itm_highlight.location,
		clip_type = "Note_Merged", # specify merged type
		date = itm_highlight.date,
		date_unix = itm_highlight.date_unix,
		text_highlight = itm_highlight.text_highlight, # highlight text
		text_note = itm_note.text_note, # note text
	)


def merge_list_clip_items(data : List[ClippingsItem]) -> List[ClippingsItem]:
	"""merge clippings if they are sufficiently close in both time and location
	
	### Parameters:
	 - `data : List[ClippingsItem]`   
	
	### Returns:
	 - `List[ClippingsItem]` 
	"""

	# separate the items by their type
	assert all(x.clip_type in ['Highlight', 'Note'] for x in data), f"all items should be of type `Highlight` or `Note`, got {data}"
	data_new : List[ClippingsItem] = [
		item for item in data if item.clip_type == 'Highlight'
	]
	data_notes_only : List[ClippingsItem] = [
		item for item in data if item.clip_type == 'Note'
	]

	# loop over all notes, and merge them into highlights that are missing notes
	for item_note in data_notes_only:
		# loop over highlights, and see if there is a highlight that has the same location and time
		for idx_new,item_new in enumerate(data_new):
			# make sure the item can still be augmented
			if (item_new.text_note is not None) or (item_new.clip_type != 'Highlight'):
				continue

			if check_can_merge(item_note, item_new):
				data_new[idx_new] = merge_note_highlight(item_note, item_new)
				break

	return data_new

	


def parse_clippings_file(filename : str = CLIPPINGS_FILENAME, merge : bool = True) -> List[ClippingsItem]:
	"""parses a clippings file into a list of named tuples

	### Parameters:
	 - `filename : str`   
	
	### Returns:
	 - `List[ClippingsItem]` 
	"""

	with open(filename, 'r') as f:
		data : List[ClippingsItem] = [
			parse_ClippingsItem(item)
			for item in f.read().split(MARKERS['item_split'])
			if item.strip()
		]
	
	if merge:
		data = merge_list_clip_items(data)
	
	return data


def sort_clippings_by_book(clippings : List[ClippingsItem]) -> Dict[str, List[ClippingsItem]]:
	"""sorts the clippings by book

	### Parameters:
	 - `clippings : List[ClippingsItem]`   
	
	### Returns:
	 - `Dict[str, List[ClippingsItem]]` 
	"""

	data : Dict[str, List[ClippingsItem]] = dict()

	for item in clippings:

		if item.title not in data:
			data[item.title] = list()

		data[item.title].append(item)

	return data


def read_and_save_json(
		filename : str = 'data.json', 
		data_reader : Callable = parse_clippings_file,
		data_converter : Callable = lambda x : x,
	) -> None:
	"""saves the data to a json file

	### Parameters:
	 - `data_reader : Callable`   
	 - `filename : str`   
	
	### Returns:
	 - `None` 
	"""

	data : dict = arbit_json_serialize(
		data_converter(
			data_reader()
		)
	)

	with open(filename, 'w', newline='\n') as f:
		json.dump(
			data, 
			f,
			indent = 4,
		)

def ClippingsItem_to_filename(item : ClippingsItem) -> str:
	"""turn a clippings item into a filename
	
	all whitespace replaced with '-' or removed
	all characters except alphanumeric, '_','-' are replaced with '.'

	format:
	`<title>_<author_short>.txt`
	
	### Parameters:
	 - `item : ClippingsItem`   
	
	### Returns:
	 - `str` 
	"""
	
	# replace all whitespace with '-'
	title : str = (
		item.title
		.strip()
		.replace('\r', '')
		.replace('\t', '--')
		.replace('\n', '---')
		.replace(' ', '-')
	)
	
	# replace all characters except alphanumeric, '_','-' with '.'
	title = ''.join(
		[
			c if c.isalnum() or c in '_-' else '.'
			for c in title
		]
	)

	# HACK:
	# get author initials
	author_short : str = (
		'-'.join(
			(
				item.author
				.strip()
				.replace('\r', '')
				.replace('\t', '')
				.replace('\n', '')
				.replace(',', ' ')
			).split()
		)
	)

	return f'{title}_{author_short}'




def ClippingsItem_md_skip_TA(item : ClippingsItem) -> str:
	"""`ClippingsItem` as markdown, skipping the title and author"""

	clip_type_text : str = 'Note'

	if item.clip_type == 'Note':
		item_hltext = '   (unknown highlighted text)'
	else:
		item_hltext = '   > ' + item.text_highlight.strip().replace("\n", "\n   > ")


	if item.clip_type == 'Highlight':
		item_notetext = []
		clip_type_text = 'Highlight'
	else:
		item_notetext = [
			"  ```",
			"  " + item.text_note.strip().replace("\n", "\n   "),
			"  ```",
		]
		
	return '\n'.join([
		f'- {clip_type_text} at location **{item.location}** made on *{item.date}*',
		item_hltext,
		*item_notetext,
	])


def grab_title_author(data : List[ClippingsItem]) -> Tuple[str,str]:
	"""grab title and author from data, check they all match"""
	title = data[0].title
	assert all(
		item.title == title
		for item in data
	), 'all items must have the same title string'

	author = data[0].author
	assert all(
		item.author == author
		for item in data
	), 'all items must have the same author string'

	return title, author


def ClippingsItem_lst_md(data : List[ClippingsItem], sort_clipitems : Callable = lambda x : x.date_unix) -> str:
	"""export list of items as markdown"""
	output : List[str] = list()
	# write header
	title,author = grab_title_author(data)
	output.append(f'# {title}\n\n')
	output.append(f'**by {author}**\n\n')

	# sort clippings items
	items_sorted : List[ClippingsItem] = sorted(
		data,
		key = sort_clipitems,
	)

	# write sorted clippings
	output.append('\n\n'.join([
		ClippingsItem_md_skip_TA(item)
		for item in items_sorted
	]))

	return '\n'.join(output)


def read_and_save_bybook_md(
		file_in : str = CLIPPINGS_FILENAME, 
		out_dir : str = 'notes/', 
		json_out : Optional[str] = 'data.json',
	) -> None:
	"""reads `file_in`, splits up by book, and saves as markdown to `out_dir/<filename>`
	
	[extended_summary]
	
	### Parameters:
	 - `file_in : str`   
	   (defaults to `CLIPPINGS_FILENAME`)
	 - `out_dir : str`   
	   (defaults to `'books/'`)
	 - `json_out : Optional[str]`   
	   (defaults to `None`)
	"""

	# read and process data
	data_list : List[ClippingsItem] = parse_clippings_file(file_in)
	data_bybook : Dict[str, List[ClippingsItem]] = sort_clippings_by_book(data_list)

	# save as json
	if json_out is not None:
		with open(json_out, 'w', newline='\n') as f:
			json.dump(
				data_bybook, 
				f,
				indent = 4,
			)
	
	# export to markdown
	for title, items in data_bybook.items():
		filename : str = out_dir + ClippingsItem_to_filename(items[0]) + '.md'
		with open(filename, 'w', newline='\n') as f:
			print(f'  saving {len(items)} notes from "{title}"')
			f.write(ClippingsItem_lst_md(items))
			

ZOTERO_KINDLE_CACHE_FILE : str = 'zotero_kindle_cache.json'

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



if __name__ == "__main__":
	import fire
	fire.Fire({
		'data_list' : lambda fn='data.json' : read_and_save_json(fn),
		'data_book' : lambda fn='data.json' : read_and_save_json(fn, data_converter=sort_clippings_by_book),
		'md_book' : read_and_save_bybook_md,
	})




