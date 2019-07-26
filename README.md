# carto-odc

Proof-of-concept open data catalog using GeoDjango/PostGIS.

Certain settings, such as allowed_hosts, debug and the secret_key in settings/settings.py will need to be changed for any sort of production usage.

## Requirements

- Python 3.7
- pipenv

## Usage

- Install Python dependencies using `pipenv install`
- Make sure that the system [geospatial library requirements for GeoDjango](https://docs.djangoproject.com/en/dev/ref/contrib/gis/install/#spatial-database) are installed.
- Install [postgis](https://docs.djangoproject.com/en/2.2/ref/contrib/gis/install/postgis/).
- Add [hstore](http://postgresguide.com/cool/hstore.html) to that database.
- Change setting/settings.py [databases](https://docs.djangoproject.com/en/2.2/ref/settings/#databases) section to connect to the Postgresql server.
- Create database schema using `python manage.py migrate`.
- Import the test census data into the app.
  - For example, run:\
  `python manage.py runscript census_import --script-args http://www.ine.es/censos2011_datos/indicadores_seccen_rejilla.xls http://www.ine.es/censos2011_datos/indicadores_seccion_censal_csv.zip http://www.ine.es/censos2011_datos/cartografia_censo2011_nacional.zip scripts/tempdata/`
  - The first URL is the census description URL.
  - The second URL is for the actual census data.
  - The third URL is for the geometry file.
  - The fourth and final argument is the directory to store the temporary downloaded files in.
This will fetch the download data files from the download URLs and load them into the database.
  - **Note:** this loading is not idempotent.
- To manually check if the data imported correctly:
  - Create a superuser and follow the prompts from: `python manage.py createsuperuser`
  - Start the local testing server: `python manage.py runserver`
  - Go the the server in a browser and log in using the created username and password. The data and geometry models are visible and the data can be browsed.

## Notes

- There is a small irregularity in the datafiles I downloaded for the 2011 Spanish Census. The shapefile has 35960 different entries, but there are only a total of 35917 data entries in the CSVs. These are discounted in the tests, otherwise they produce issues.
- The same data refers to Gipuzcoa and Gipuzkoa as separate provinces. This is not handled.

## Possible Improvements

- Data is imported as-is into the JSONField. Various fields would be better server by being converted from a string into the integer that string represents.
- Some operations are quite slow due to Django presently (version 2.2.3) using PostgreSQL's json data type and not the jsonb datatype. This could be worked around with raw SQL until Django updates, or a third-party package could be added.
- The FriendlyName model is intended to be used to map a nice name to a key in the JSONField. I haven't implemented this nice lookup.
- Make data loading script idempotent so that it can be stopped and resumed as needed.
- Add a more generic API. This could possibly be implemented as a REST or GraphQL API. GraphQL seems like it could be a good choice.

## Tests

Two test views have been created:

- `catalog/es-census-2011/test1/<province>` where \<province\> is the name of the province to look up. This returns a list of all municipalties in a province and their associated population densities, in people/square km. This is sorted alphabetically, but the sorting isn't correct with accented letters, such as in Spanish.
- `catalog/es-census-2011/test2<count>` where \<count\> is the number of provinces to show results for. This returns a list of all provinces and what percentage of the population that has a university degree, sorted from most to least. **Note:** As Gipuzcoa and Gipuzkoa are treated as separate provinces, this impacts the results of this test. **Note:** As some small census "tracts" are missing data, this impacts the results of this test.
