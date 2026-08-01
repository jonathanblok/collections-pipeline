from rdflib.namespace import SDO, XSD
from rdflib import RDF, Literal, URIRef, Node
import xpaths
import endpoint 

def get_mapping() -> dict[str, list[tuple[URIRef, URIRef] | tuple[URIRef, list[str, Node, URIRef]] | ]]]:
    return CLASS

## Class definition
CLASS = {
    'contstants': [
        (RDF.type, SDO.CreativeWork),
    ],
    'literals': [
        (SDO.name, xpaths.OBJECT_NAME_ITEM),
    ],
    'classes': [],
}