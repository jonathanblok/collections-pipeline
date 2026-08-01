from datetime import datetime
import logging
import re
from typing import Optional, Any
import xml.etree.ElementTree as ET
import uuid
from rdflib import Graph, Literal, Node, URIRef
from rdflib.namespace import RDF, SDO, XSD
import uritools
import config.tmp as mapping
import config.endpoint as endpoint

logger = logging.getLogger(__name__)

def transform(target_graph: Graph, tree: Any, xpath: Any, ns_pfx=None, ns=None) -> Graph:
    """ for each record this method is called """
    root_uri = None
    for const in mapping.RECORD.get('constants', []):
        conpred = const[0]  
        conobj = const[1]
        if conpred == RDF.type:
            root_uri = uritools.get_object_uri(endpoint.BASE_URI, endpoint.COLLECTION_ID, str(uuid.uuid4()), conobj)
        else if root_uri:
            target_graph.add((root_uri, conpred, conobj))
    for lit in mapping.RECORD.get('literals', {}):
        pass 
    for cls in mapping.RECORD.get('class', {}):
        pass 
    
def parse_tree_to_graph(target_graph: Graph, tree: Any, mapping: Any, xpath: Any, ns_pfx=None, ns=None) -> Graph:
    """ This function takes a Graph and an XML tree and parses the tree into the graph """

    # Adlib record priref unique identifier
    priref = get_text_from_tree(tree, xpath.PRIREF, ns_pfx, ns)
    # Modification date of record
    #mod_dt = datetime.strptime(tree.attrib['modification'], '%Y-%m-%dT%H:%M:%S')
    # Check record in scope
    if priref:
        record_object_node = uritools.get_object_uri(config['BASE_URI'], config['COLLECTION_ID'], priref, SDO.CreativeWork)
        #target_graph.add((record_object_node, SDO.sdDatePublished, Literal(mod_dt, datatype=XSD.dateTime)))
    else:
        logger.warning('no priref found skipping record')
        return target_graph
    
    # adding required field isPartOf dataset reference
    dataset_node = uritools.get_object_uri(config['BASE_URI'], 'rce/datacatalog', 'https://kennis.cultureelerfgoed.nl/index.php/Dataset/103', SDO.Dataset)
    target_graph.add((record_object_node, SDO.isPartOf, dataset_node))

    # add record types from mapping
    for rtype in mapping.RECORD_OBJECT_TYPES:
        target_graph.add((record_object_node, RDF.type, rtype))

    # first degree attributes
    for key, ref in mapping.CREATIVEWORK_MAPPING.items():
        item_text = get_text_from_tree(tree, ref, ns_pfx, ns)
        if item_text:
            target_graph.add((record_object_node, key, Literal(item_text, lang='nl')))

    # add property value attributes
    for key, ref in mapping.PROPERTY_VALUE_MAPPING.items():
        item_text = get_text_from_tree(tree, key, ns_pfx, ns)
        if item_text:
            property_node = uritools.get_object_uri(config['BASE_URI'], config['COLLECTION_ID'], str(uuid.uuid4()), SDO.PropertyValue)
            target_graph.add((property_node, RDF.type, SDO.PropertyValue))
            target_graph.add((property_node, SDO.value, Literal(item_text, datatype=XSD.string)))
            target_graph.add((property_node, SDO.propertyID, ref[1]))
            target_graph.add((property_node, SDO.description, Literal(ref[2], datatype=XSD.string)))
            target_graph.add((record_object_node, ref[0], property_node))

            if key == xpath.OBJECT_NUMBER:
                target_graph.add((record_object_node, SDO.url, uritools.get_beeldbank_result_from_adlib_object_number(item_text)))

    # add defined terms
    process_defined_terms(target_graph, tree, record_object_node, mapping.DEFINED_TERM_FIELD_MAPPING, mapping.DEFINED_TERM_TYPES, ns_pfx, ns)

    # add creator, creators are always persons in version 0.1 of datamodel
    sdo_creator_node = uritools.get_object_uri(config['BASE_URI'], config['COLLECTION_ID'], priref, SDO.Person)
    target_graph.add((sdo_creator_node, RDF.type, SDO.Person))
    target_graph.add((record_object_node, SDO.creator, sdo_creator_node))
    for key, ref in mapping.CREATOR_MAPPING.items():
        item_text = get_text_from_tree(tree, ref[0], ns_pfx, ns)
        if item_text:
            if ref[1] == URIRef and uritools.is_valid_uri(item_text):
                target_graph.add((sdo_creator_node, key, ref[1](item_text.strip())))
            elif ref[1] == Literal and ref[2]:
                target_graph.add((sdo_creator_node, key, ref[1](item_text.strip(), datatype=ref[2])))
            elif ref[1] == Literal:
                target_graph.add((sdo_creator_node, key, ref[1](item_text.strip())))
    
    process_defined_terms(target_graph, tree, sdo_creator_node, mapping.CREATOR_DEFINED_TERM_MAPPING, mapping.CREATOR_DEFINED_TERM_TYPES, ns_pfx, ns)

    # Link to image of object at memorix based on reproduction reference
    repro_list = findall_ns_wrapper(tree, mapping.MEDIAOBJECT_MAPPING[SDO.contentUrl], ns_pfx, ns)
    if repro_list:
        for index, r_ref in enumerate(repro_list):
            # check presence of reproduction reference and that the assigned rights permit publication 
            if r_ref.text and get_text_from_tree(tree, xpath.RIGHTS_ASSIGNED_VALUE, ns_pfx, ns) in config['RIGHTS_ASSIGNED_ALLOWLIST']:
                r_ref_node = uritools.get_object_uri(config['BASE_URI'], config['COLLECTION_ID'], r_ref.text, mapping.MEDIAOBJECT_MAPPING[RDF.type])
                target_graph.add((r_ref_node, RDF.type, mapping.MEDIAOBJECT_MAPPING[RDF.type]))
                target_graph.add((record_object_node, SDO.associatedMedia, r_ref_node))
                target_graph.add((r_ref_node, SDO.encodesCreativeWork, record_object_node))
                target_graph.add((r_ref_node, SDO.contentUrl, uritools.get_memorix_uri_from_reference(r_ref.text)))
                target_graph.add((r_ref_node, SDO.license, mapping.MEDIAOBJECT_MAPPING[SDO.license]))
                target_graph.add((r_ref_node, SDO.thumbnailUrl, uritools.get_memorix_uri_from_reference(r_ref.text, size='200x200')))


    # Dimensions
    qv_list = findall_ns_wrapper(tree, xpath.DIMENSION, ns_pfx, ns)
    for qv_dimension in qv_list:
        qv_node = uritools.get_object_uri(config['BASE_URI'], config['COLLECTION_ID'], str(uuid.uuid4()), SDO.QuantitativeValue)
        
        try:
            d_unit = get_text_from_tree(qv_dimension, xpath.DIMENSION_UNIT, ns_pfx, ns)
            target_graph.add((qv_node, RDF.type, SDO.QuantitativeValue))
            if d_unit:
                target_graph.add((qv_node, mapping.DIMENSION_MAPPING[xpath.DIMENSION_UNIT], Literal(d_unit, datatype=XSD.string)))
            
            #d_val = next(dimension.iterfind(tags.DIMENSION_VALUE))
            d_val = get_text_from_tree(qv_dimension, xpath.DIMENSION_VALUE, ns_pfx, ns)
            if d_val:
                target_graph.add((qv_node, mapping.DIMENSION_MAPPING[xpath.DIMENSION_VALUE], Literal(d_val, datatype=XSD.string)))
            
            #d_type = next(dimension.iterfind(tags.DIMENSION_TYPE))
            d_type = get_text_from_tree(qv_dimension, xpath.DIMENSION_TYPE, ns_pfx, ns)
            target_graph.add((qv_node, SDO.valueReference, Literal(d_type, lang='nl')))
            target_graph.add((record_object_node, SDO.size, qv_node))
        except StopIteration:
            logger.error('Invalid Dimension: %s', ET.tostring(qv_dimension))
            target_graph.remove((qv_node, None, None))
            target_graph.remove((None, None, qv_node))        

    # rightsholder
    rholder_text = get_text_from_tree(tree, xpath.RIGHTS_HOLDER, ns_pfx, ns)
    if rholder_text:
        sdo_rholder_node = uritools.get_object_uri(config['BASE_URI'], config['COLLECTION_ID'], str(uuid.uuid4()), SDO.Person)
        target_graph.add((sdo_rholder_node, RDF.type, SDO.Person))
        target_graph.add((sdo_rholder_node, SDO.name, Literal(rholder_text, datatype=XSD.string)))
        target_graph.add((record_object_node, SDO.copyrightHolder, sdo_rholder_node))

    return target_graph
    
