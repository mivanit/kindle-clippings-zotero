from typing import *
import json

from util.zotero import ZoteroKey,ZoteroManager,ZKCacheKey_from_item_raw

from pyzotero import zotero

def get_single_item(item_id : ZoteroKey) -> str:
	zotero_manager = ZoteroManager()
	return zotero_manager.get_raw(item_id)

def search_items(query : str) -> List[str]:
	zotero_manager = ZoteroManager()
	return zotero_manager.search_fmt_key(query)

def upload_note(filepath : str, parentID : ZoteroKey):
	zotero_manager = ZoteroManager()
	data = zotero_manager.get_raw(parentID)
	return zotero_manager.upload_attachment(filepath, parentID)

if __name__ == '__main__':
	import fire
	fire.Fire({
		'get_single_item' : get_single_item,
		'search_items' : search_items,
		'upload_note' : upload_note,
	})