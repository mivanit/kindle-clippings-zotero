from typing import *
import json

from util.json_serialize import arbit_json_serialize
from util.clippingsitem import (
	ClippingsType, ClippingsItem,
	CLIPPINGS_FILENAME, MARKERS,
	parse_ClippingsItem, merge_list_clip_items
)



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
		filename : str = '../data.json', 
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
		out_dir : str = '../notes', 
		json_out : Optional[str] = '../data.json',
	) -> None:
	"""reads `file_in`, splits up by book, and saves as markdown to `out_dir/<filename>`
	
	[extended_summary]
	
	### Parameters:
	 - `file_in : str`   
	   (defaults to `CLIPPINGS_FILENAME`)
	 - `out_dir : str`   
	   (defaults to `'../notes/'`)
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



if __name__ == "__main__":
	import fire
	fire.Fire({
		'data_list' : lambda fn='../data.json' : read_and_save_json(fn),
		'data_book' : lambda fn='../data.json' : read_and_save_json(fn, data_converter=sort_clippings_by_book),
		'md_book' : read_and_save_bybook_md,
	})




