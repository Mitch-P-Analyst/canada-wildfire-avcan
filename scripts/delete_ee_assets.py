# ===================================================================
# Introduciton
# ===================================================================
# Optional script to delete Google EE assets. Therefore ability to rerun other pipeline scripts 
# (Scripts will not overwrite already existing assets) 

# ===================================================================
# Imports
# ===================================================================
import ee

# ===================================================================
# Google EE Initialize
# ===================================================================
ee.Initialize(project="wildfire-canada-475322")


# ===================================================================
# Constants
# ===================================================================
FOLDER = "projects/wildfire-canada-475322/assets/AvCan_Wildfire_Explorer/Stage_A2"
ONLY_PREFIX = None            # e.g., "Stage_A2_" to restrict; set None to delete all TABLEs

# ===================================================================
# Function
# ===================================================================
def purge_tables(folder: str, only_prefix: str | None = None) -> None:
    """
    Docstring for purge_tables
    
    :param folder: Google EE folder destination
    :param only_prefix: Specific prefix for deletion
    """
    deleted = 0
    page_token = None

    while True:
        req = {"parent": folder}
        if page_token:
            req["pageToken"] = page_token

        resp = ee.data.listAssets(req)
        assets = resp.get("assets", [])

        for a in assets:
            if a.get("type") != "TABLE":
                continue

            name = a["id"].split("/")[-1]
            if only_prefix and not name.startswith(only_prefix):
                continue

            ee.data.deleteAsset(a["id"])
            deleted += 1
            print("Deleted:", a["id"])

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Deleted {deleted} TABLE assets from {folder}")

purge_tables(FOLDER, ONLY_PREFIX)
