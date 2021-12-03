from typing import *

from util.zotero import ZoteroKey,ZoteroManager


def get_single_item(item_id : ZoteroKey) -> str:
	zotero_manager = ZoteroManager()
	return zotero_manager.get_raw(item_id)

def search_items(query : str) -> List[str]:
	zotero_manager = ZoteroManager()
	return zotero_manager.search_fmt(query)

if __name__ == '__main__':
	import fire
	fire.Fire({
		'get_single_item' : get_single_item,
		'search_items' : search_items
	})