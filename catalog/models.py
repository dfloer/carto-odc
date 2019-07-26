from django.contrib.gis.db import models
from django.contrib.postgres.fields import HStoreField, JSONField


class Catalog(models.Model):
    """
    Stores metadata for each data catalog. There should be one entry here per dataset.
    """
    catalog_name = models.TextField(primary_key=True)
    catalog_description = models.TextField()

    def __str__(self):
        return(f"{self.catalog_name}: {self.catalog_description}")


class FriendlyName(models.Model):
    """
    Maps a non-descrivptive data field name to a nice, easy to read name.
    """
    catalog = models.ForeignKey(Catalog, on_delete=models.PROTECT)
    mapping = HStoreField()

    def __str__(self):
        return(str(self.mapping))


class MultiPolygonStore(models.Model):
    """
    Stores a multipolygon.
    """
    catalog = models.ForeignKey(Catalog, on_delete=models.PROTECT)
    geom = models.MultiPolygonField(geography=True, srid=4326)
    # Why not put this in the DataStore? Because this should be used for data connected directly to the polygon.
    # For example, if the original datasource has area already calculated, store that here.
    # To reiterate, this shouldn't be used to what's inside the geometry, but the geometry itself.
    metadata = JSONField()

    def __str__(self):
        return(f"id: {self.id}, metadata items: {len(self.metadata)}")


class DataStore(models.Model):
    """
    Stores all of the data related to a piece of geometry.
    """
    catalog = models.ForeignKey(Catalog, on_delete=models.PROTECT)
    parent_geometry = models.ForeignKey(MultiPolygonStore, on_delete=models.PROTECT)
    data = JSONField()

    def __str__(self):
        return f"id: {self.id}, catalog: {self.catalog.catalog_name}, geom: {self.parent_geometry.id}, items: {len(self.data)}"
