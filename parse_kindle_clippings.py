from typing import *
import json

from util.clippingsitem import ClippingsItem
from util.export import (
	sort_clippings_by_book, read_and_save_json, read_and_save_bybook_md,
)

from util.zotero import (
	zotero_upload_all,
)


if __name__ == "__main__":
	import fire
	fire.Fire({
		'data_list' : lambda fn='../data.json' : read_and_save_json(fn),
		'data_sorted' : lambda fn='../data.json' : read_and_save_json(fn, data_converter=sort_clippings_by_book),
		'md_sorted' : read_and_save_bybook_md,
		'zotero_upload' : zotero_upload_all,
	})




