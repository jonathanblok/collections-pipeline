from rdflib.namespace import SDO, XSD
from rdflib import RDF, Literal, URIRef
import xpaths
import endpoint 

## Class definition
#CLASS = {
#    'contstants': {},
#    'literals': {},
#    'classes': {},
#}

# mapping voor record object
RECORD = {
    'constants': [
        (RDF.type, SDO.CreativeWork),
        (SDO.isPartOf, endpoint.DATASET_URI),
    ],
    'literals': [
        (SDO.name, xpaths.TITLE_TEXT),
        (SDO.alternateName, xpaths.OBJECT_NAME_ITEM),
        (SDO.publisher, xpaths.INSTITUTION_NAME),
        (SDO.alternateName, xpaths.OBJECT_NAME_ITEM),
        (SDO.temporal, xpaths.PRODUCTION_DATE_END),
        (SDO.license, xpaths.RIGHTS_TYPE),
        (SDO.description, xpaths.DESCRIPTION_TEXT),
        (SDO.copyrightHolder, xpaths.RIGHTS_HOLDER),
        (SDO.creditText, xpaths.RIGHTS_NOTES),
        (SDO.dateCreated, xpaths.PRODUCTION_DATE_END),
        (SDO.temporal, xpaths.PRODUCTION_DATE_END),
        (SDO.size, xpaths.DIMENSION_FREE),
    ],
    'classes': [
        (SDO.creator, {
            'constants': [
                (RDF.type, SDO.Person),
            ],
            'literals': [
                (SDO.name, [xpaths.CREATOR_NAME, Literal, XSD.string]),
                (SDO.sameAs, [xpaths.RKDARTISTS, Literal, XSD.anyURI]),
                (SDO.deathDate, [xpaths.CREATOR_DATE_OF_DEATH, Literal, XSD.string]),
                (SDO.birthDate, [xpaths.CREATOR_DATE_OF_BIRTH, Literal, XSD.string]),
            ],
            'classes': {
                (SDO.birthPlace, {
                    'contstants': [],
                    'literals': [],
                    'classes': [],
                }),
                SDO.hasOccupation: {
                    'contstants': [
                        RDF.type: SDO.Occupation,
                        RDF.type: SDO.DefinedTerm,
                    ],
                    'literals': {
                        SDO.name: [xpaths.CREATOR_ROLE_NAME, Literal, XSD.string],
                        SDO.sameAs: [xpaths.CREATOR_ROLE_URI, Literal, XSD.anyURI],
                    },
                    'classes': {},
                },
            },
        }),
        (SDO.material, {
            'contstants': {
                RDF.type: SDO.Product,
                RDF.type: SDO.DefinedTerm,
            },
            'literals': {
                SDO.name: [xpaths.MATERIAL_TERM, Literal, XSD.string],
                SDO.sameAs: [xpaths.MATERIAL_SRC_URI, Literal, XSD.anyURI],
            },
            'classes': {},
        }),
        (SDO.associatedMedia, {
            'constants': {
                RDF.type: SDO.MediaObject,
                SDO.license: Literal('https://rightsstatements.org/page/InC/1.0/?language=nl', datatype=XSD.anyURI),
            },
            'literals': {
                SDO.contentUrl: xpaths.REPRODUCTION_REFERENCE,
            }, 
            'classes': {
                SDO.encodesCreativeWork: URIRef(RECORD),
                SDO.copyrightHolder: xpaths.RIGHTS_HOLDER,
            }, 
        }),
        (SDO.identifier, {
            'contstants': {
                RDF.type: SDO.PropertyValue,
                SDO.propertyID: Literal('https://documentation.axiell.com/alm/en/index.html?ds_eiefxml.html', datatype=XSD.anyURI),
                SDO.description: Literal('AdlibXML object_number')
            },
            'literals': {
                SDO.value: [xpaths.OBJECT_NUMBER, Literal, XSD.string],
            },
            'classes': {},
        }),
        (SDO.locationCreated, {
            'contstants': {},
            'literals': {},
            'classes': {},
        }),
        (SDO.genre, {
            'contstants': {
                RDF.type: SDO.DefinedTerm,
            },
            'literals': {
                SDO.name: [xpaths.OBJECT_CATEGORY_TERM, Literal, XSD.string],
                SDO.sameAs: [xpaths.OBJECT_CATEGORY_SRC_URI, Literal, XSD.anyURI],
            },
            'classes': {},
        }),
        (SDO.keywords, {
                    RDF.type: SDO.Product,
            'contstants': {
                    RDF.type: SDO.DefinedTerm,
                },
                'literals': {
                    SDO.name: [xpaths.ASSOCIATION_SUBJECT_TERM, Literal, XSD.string],
                    SDO.sameAs: [xpaths.ASSOCIATION_SUBJECT_SRC_URI, Literal, XSD.anyURI],
                },
                'classes': {},
        }),
    ],
}