import logging
import traceback
from rdflib import Graph
import yaml
import re
import time
import gzip
import zlib
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
import transform_service
import oai_to_schemaorg_mapping as mapping
from rdflib.namespace import SDO, RDF
import oai_xpaths as xpath

logger = logging.getLogger(__name__)
config = yaml.safe_load(open('config/config.yml', encoding='utf-8'))

# Verwijder ongeldige XML control chars (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F)
INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

# Repareer losse & die geen geldige entity openen, bijv. "A&B" -> "A&amp;B"
AMP_FIX = re.compile(r'&(?![A-Za-z#][A-Za-z0-9]*;)')

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

def oai_params_first_call(verb: str, metadata_prefix: Optional[str], set_spec: Optional[str]) -> dict:
    params = {"verb": verb}
    if verb in ("ListRecords", "ListIdentifiers"):
        if metadata_prefix:
            params["metadataPrefix"] = metadata_prefix
        if set_spec:
            params["set"] = set_spec
    return params

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

def fetch_and_parse(url: str, headers: dict, 
                    retries: int, backoff: float) -> Tuple[ET.Element, str]:
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

    # Eerste parsepoging
    try:
        root = ET.fromstring(text)
        return root, text
    except ET.ParseError:
        pass

    # Reparatie: losse & omzetten naar &amp; en opnieuw proberen
    repaired = AMP_FIX.sub("&amp;", text)
    try:
        root = ET.fromstring(repaired)
        logger.debug("Waarschuwing: XML gerepareerd (losse & geëscapet).")
        return root, repaired
    except ET.ParseError as e2:
        # Dump voor diagnose
        raise e2

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
def harvest(target_graph: Graph, base_url: str, metadata_prefix: Optional[str], set_spec: Optional[str],
            sleep_between: float = 0.2, retries: int = 3, backoff: float = 1.5, 
            max_items: Optional[int] = None, state: Optional[dict] = None, verb='ListRecords') -> Graph:

    headers = {
        "User-Agent": "OAI-PMH harvester (Python stdlib)",
        "Accept": "application/xml, text/xml;q=0.9, */*;q=0.1",
        "Accept-Encoding": "identity, gzip, deflate",
    }
    st_items = len(list(target_graph.subjects(RDF.type, SDO.ArchiveComponent)))

    params = {"verb": verb}
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
        while True:
            len_diff = len(list(target_graph.subjects(RDF.type, SDO.CreativeWork))) - st_items
            if max_items is not None and len_diff >= max_items:
                logger.debug(f"Max-items bereikt ({max_items}). Stoppen.")
                state.update({
                    'total': int(state.get('total', 0)) + len_diff,
                })
                break

            if state.get("resumptionToken") and state.get('resumptionToken', '').strip() != '':
                params["resumptionToken"] = state.get("resumptionToken")

            url = build_url(base_url, params)
            root, text = fetch_and_parse(url, headers, retries, backoff)
            text = clean_xml(text)
            root = ET.fromstring(text)

            # Selecteer items
            if verb == "ListRecords":
                elements = root.findall(".//oai:metadata/oai:record", NS)
 
                for element in elements:
                    try:
                        transform_service.parse_tree_to_graph(target_graph, element, mapping, xpath, 'ns0', 'http://www.openarchives.org/OAI/2.0/')
                    except (AssertionError, TypeError, Exception) as te:
                        logger.warning('Error during transformation: %s', str(traceback.format_exception(te)))

            # Volgende pagina
            rt_el = root.find(".//oai:resumptionToken", NS)
            # maybe get oai:completeListSize?
            rt = rt_el.text.strip() if rt_el is not None and rt_el.text else ""
            
            logger.debug(f"{len(list(target_graph.subjects(RDF.type, SDO.CreativeWork)))} items in graph. ResumptionToken {'aanwezig' if rt else 'ontbreekt'}.")

            state.update({
                "resumptionToken": rt,
            })

            if not rt:
                break

            time.sleep(sleep_between)

        return target_graph
    except Exception as e:
        raise e

def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    print('Starting harvest test.')
    rgraph = Graph()
    persistant_state = {
                "total": 0,
                "resumptionToken": "",
        }
    print('Calling harvester..')
    rgraph = harvest(rgraph, 
                        base_url=config['SRC_URI'], 
                        verb='ListRecords', 
                        metadata_prefix='kc_rs', 
                        set_spec=config['SRC_DB'],
                        state=persistant_state,
                        max_items=10)
    records = len(list(rgraph.subjects(RDF.type, SDO.ArchiveComponent)))
    rgraph.serialize(format='json-ld', 
                            destination='TEST-oai-kc.jsonld',  
                            auto_compact=True)
    logger.info(f'got {records} records ')
    #assert records == 100

if __name__ == "__main__":
    main()