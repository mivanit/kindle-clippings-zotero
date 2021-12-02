from typing import *
import json

from util.clippingsitem import ClippingsItem
from util.export import (
	sort_clippings_by_book, read_and_save_json, read_and_save_bybook_md,
)


if __name__ == "__main__":
	import fire
	fire.Fire({
		'data_list' : lambda fn='../data.json' : read_and_save_json(fn),
		'data_book' : lambda fn='../data.json' : read_and_save_json(fn, data_converter=sort_clippings_by_book),
		'md_book' : read_and_save_bybook_md,
	})




