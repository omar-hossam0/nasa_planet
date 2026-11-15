# Map context assets

`africa-blue-marble.jpg`: NASA GIBS, BlueMarble_ShadedRelief_Bathymetry. Static visual context, not current observations and not used to calculate trends. WMS 1.1.1 / EPSG:4326, bounds -40,-20,70,50, 1600 x 1018 pixels. Retrieved 2026-11-15.

https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi

`world-countries.geojson`: Natural Earth 1:110m admin-0 country boundaries (public domain), distributed by nvkelso/natural-earth-vector.

https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson

The map uses a geographic linear projection and places each NASA trend raster over its returned bounding box. Geographic context does not increase the scientific resolution of that raster.

`expedition-landscape.png`: AI-generated decorative landscape, not Earth observation data.

`earth-horizon-footer.png`: AI-generated decorative Earth horizon used behind the landing evidence and closing sections; not a geographic map or scientific observation.
