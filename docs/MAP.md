# The map of the realms

The map of the app is drawn from two things: the static data of the
realms (`data/realms.json`) and the vendored ground of the map
(`app/static/map/geometry.json`). Nothing is fetched while the page is
drawn, and no picture of a fantasy map was copied: the ground of the map
is the real geography of Great Britain, taken from public-domain data.

## The data of the realms

`data/realms.json` holds the fourteen realms of the map and the hidden
one. Every realm has:

- `key` — the neutral English name that the code and the database use;
- `name_fa`, `name_en` — the name of the realm in Persian and in English;
- `legend_fa` — the note that tells the legend of the realm;
- `coverage_fa`, `coverage_en` — the ground the realm covers;
- `themes` — the words that describe the craft of the realm; the AI
  reads them when it suggests a realm for a domain;
- `adjacent` — the realms that touch it. The list is symmetric: if a
  realm touches another, the other touches it back;
- `start` — the realm every user begins with (`dumnonia`);
- `hidden` — the realm that stays closed until the order of the scholar
  is earned (`lyonesse`).

## The ground of the map

The ground comes from [Natural Earth](https://www.naturalearthdata.com/),
whose data is in the public domain. The processing was done once, on the
machine of the developer, and the result is committed with the code.

### The sources

- `ne_10m_admin_1_states_provinces` — the counties and the unitary
  authorities of Great Britain;
- `ne_10m_admin_0_countries` — the outline of the United Kingdom, of
  which the biggest ring (Great Britain) is the coast of the map.

Both are downloaded from `naciscdn.org/naturalearth/10m/cultural/`.

### The steps

1. **The counties.** Every county of England, Wales and Scotland is
   given to the realm it belongs to. The list is in the script below;
   the English Midlands and the home counties go to `mercia`, the
   Scottish Lowlands to `hadrian_wall` and everything north of the
   Forth-Clyde line to `caledonia`.
2. **The projection.** An equirectangular projection with the standard
   parallel at 54.5° N: `x = lon · cos(54.5°)`, `y = −lat`. The map of
   Britain is small, so the distortion of the projection is smaller
   than the mistake of the hand-drawn borders.
3. **The simplification.** Every ring is thinned with the
   Douglas-Peucker algorithm (a tolerance of 1.1 units for the counties
   and 1.6 for the coast). The rings keep their shape and lose their
   needless points.
4. **The hidden realm.** `lyonesse` is not on the land: it is drawn by
   hand as a small ring west of Cornwall.
5. **The result.** The paths and the anchors (the middle of every
   realm, where its castles and its name are drawn) are written to
   `app/static/map/geometry.json`.

### The script

The script is not part of the app and the app never runs it. It is kept
here so the map can be made again when the data or the borders change:

```python
import json, math, shapefile  # shapefile: the pyshp package

ADMIN1 = "ne_10m_admin_1_states_provinces.shp"
ADMIN0 = "ne_10m_admin_0_countries.shp"
LAT0, SCALE, PADDING = 54.5, 120.0, 12.0

REALM_COUNTIES = {
    "dumnonia": ["Cornwall", "Devon"],
    "avalon": ["Somerset", "Bath and North East Somerset"],
    # ... the rest of the realms; see the list in the paragraph above
}
```

The steps of the script are: read the shapefile, keep the counties of
Great Britain, project the points, thin every ring, write the paths and
the anchors as JSON.

## What is an approximation

The counties are real, and the borders between the realms are the
borders of the counties. What is an approximation is the choice of the
counties that stand for a realm: a realm is a story, and the story
covers more or less ground than the county that carries it. The
legend of every realm says what it covers, so the map and the legend
never disagree.

The outline of the coast is the outline of Natural Earth at the 1:10m
scale, thinned. It is good enough to recognise the island and it is
not a survey.

## The rules of the map

- A realm is given to a domain by the user, never by hand in the
  database.
- A realm may only be taken next to a realm that is already assigned or
  claimed. The map begins with the start realm, which is the only
  exception.
- Every counted medal of the domain lights the next castle of its
  realm. The third castle claims the realm.
- The hidden realm stays closed until the order of the scholar is
  earned.
- The states of the map are read from the database: `fog`, `progress`,
  `claimed` and `hidden`.
