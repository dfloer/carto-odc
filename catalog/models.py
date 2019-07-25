from django.contrib.gis.db import models
from django.contrib.postgres.fields import HStoreField, JSONField


class Catalog(models.Model):
    """
    Stores metadata for each data catalog. There should be one entry here per dataset.
    """
    catalog_name = models.TextField()
    catalog_description = models.TextField()
    field_friendly_name = models.ForeignKey('FriendlyName', on_delete=models.CASCADE)



class FriendlyName(models.Model):
    """
    Maps a non-descrivptive data field name to a nice, easy to read name.
    """
    mapping = HStoreField()

    def __str__(self):
        return(str(self.mapping))


class MultiPolygonStore(models.Model):
    """
    Stores a multipolygon.
    """
    geom = models.MultiPolygonField(srid=4269)


class DataStore(models.Model):
    """
    Stores all of the data related to a piece of geometry.
    """
    catalog = models.ForeignKey(Catalog, on_delete=models.PROTECT)
    parent_geometry = models.ForeignKey(MultiPolygonStore, on_delete=models.PROTECT)
    data = JSONField()