def get_text_from_tree(tree: (ET.ElementTree | ET.Element), target_xpath: str, ns_pfx: Optional[str], ns: Optional[str]) -> Optional[str]:
    if ns_pfx and ns:
        xp_segms = re.split(r'\.//|\./|/', target_xpath)[1:]
        for segment in xp_segms:
            target_xpath = target_xpath.replace(segment, f'{ns_pfx}:{segment}')
        t_elem = tree.find(target_xpath, namespaces={ns_pfx:ns})
    else:
        t_elem = tree.find(target_xpath)
    if t_elem is not None and t_elem.text:
        return t_elem.text
    
def findall_ns_wrapper(tree: (ET.ElementTree | ET.Element), target_xpath: str, ns_pfx: Optional[str], ns: Optional[str]) -> Optional[list[ET.Element]]:
    if ns_pfx and ns:
        xp_segms = re.split(r'\.//|\./|/', target_xpath)[1:]
        for segment in xp_segms:
            target_xpath = target_xpath.replace(segment, f'{ns_pfx}:{segment}')
        t_elems = tree.findall(target_xpath, namespaces={ns_pfx:ns})
    else:
        t_elems = tree.findall(target_xpath)
    return t_elems

def process_defined_terms(target_graph: Graph, tree: (ET.ElementTree | ET.Element), target_node: Node, field_mapping: dict[str|list], type_mapping: dict[str|list], ns_pfx: Optional[str], ns: Optional[str]):
    # add defined terms
    for key, ref in field_mapping.items():
        for dt_item in findall_ns_wrapper(tree, key, ns_pfx, ns):
            dt_name = get_text_from_tree(dt_item, ref[1], ns_pfx, ns)
            if dt_name:
                dt_url = URIRef(uritools.get_object_uri(config['BASE_URI'], config['COLLECTION_ID'], dt_name,  type_mapping[key][0]))
                
                target_graph.add((target_node, ref[0], dt_url))
                target_graph.add((dt_url, SDO.name, Literal(dt_name, datatype=XSD.string)))
                for item_type in type_mapping[key]:
                    target_graph.add((dt_url, RDF.type, item_type))

                dt_same_as = get_text_from_tree(dt_item, ref[2], ns_pfx, ns)
                if dt_same_as and uritools.is_valid_uri(dt_same_as):
                    target_graph.add((dt_url, SDO.sameAs, URIRef(dt_same_as)))

def make_statistics_from_string(xml: str) -> dict[str, int]:
    tree = ET.fromstring(xml)    
    return make_statistics(tree, True)

def make_statistics(tree: Any, check_text=False) -> dict[str, int]:
    stats = {
        'total_files_processed': 0
    }
    for elem in tree.iter():
        if check_text:
            text_present = (elem.text != None and elem.text.strip() != '')
            has_children = len(list(elem))
            if not (text_present or has_children > 0): continue
        if elem.tag in stats:
            stats[elem.tag] = stats[elem.tag] + 1
        else:
            stats[elem.tag] = 1
    return stats

def combine_stats(base: dict[str, int], addition: dict[str, int]) -> dict[str, int]:
    for key in addition:
        if key in base:
            base[key] = base[key] + 1
        else:
            base[key] = 1
    return base

def print_stats(base: dict[str, int]):
    sorted_stats = dict(sorted(base.items(), key=lambda item: item[1]))
    for key in sorted_stats:
        if key == 'total_files_processed': continue
        percentage = (sorted_stats[key] / sorted_stats['total_files_processed']) * 100
        logger.info('Element %s occurred %i times (%i%%)', key, sorted_stats[key], percentage)