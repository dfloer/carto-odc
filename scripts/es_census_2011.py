import argparse
import csv
import django
import os
import sys
import requests
import zipfile
import xlrd
from os import path
from django.contrib.gis.gdal import DataSource, SpatialReference, CoordTransform, OGRGeometry, OGRGeomType
from django.contrib.gis import geos

from catalog.models import *

def file_downloader(census_url, description_url, geometry_url, save_dir):
    """
    Downloads the three files needed to populate the database and saves them.
    If the files already exist in the path to save the files, it doesn't download them again.
    Args:
        census_url (str): Full URL for the census data to download.
        description_url (str): Full URL for the census data description to download.
        geometry_url (str): Full URL for the geometry data to download.
        save_dir (path): Path to the location to save the files to.
    Returns:
        True if all files downloaded correctly, False otherwise.
    """
    try:
        census_path = path.join(save_dir, "census.tmp")
        if not path.isfile(census_path):
            census_request = requests.get(census_url, allow_redirects=True)
            with open(census_path, "wb") as f:
                f.write(census_request.content)

        description_path = path.join(save_dir, "description.tmp")
        if not path.isfile(description_path):
            description_request = requests.get(description_url, allow_redirects=True)
            with open(description_path, "wb") as f:
                f.write(description_request.content)

        geometry_path = path.join(save_dir, "geometry.tmp")
        if not path.isfile(geometry_path):
            geometry_request = requests.get(geometry_url, allow_redirects=True)
            with open(geometry_path, "wb") as f:
                f.write(geometry_request.content)
    except Exception:
        return False
    return True

def open_temp_files(temp_files_path):
    """
    Unzips the temp files into the same directory.
    Args:
        temp_files_path (path): path to the directory the downloaded temp files are in.
    Returns:
        Dictionary where the key is the source filename, and the value is a list of individual filenames produced.
    """
    temp_names = ["census.tmp", "geometry.tmp"]
    res = {}
    for t in temp_names:
        p = path.join(temp_files_path, t)
        with zipfile.ZipFile(p, 'r') as zip_file:
            decompressed_files = list(zip_file.namelist())
            res[t] = decompressed_files
            zip_file.extractall(temp_files_path)
    return res

def make_friendly_mapping(description_xlsx_path, catalog, extra={}):
    """
    Convert the description .xlsx file to a SpanishCensusMapping model so we can have nice mappings for all the hstore fields.
    Args:
        description_xlsx_path (path): Path to the xlsx file to open.
        catalog (Catalog): catalog to associate this with.
    """
    wb = xlrd.open_workbook(description_xlsx_path)
    s = wb.sheet_by_index(1)
    # I'd prefer this not to be hard-coded, but xlsx files suck to work with programatically.
    friendly_names = {}
    for k, v in [s.row_values(x) for x in range(8, 153)]:
        friendly_names[k] = v
    for k, v in extra.items():
        friendly_names[k] = v
    fn = FriendlyName(catalog=catalog, mapping=friendly_names)
    fn.save()

def import_geodata(data_files, data_path, catalog):
    """
    Imports the geospatial data into the database.
    Note, in the case of this data, there's data attached to the multipolygon that we want in the datastore.
    Will also convert Polygons to MulitPolygons.
    Not idempotent! (get_or_create doesn't really work with geometry objects.)
    Args:
        data_files (list(str)): List of source files.
        data_path (path): Path to the source files.
        catalog (Catalog): Catalog that this geodata belongs to.
    """
    geometry_data_mapping = {
        'CUSEC': 'cusec',
        'CUMUN': 'cumun',
        'CSEC': 'secc',
        'CDIS': 'dist',
        'CMUN': 'cmun',
        'CPRO': 'cpro',
        'CCA': 'ccaa',
        'CUDIS': 'cudis',
        'OBS': 'obs',
        'CNUT0': 'cnut0',
        'CNUT1': 'cnut1',
        'CNUT2': 'cnut2',
        'CNUT3': 'cnut3',
        'CLAU2': 'clau2',
        'NPRO': 'npro',
        'NCA': 'nca',
        'NMUN': 'nmun'}
    metadata_map = {"OBJECTID": "obj_id", "Shape_len": "perimeter", "Shape_area": "area",}
    ignore = ["Shape_Leng"]
    field_skip = list(metadata_map.keys()) + ignore
    metadata_skip = list(geometry_data_mapping.keys()) + ignore

    shp = [s for s in data_files if ".shp" == s[-4 :]][0]
    shape_file = path.join(data_path, shp)
    ds = DataSource(shape_file)
    layer = ds[0]
    fields = layer.fields
    source_srid = SpatialReference(layer.srs.srid)
    our_srid = SpatialReference(4326)
    transform = CoordTransform(source_srid, our_srid)

    for shape in layer:
        geom = shape.geom
        geom.transform(transform)
        field_data = {geometry_data_mapping[k]: shape.get(v) for k, v in zip(fields, range(len(fields))) if k not in field_skip}
        metadata = {metadata_map[k]: shape.get(v) for k, v in zip(fields, range(len(fields))) if k not in metadata_skip}
        # Normalise all Polygons to Multipolygons for ease of use later.
        if geom.geom_type.name == "Polygon":
            mp = OGRGeometry(OGRGeomType('MultiPolygon'))
            mp.add(geom)
            geom = mp
        g = GeometryStore(catalog=catalog, geom=geom.geos, metadata=metadata)
        g.save()
        d = DataStore(catalog=catalog, parent_geometry=g, data=field_data)
        d.save()

