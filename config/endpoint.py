### Linked Data ### 
# base uri voor linked data, nodes worden op basis van deze uri opgebouwd 
BASE_URI = 'https://linkeddata.cultureelerfgoed.nl/'
# COLLECTION_ID is de gebruikte suffix voor de URIs
COLLECTION_ID = 'rce/rijkscollectie-rce'

### Adlib API ###
# API endpoint
SRC_URI = 'https://rcerijswijk.adlibhosting.com/api.wo2/oai.ashx'
# naam van database in Adlib
SRC_DB = 'ruben_s'
# records per pagina, 100 is het meest consistent
SRC_API_LIMIT = 100
# metadataprefix
SRC_PFX = 'kc_rs'

### Toegestane waardes om link naar afbeelding te tonen ###
RIGHTS_ASSIGNED_ALLOWLIST = ['NOPMB', 'PICTORIGHT', 'YES']

### Organisatie ###
# isPartOf referentie naar dataset waar de records deel van uitmaken
DATASET_URI = 'https://linkeddata.cultureelerfgoed.nl/rce/datacatalog/id/dataset/db6193aa-84af-3edf-90fd-074a0a11248d'
