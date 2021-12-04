from typing import *
import json
import datetime

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

CLIPPINGS_FILENAME : str = "..\\My Clippings.txt"

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

	# first, just use the whole string as the title
	title : str = line_titleauthor
	author : str = ''
	
	try: 
		if '(' in line_titleauthor:
			# first, assume it is in epub format:
			# find the title by getting all the text before the last '('
			index_title_end : str = line_titleauthor.rindex('(')
			title = line_titleauthor[:index_title_end].strip()
			# and the author(s) by stripping the text after the last '('
			author = line_titleauthor[index_title_end:].strip(' \t\n()').strip()
		elif line_titleauthor.count('-') == 2:
			# if it has dashes, assume it is in the (custom) zotero format
			# `author_names_etal-<year>-title_with_underscores`
			author, year, title = line_titleauthor.split('-')
			title = title.replace('_', ' ').strip()
			author = author.replace('_', ' ').strip()

	except (IndexError,ValueError) as e:
		print(f'caught exception when finding metadata: \n {author=}\t{title=}\n{e}')
		

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
		abs(itm_note.date_unix - itm_highlight.date_unix) < 10,
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
		found_match : bool = False
		for idx_new,item_new in enumerate(data_new):
			# make sure the item can still be augmented
			if (item_new.text_note is not None) or (item_new.clip_type != 'Highlight'):
				continue

			if check_can_merge(item_note, item_new):
				data_new[idx_new] = merge_note_highlight(item_note, item_new)
				found_match = True
				break
		# if no match was found, add the note to the list
		if not found_match:
			data_new.append(item_note)

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