def import_census_data(data_files, data_path, catalog):
    """
    Imports the census data into the DataStore.
    Args:
        data_files (list(str)): List of source files.
        data_path (path): Path to the source files.
        catalog (Catalog): Catalog that this geodata belongs to.
    """
    for f in data_files:
        file_path = path.join(data_path, f)
        with open(file_path) as csv_file:
            data_reader = csv.reader(csv_file)
            header = next(data_reader, None)
            for row in data_reader:
                parse_row = census_data_parse_row(row, header)
                # Because JSONField is schemaless, we need to enforce our own schema here.
                ccaa = parse_row["ccaa"].zfill(2)
                cpro = parse_row["cpro"].zfill(2)
                cmun = parse_row["cmun"].zfill(3)
                dist = parse_row["dist"].zfill(2)
                secc = parse_row["secc"].zfill(3)
                existing_datastore_entry = DataStore.objects.get(
                    data__ccaa=ccaa, data__cpro=cpro, data__cmun=cmun, data__dist=dist, data__secc=secc)
                # We know that the only entries that overlap between the two dictionaries are exact as we just used them for the lookup.
                new_data = {**existing_datastore_entry.data, **parse_row}
                existing_datastore_entry.data = new_data
                existing_datastore_entry.save()

def census_data_parse_row(raw_row, row_header):
    """
    Parses a raw row of census data into a list representing the data for the model.
    Args:
        raw_row (list(str)): Raw data as a list of strings in the same order as the CSV.
        row_header (list(str)): Header information from the CSV.
    Returns:
        A dictionary where the key is the columns header, and the data is the data for that row.
    """
    return {h: e for h, e in zip(row_header, raw_row)}
    
def create_catalog(catalog_name, catalog_description):
    """
    Creates a catalog to store this data in.
    Args:
        catalog_name (str): short name for the catalog. This must be unique per catalog!
        catalog_description (str): Nice description of a catalog.
    """
    catalog = Catalog.objects.get_or_create(catalog_name=catalog_name, defaults={'catalog_description': catalog_description})
    return catalog[0]

def run(description_url, census_url, geometry_url, temp_dir='.'):
    
    CATALOG_NAME = "Census-ES-2011"
    CATALOG_DESCRIPTION = "Data for the 2011 Spanish Census."

    other_friendly = {
        "ccaa": "Census Area",
        "cpro": "Province",
        "cmun": "Municipality",
        "dist": "district",
        "secc": "Socio-Economic Cast",
        "npro": "Province Name",
        "nca": "Autonomous Community Name",
        "nmun": "Municipality Name",}

    res = file_downloader(census_url, description_url, geometry_url, temp_dir)
    if not res:
        print("File downloading failed.")
    else:
        data_files = open_temp_files(temp_dir)
        description_path = path.join(temp_dir, "description.tmp")
        catalog = create_catalog(CATALOG_NAME, CATALOG_DESCRIPTION)
        make_friendly_mapping(description_path, catalog, other_friendly)
        import_geodata(data_files["geometry.tmp"], temp_dir, catalog)
        import_census_data(data_files["census.tmp"], temp_dir, catalog)
