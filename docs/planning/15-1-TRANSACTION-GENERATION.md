# Helpfull Snippets


## Get top venues in Munich

We want to focus our mvp on munich

```
# pip install overpy
import overpy
import pandas as pd

def get_munich_venues():
    api = overpy.Overpass()
    
    # Overpass QL query: Search for bars, cafes, and restaurants in Munich
    # We use a bounding box roughly around Munich city center
    query = """
    [out:json][timeout:25];
    area["name"="München"]->.searchArea;
    (
      node["amenity"="bar"](area.searchArea);
      node["amenity"="cafe"](area.searchArea);
      node["amenity"="restaurant"](area.searchArea);
    );
    out body;
    """
    
    print("Fetching venues from OpenStreetMap...")
    result = api.query(query)
    
    venues = []
    for node in result.nodes:
        name = node.tags.get("name", "Unknown")
        if name != "Unknown":
            venues.append({
                "merchant_id": f"MID_{node.id}", # We will use the OSM ID as our Payone MID
                "name": name,
                "type": node.tags.get("amenity", "unknown"),
                "lat": float(node.lat),
                "lon": float(node.lon)
            })
            
    df = pd.DataFrame(venues)
    print(f"Found {len(df)} venues!")
    
    # If you just want a mock "Top 100", you can randomly sample or sort them alphabetically for now
    top_100 = df.sample(100) 
    return top_100

munich_venues = get_munich_venues()
print(munich_venues.head())
```

## Human prepared typical business information per sector

I will get the info for the top x businesses from the top venue list.


