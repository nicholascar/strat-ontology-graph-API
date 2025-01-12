from .functions import query_graphdb_endpoint, get_resource
from .config import GEOM_DATA_SVC_ENDPOINT
import requests

def find_at_location(lat, lon, feature_type="any", crs=4326, count=1000, offset=0):
    """
    This function finds geometries for a given lat-long coord. 
    It then queries the graphDB to get related features based on 
    apriori known datatype relationships with the geometry of the features.
    :param lat:
    :type lat: float
    :param lon:
    :type lon: float
    :param crs:
    :type crs: int
    :param count:
    :type count: int
    :param offset:
    :type offset: int
    :return:
    """
    row = {}
    results = {}
    counter = 0
    params = {
       "_format" : "application/json",
       "crs": crs
    }
    headers = {
       "Accept" : "application/json"
    }
    formatted_resp = {
        'ok': False
    }
    http_ok = [200]
    if feature_type == 'any':
       search_by_latlng_url = GEOM_DATA_SVC_ENDPOINT + "/search/latlng/{},{}".format(lon,lat)
    else:
       search_by_latlng_url = GEOM_DATA_SVC_ENDPOINT + "/search/latlng/{},{}/dataset/{}".format(lon, lat, feature_type)
    try:
        resp = requests.get(search_by_latlng_url, params=params, headers=headers)
        if resp.status_code not in http_ok:
            formatted_resp['errorMessage'] = "Could not connect to the geometry data service at {}. Error code {}".format(GEOM_DATA_SVC_ENDPOINT, resp.status)
            return formatted_resp
        formatted_resp = resp.json()
        formatted_resp['ok'] = True
    except:
        formatted_resp['errorMessage'] = "Could not connect to the geometry data service at {}. Error thrown.".format(GEOM_DATA_SVC_ENDPOINT)
        return formatted_resp
    r = formatted_resp['res']
    del(formatted_resp['res'])
    meta = formatted_resp
    meta['offset'] = offset

    #query triple store for the features with input geom
    for geom_res in r:
       arrFeatures = fetch_feature_for_geom(geom_res['geometry'], geom_res['id'],  geom_res['dataset'])
       geom_res['feature'] = arrFeatures

    returned_resp = { "meta" : meta, "results": r }
    return returned_resp, 200

def fetch_feature_for_geom(geom_uri, local_id, dataset, limit=1000, offset=0):
   arr_features = []
   the_geom_uri = geom_uri
   if dataset == 'province':
      #A Province has the geometry. A StratUnit hasRelation with Province
      #So for now return both
      ### TODO: Replace the following hacky solution
      #the_geom_uri = geom_uri  ##Commenting this out for when the geom uri is stable. 
      #use the id for now and build a URI
      the_geom_uri = "https://gds.loci.cat/geometry/province/p{}".format(local_id)
   sparql = """\
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
select ?feature where {{ 
    ?feature geo:hasGeometry <{g_uri}> .
}}
""".format(g_uri=the_geom_uri)
   resp = query_graphdb_endpoint(sparql, limit=limit, offset=offset)
   if 'results' not in resp:
      return resp_object
   bindings = resp['results']['bindings']
   for b in bindings:
      arr_features.append(b['feature']['value'])
   return arr_features

def find_stratunit_at_location(lat, lon, crs=4326, count=1000, offset=0):
    """
    This function finds geometries for a given lat-long coord. 
    It then queries the graphDB to workout which stratunits match based on 
    apriori known datatype relationships with the geometry of the features.
    :param lat:
    :type lat: float
    :param lon:
    :type lon: float
    :param crs:
    :type crs: int
    :param count:
    :type count: int
    :param offset:
    :type offset: int
    :return:
    """
    row = {}
    results = {}
    counter = 0
    params = {
       "_format" : "application/json",
       "crs": crs
    }
    headers = {
       "Accept" : "application/json"
    }
    formatted_resp = {
        'ok': False
    }
    http_ok = [200]
    search_by_latlng_url = GEOM_DATA_SVC_ENDPOINT + "/search/latlng/{},{}".format(lon,lat)
    try:
        resp = requests.get(search_by_latlng_url, params=params, headers=headers)
        if resp.status_code not in http_ok:
            formatted_resp['errorMessage'] = "Could not connect to the geometry data service at {}. Error code {}".format(GEOM_DATA_SVC_ENDPOINT, resp.status)
            return formatted_resp
        formatted_resp = resp.json()
        formatted_resp['ok'] = True
    except:
        formatted_resp['errorMessage'] = "Could not connect to the geometry data service at {}. Error thrown.".format(GEOM_DATA_SVC_ENDPOINT)
        return formatted_resp
    r = formatted_resp['res']
    del(formatted_resp['res'])
    meta = formatted_resp
    meta['offset'] = offset

    #query triple store for the features with input geom
    for geom_res in r:
       dict_stratUnits = fetch_stratunit_for_geom(geom_res['geometry'], geom_res['id'],  geom_res['dataset'])
       geom_res['features'] = dict_stratUnits 
       geom_res.pop('feature') 

    returned_resp = { "meta" : meta, "results": r }
    return returned_resp, 200

def fetch_stratunit_for_geom(geom_uri, local_id, dataset, limit=1000, offset=0):
   the_geom_uri = geom_uri
   arr_features = []
   if dataset != 'province':
      print("Don't know how to handle data that's not a province")
      return []
   #A Province has the geometry. A StratUnit hasRelation with Province
   #So for now return both
   ### TODO: Replace the following hacky solution
   #the_geom_uri = geom_uri  ##Commenting this out for when the geom uri is stable. 
   #use the id for now and build a URI
   the_geom_uri = "https://gds.loci.cat/geometry/province/p{}".format(local_id)
   sparql = """\
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX strat: <http://pid.geoscience.gov.au/def/stratname#>
select ?province ?stratunit where {{
    ?province geo:hasGeometry <{g_uri}> .
    ?stratunit strat:relation ?province . 
    ?stratunit a strat:Unit .
    ?province a strat:Province
}}
""".format(g_uri=the_geom_uri)
   resp = query_graphdb_endpoint(sparql, limit=limit, offset=offset)
   if 'results' not in resp:
      return resp_object
   bindings = resp['results']['bindings']
   dict_features = {}
   for b in bindings:
      curr_province = b['province']['value']
      if curr_province not in dict_features:
         dict_features[curr_province] = []
      dict_features[curr_province].append(b['stratunit']['value'])

   returned_obj = []
   for p in dict_features:
      o = {}
      o['province'] = p
      o['stratunit'] = dict_features[p]
      returned_obj.append(o)
   return returned_obj

