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
    Args:
        request (HttpRequest): Django request object.
        count (int): count of the top provinces to show.    
    Raises:
        Http404: If the count is incorrect.    
    Returns:
        HttpResonse object containing the results. Each result is the province name and the percentage.
    """
    pass

