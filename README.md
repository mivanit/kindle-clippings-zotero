# kindle-clippings-zotero
parsing and exporting kindle clippings, as well as syncing them with [Zotero](https://www.zotero.org). I made this tool so that I could read and annotate papers on my kindle, and then send them back to my Zotero library without too much manual work.

# Disclaimer:
This tool has not been thoroughly tested, and thus can behave unexpectedly. It directly interacts with your Zotero library (and indirectly with your Kindle device) and thus might delete your entire library, brick your kindle, or a wide variety of other unpleasant things. **USE AT YOUR OWN RISK**


# Installation

1. clone the repo and install the minimal requirements. 

```bash
git clone https://github.com/mivanit/kindle-clippings-zotero kindle-clippings-zotero
cd kindle-clippings-zotero
pip install -r requirements.txt
```

1. copy the file `__zotero_api__.json.TEMPLATE` to create a file `__zotero_api__.json`. Replace the dummy key and url with whatever you'd like. See the [Zotero API docs](https://www.zotero.org/support/dev/web_api/v3/basics) for information on how to get your library ID and an API key.


3. Done!

> Note: the only dependencies are [`urllib3`](https://urllib3.readthedocs.io/en/stable/) and [`pyzotero`](https://github.com/urschrei/pyzotero). Eventually, I'd like to depend only on the former -- but for now, direct calls to the [Zotero api](https://www.zotero.org/support/dev/web_api/v3/basics) through `urllib3` are made.

# Usage

data will be written to the parent directory. It is expected that a file `CLIPPINGS_FILENAME : str = "../My Clippings.txt"` exists relative to the directory the script is run from. I recommend a separate script to copy the clippings file to the appropriate location. On my kindle, it is found at `"Kindle/documents/My Clippings.txt"`.

> Note: I have not figured out a way to access the kindle clippings (for non-kindle-store items) from the desktop or web readers, although I know that the clippings data must be uploaded somehow, since it can (usually) be accessed from a mobile device. If you figure out how to interact with Amazon's API and get this data, please let me know! For now, I need to physically plug my kindle into my machine.

## Exporting as `json`

to a `json` file mapping titles to lists of clipping items
```bash
python parse_kindle_clippings.py data_sorted <output>
```

## Exporting as markdown

Takes in a raw clippings file `file_in`, and outputs a sorted `json` to `json_out`, as well as markdown files with clippings to the directory `out_dir`
```bash
python parse_kindle_clippings.py md_sorted <file_in> <out_dir> <json_out>
```

## Uploading to zotero

relies on existing exported `json`, pass this as `data_json_path`. For each item (identified by title), it stores in the cache file `zotero_kindle_cache.json` whether to ignore the clippings, postpone and prompt the user next time, or a Zotero item key to be used as the parent item. If the user is prompted, you can specify `'a'` or `'add'` to get a list of possible matches and their Zotero keys (you can also specify any key you wish, but be careful)

```bash
python parse_kindle_clippings.py zotero_upload_all <data_json_path>
```


