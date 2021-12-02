from typing import *

from util.json_serialize import arbit_json_serialize
from util.clippingsitem import (
	ClippingsType, ClippingsItem,
	CLIPPINGS_FILENAME,
	parse_clippings_file,
)

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