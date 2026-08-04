from datetime import datetime
import logging
import re
import time
import gzip
import zlib
import os
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
import yaml

CONFIG_PATH = os.getenv('CONFIG_PATH', 'config/config.yml')
ENCODING = os.getenv('ENCODING', 'utf-8')

# Verwijder ongeldige XML control chars (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F)
INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

# Repareer losse & die geen geldige entity openen, bijv. "A&B" -> "A&amp;B"
AMP_FIX = re.compile(r'&(?![A-Za-z#][A-Za-z0-9]*;)')

logger = logging.getLogger(__name__)
config = yaml.safe_load(open(CONFIG_PATH, encoding=ENCODING))

# Namespaces
NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/"
}

HEADER = ".//oai:header"
IDENTIFIER = ".//oai:identifier"
DATESTAMP =  ".//oai:datestamp"

def clean_xml(s: str) -> str:
    s = INVALID_XML_CHARS.sub("", s)
    return s

def build_url(base: str, params: dict) -> str:
    base = base.rstrip("?")
    return f"{base}?{urllib.parse.urlencode(params)}"

# -----------------------------
# HTTP ophalen met retries en Retry-After
# -----------------------------
def safe_open_url(req: urllib.request.Request, retries: int = 3, backoff: float = 1.5) -> Tuple[int, str, bytes, dict]:
    """
    HTTP GET met retries en backoff.
    Respecteert Retry-After bij 429/503.
    Retourneert (status, content_type, raw_bytes, headers_dict).
    """
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as resp:
                status = getattr(resp, "status", 200)
                headers = {k: v for k, v in resp.headers.items()}
                ct = headers.get("Content-Type", "")
                ce = headers.get("Content-Encoding", "")
                raw = resp.read()

                # Decompressie (pas ná read)
                if ce.lower() == "gzip":
                    raw = gzip.decompress(raw)
                elif ce.lower() in ("deflate", "zlib"):
                    try:
                        raw = zlib.decompress(raw)
                    except zlib.error:
                        raw = zlib.decompress(raw, -zlib.MAX_WBITS)

                logger.debug(f"HTTP {status} | Content-Type: {ct} | Content-Encoding: {ce or 'none'}")
                return status, ct, raw, headers

        except urllib.error.HTTPError as e:
            last_err = e
            status = e.code
            headers = {k: v for k, v in (e.headers or {}).items()}
            retry_after = headers.get("Retry-After")
            wait = backoff * (attempt + 1)
            if status in (429, 503) and retry_after:
                try:
                    wait = max(wait, float(retry_after))
                except ValueError:
                    # Als Retry-After geen seconds is: val terug op backoff
                    pass
            if attempt == retries - 1:
                raise
            logger.warning(f"HTTPError {status}: {e.reason}. Wachten {wait:.1f}s en opnieuw proberen...")
            time.sleep(wait)

        except Exception as e:
            last_err = e
            if attempt == retries - 1:
                raise
            wait = backoff * (attempt + 1)
            logger.warning(f"Netwerkfout: {e}. Wachten {wait:.1f}s en opnieuw proberen...")
            time.sleep(wait)

    if last_err:
        raise last_err

def fetch_and_parse(url: str, 
                    headers: dict[str, str], 
                    retries: int, 
                    backoff: float) -> Optional[ET.ElementTree]:
    """
    Haal op -> decodeer -> schoon -> parse.
    Bij parsefout: één reparatiepoging met AMP_FIX. Dump ruwe response en stop als het dan nog faalt.
    Retourneert (root_element, text_na_clean/repair).
    """
    req = urllib.request.Request(url, headers=headers)
    status, ct, raw, _ = safe_open_url(req, retries=retries, backoff=backoff)

    # Decodeer en schoon
    text = raw.decode("utf-8", errors="replace")
    text = clean_xml(text)
    text = re.sub(' xmlns="http://www.openarchives.org/OAI/2.0/"', '', text)
    text = re.sub(' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '', text)
    text = re.sub(' xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"', '', text)
    text = AMP_FIX.sub("&amp;", text)

    filepath = f'{config['EXPORT_DIR']}record_{datetime.timestamp(datetime.now())}.xml'
    with open(filepath, mode='w', encoding=ENCODING) as file:
        file.write(text)

    # Eerste parsepoging
    try:
        tree = ET.parse(filepath)
        #root = ET.fromstring(text)
        return tree
    except ET.ParseError as pe:
        raise pe



def oai_params_first_call(verb: str, metadata_prefix: Optional[str], set_spec: Optional[str]) -> dict:
    params = {"verb": verb}
    if verb in ("ListRecords", "ListIdentifiers"):
        if metadata_prefix:
            params["metadataPrefix"] = metadata_prefix
        if set_spec:
            params["set"] = set_spec
    return params

# -----------------------------
# Harvest met rotatie, limiet, CSV/JSONL
# -----------------------------
def harvest(base_url: str, metadata_prefix: Optional[str], set_spec: Optional[str],
            sleep_between: float = 0.2, retries: int = 3, backoff: float = 1.5, 
            page_limit=0, state: Optional[dict] = None, verb='ListRecords'):

    headers = {
        "User-Agent": "OAI-PMH harvester (Python stdlib)",
        "Accept": "application/xml, text/xml;q=0.9, */*;q=0.1",
        "Accept-Encoding": "identity, gzip, deflate",
    }

    params = {'verb': verb, 'limit': config['SRC_API_LIMIT']}
    if metadata_prefix:
        params["metadataPrefix"] = metadata_prefix
    if set_spec:
        params["set"] = set_spec
    #if modified:
    #    params["from"] = modified

    if not state:
        # State init
        state = {
            "total": 0,
            "resumptionToken": "",
        }
    
    try:
        page_iterator = 0
        while True:
            if state.get("resumptionToken") and state.get('resumptionToken', '').strip() != '':
                params["resumptionToken"] = state.get("resumptionToken")

            url = build_url(base_url, params)
            tree = fetch_and_parse(url, headers, retries, backoff)
            root = tree.getroot()

            # Selecteer items
            if verb == "ListRecords":
            
                record_elements = root.findall(".//metadata/record", NS)

                if len(record_elements) > 0 and (page_limit == 0 or page_iterator < page_limit): 
                    page_iterator += 1
                    if page_limit > 0 and (page_limit / page_iterator) % (page_limit/10) == 0:
                        logger.info('Harvested %i out of %i pages. ', page_iterator, page_limit)
                else:
                    break

            # Volgende pagina
            rt_el = root.find(".//resumptionToken", NS)
            # maybe get oai:completeListSize?
            rt = rt_el.text.strip() if rt_el is not None and rt_el.text else ""
            
            state.update({
                "resumptionToken": rt,
            })

            if not rt:
                break

            time.sleep(sleep_between)

    except Exception as e:
        raise e

def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    persistent_state = {
                "total": 0,
                "resumptionToken": "",
        }
    harvest(base_url=config['SRC_URI'], 
            verb='ListRecords', 
            metadata_prefix=config['SRC_PFX'], 
            set_spec=config['SRC_DB'],
            state=persistent_state)

if __name__ == "__main__":
    main()