from collections import defaultdict
from django.shortcuts import render
from django.http import Http404, HttpResponse

from .models import *

def province_density_test(request, province):
    """
    Find the population density for each municipality in a province.
    Area in data is given in square meters, but result is in square kilometers for nicer output.
    Args:
        request (HttpRequest): Django request object.
        province (str): Name of the province to lookup.
    Raises:
        Http404: If he province doesn't exist.
    Returns:
        HttpResponse with the resulting population density per municipality and total or a 404 if it doesn't exist.
    """
    try:
        catalog = Catalog.objects.get(catalog_name="Census-ES-2011")
        province_data = DataStore.objects.filter(catalog=catalog, data__npro=province)
        muni_data = defaultdict(list)
        muni_names = set()
        for census_block in province_data:
            municipality = census_block.data["nmun"]
            muni_names.add(municipality)
            population = census_block.data["t1_1"]
            area = census_block.parent_geometry.metadata["area"]
            muni_data[municipality] += [(population, area)]
        results = ""
        # Note that this sorting is not smart enough to do Spanish names properly.
        muni_names = sorted(list(muni_names))
        for name in muni_names:
            muni_blocks = muni_data[name]
            muni_pop = [int(x[0]) for x in muni_blocks]
            muni_area = [x[1] for x in muni_blocks]
            density = round(sum(muni_pop) / (sum(muni_area) / 1000000), 3)
            results += f"{name} : {density}<br />"
        return HttpResponse(f"Population density by municipalities of {province}. Density is people/square km.<br /><br />{results}")
    except Exception:
        raise Http404(f"Province {province} does not exist.")

def province_university_test(request, count):
    """
    Returns a list of the top provinces, ordered by the percentage of the population who has completed university (3rd level studies).
    Results are given to two decimal places.
    Args:
        request (HttpRequest): Django request object.
        count (int): count of the top provinces to show.    
    Raises:
        Http404: If the count is incorrect.    
    Returns:
        HttpResonse object containing the results. Each result is the province name and the percentage.
    """
    catalog = Catalog.objects.get(catalog_name="Census-ES-2011")
    all_data = DataStore.objects.filter(catalog=catalog)
    province_population = defaultdict(list)
    province_university = defaultdict(list)
    # Start by aggregating population and number of university educated people per province.
    for e in all_data:
        province_name = e.data["npro"]
        # '' in the data is treated as 0.
        try:
            population = int(e.data["t1_1"])
        except ValueError:
            population = 0
        # See note in the readme about this. tl;dr: The source data is inconsistent.
        # This means to ignore that regions from the shapefile that don't have associated full data.
        except KeyError:
            continue
        try:
            university = int(e.data["t12_5"])
        except ValueError:
            univercity = 0
        province_population[province_name] += [population]
        province_university[province_name] += [university]
    # After aggregating population and university educated people, get the total of them and find percentage per province.
    results = {}
    for prov in province_population.keys():
        total_population = sum(province_population[prov])
        total_university = sum(province_university[prov])
        results[prov] = round((total_university / total_population) * 100, 2)
    # Sort highest to lowest and take top n (n=count).
    results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    results = results[ : int(count)]
    output = ""
    for idx, res in enumerate(results):
        k, v = res
        output += f"{k}: {v}%<br />"        
    return HttpResponse(f"{output}")


def find_problem_entries(request):
    """
    Finds the DataStore entries that were in the shapefile, but not in the CSVs.
    Args:
        request (HttpRequest): Django request object.
    Returns:
        HttpResonse object containing a list of the DataStore entries missing data and useful data to figure out which they are.
    """
    catalog = Catalog.objects.get(catalog_name="Census-ES-2011")
    all_data = DataStore.objects.filter(catalog=catalog)
    missing_data = ""
    for x in all_data:
        # One with data from just the shapefile is 17 entries, with the CSV data should be 162
        if len(x.data) == 17:
            raw = f"ccaa: {x.data['ccaa']}, cpro: {x.data['cpro']}, cmun: {x.data['cmun']}, dist: {x.data['dist']}, secc: {x.data['secc']}"
            missing_data += f"id: {x.id}, province: \"{x.data['npro']}\", autonomous community: \"{x.data['nca']}\", municipality: \"{x.data['nmun']}\"<br />"
            missing_data += f"raw: ({raw})<br /><br />"
    return HttpResponse(missing_data)
