import os
from pathlib import Path

import fasthtml.common as fh
import googlemaps
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API = os.getenv("GOOGLE_API")
gmaps = googlemaps.Client(key=GOOGLE_API)


BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "imgs"
PDF_DIR = BASE_DIR / "pdfs"
DEFAULT_IMG = "/imgs/default_image.jpg"

db = fh.database("data/test.db")

addresses = db.t.addresses
properties = db.t.properties
warehouses = db.t.warehouses
lands = db.t.lands
offices = db.t.offices
shops = db.t.shops
users = db.t.users
comparisons = db.t.comparisons
warehouse_comparisons = db.t.warehouse_comparisons
land_comparisons = db.t.land_comparisons
shop_comparisons = db.t.shop_comparisons
office_comparisons = db.t.office_comparisons
ppt_images = db.t.ppt_images
ppt_infrastructures = db.t.ppt_infrastructures
cities = db.t.cities
streets = db.t.streets
regions = db.t.regions
districts = db.t.districts
infrastructures = db.t.infrastructures
notes = db.t.notes
tasks = db.t.tasks
task_cities = db.t.task_cities
task_regions = db.t.task_regions
task_districts = db.t.task_districts
task_infrastructures = db.t.task_infrastructures
task_avcbs = db.t.task_avcbs
warehouse_tasks = db.t.warehouse_tasks
land_tasks = db.t.land_tasks
shop_tasks = db.t.shop_tasks
office_tasks = db.t.office_tasks
avcbs = db.t.avcbs
covers = db.t.covers
ppt_pdfs = db.t.ppt_pdfs


class Choice:
    YES = 1
    NO = 2
    BOTH = 3


class Role:
    ADMIN = 1
    USER = 2
    BROKER = 3
    OWNER = 4
    SECRETARY = 5


class AdType:
    RENT = 1
    SELL = 2


class Status:
    ACTIVE = 1
    ARCHIVE = 2
    NEW = 3
    SUSPENDED = 4
    SUCCESS = 5


class PropertyType:
    WAREHOUSE = 1
    LAND = 2
    OFFICE = 3
    SHOP = 4


DATE_FLDS = (
    "start_date",
    "last_update",
    "end_date",
)

CDR_FK = {
    "city_id": cities,
    "region_id": regions,
    "district_id": districts,
}

TSK_MULT_FK = {
    "city_id": task_cities,
    "region_id": task_regions,
    "district_id": task_districts,
    "infr_id": task_infrastructures,
    "avcb_id": task_avcbs,
}

CDRS_FK = {
    **CDR_FK,
    "street_id": streets,
}

USR_DFLT_FLDS = {
    "name": str,
    "email": str,
    "phone": str,
    "organization": str,
}

CNB_FLDS = {
    "cep": str,
    "str_number": int,
    "block": str,
}

ADDRESS_FLDS = {
    **{k: int for k in CDRS_FK},
    **CNB_FLDS,
}

# table fields
PPT_CHOICE_FLDS = (
    "in_conodminium",
    "under_construction",
)
PPT_BOOL_FLDS = (
    *PPT_CHOICE_FLDS,
    "retha_admin",
    "on_site",
)

PPT_COSTS_FLDS = (
    "iptu",
    "condominium",
    "foro",
)

PPT_SLCT_FLDS = ("ppt_type",)

PPT_FLDS = {
    "name": str,
    **{k: bool for k in PPT_BOOL_FLDS},
    **{k: int for k in PPT_SLCT_FLDS},
    "description": str,
    **{k: float for k in PPT_COSTS_FLDS},
}

UNIT_RANGE_FLDS = ("area",)

WH_MD_FLDS = (
    "available",
    "flr_capacity",
    "height",
    "energy",
    "between_pilars",
)

WH_RANGE_FLDS = (
    "flr_capacity",
    "height",
    "office_area",
    "energy",
    "docks",
)

WH_BOOL_FLDS = (
    "under_construction",
    "sprinklers",
    "dock_leveler",
    "refrigeration",
)

UNIT_FK_FLDS = {
    "broker_id": int,
    "owner_id": int,
    "ppt_id": int,
}

RENT_SELL_FLDS = (
    "rent",
    "sell",
)

UNIT_COMMON_FLDS = {
    "title": str,
    "available": str,
    "area": int,
    **{k: int for k in RENT_SELL_FLDS},
}

WH_FLDS = {
    **UNIT_COMMON_FLDS,
    **{k: bool for k in WH_BOOL_FLDS},
    **{k: int for k in WH_RANGE_FLDS},
    "between_pilars": str,
}

TSK_SLC_FLDS = ("ad_type", "ppt_type")

TSK_FK_FLDS = (
    "client_id",
    "broker_id",
)

TSK_RANGE_FLDS = (
    "area",
    "price",
)

TSK_FLDS = {
    **{k: int for k in TSK_FK_FLDS},
    **{k: int for k in TSK_SLC_FLDS},
    # **{k: int for k in CDR_FK},
    "initial_dscr": str,  # initial reqeust
}

U_PARAMS = {
    **{f"{k}_{n}": int for k in TSK_RANGE_FLDS for n in ("min", "max")},
    "under_construction": bool,
}

WH_PARAMS = {
    **{
        f"{k}_{n}": int
        for k in (*WH_RANGE_FLDS, *TSK_RANGE_FLDS)
        for n in ("min", "max")
    },
    **{k: int for k in WH_BOOL_FLDS},
    "between_pilars": str,
}

FK_TABLES = {
    "city_id": cities,
    "region_id": regions,
    "district_id": districts,
    "street_id": streets,
    "adrs_id": addresses,
    "avcb_id": avcbs,
    "ppt_id": properties,
    "user_id": users,
    "author_id": users,
    "task_id": tasks,
    "client_id": users,
    "broker_id": users,
    "owner_id": users,
    "comparison_id": comparisons,
    "shop_id": shops,
    "office_id": offices,
    "land_id": lands,
    "warehouse_id": warehouses,
    "infr_id": infrastructures,
}

PPT_TSK_PARAMS = {
    PropertyType.WAREHOUSE: WH_PARAMS,
    PropertyType.LAND: U_PARAMS,
    PropertyType.OFFICE: U_PARAMS,
    PropertyType.SHOP: U_PARAMS,
}

PPT_TABLE_NAMES = {
    PropertyType.WAREHOUSE: "warehouses",
    PropertyType.LAND: "lands",
    PropertyType.OFFICE: "offices",
    PropertyType.SHOP: "shops",
}


def _initialize_db():
    if users not in db.t:
        users.create(
            **USR_DFLT_FLDS,
            id=int,
            pwd=str,
            role=int,
            pk="id",
        )
        users.create_index(
            ["email"],
            unique=True,
        )
        pwd = os.getenv("ADMIN_PWD")
        email = os.getenv("ADMIN_EMAIL")
        admin = {
            "email": email,
            "pwd": pwd,
            "role": Role.ADMIN,
            "organization": "Retha",
        }
        broker = {
            "name": "broker0",
            "email": "broker0@ya.ru",
            "pwd": pwd,
            "role": Role.BROKER,
            "organization": "Retha",
        }
        secretary = {
            "email": "secretary@ya.ru",
            "pwd": pwd,
            "role": Role.SECRETARY,
            "organization": "Retha",
        }
        users.insert_all(
            [
                admin,
                secretary,
                broker,
            ]
        )
    if properties not in db.t:
        regions.create(id=int, name=str, pk="id")
        cities.create(id=int, name=str, pk="id")
        districts.create(id=int, name=str, pk="id")
        streets.create(id=int, name=str, pk="id")
        infrastructures.create(id=int, name=str, pk="id")
        avcbs.create(id=int, name=str, pk="id")
        addresses.create(
            **ADDRESS_FLDS,
            location=str,
            id=int,
            pk="id",
            foreign_keys=[
                ("city_id", "cities", "id"),
                ("region_id", "regions", "id"),
                ("district_id", "districts", "id"),
                ("street_id", "streets", "id"),
            ],
        )
        properties.create(
            **PPT_FLDS,
            adrs_id=int,
            avcb_id=int,
            pdf_path=str,
            id=int,
            pk="id",
            foreign_keys=[
                ("adrs_id", "addresses", "id"),
                ("avcb_id", "avcbs", "id"),
            ],
        )
        ppt_images.create(
            id=int,
            ppt_id=int,
            cover=bool,
            name=str,
            pk="id",
            foreign_keys=[("ppt_id", "properties", "id")],
        )
        ppt_images.create_index(["ppt_id", "name"], unique=True)
        fk = [
            ("ppt_id", "properties", "id"),
            ("broker_id", "users", "id"),
            ("owner_id", "users", "id"),
        ]
        warehouses.create(
            **WH_FLDS,
            id=int,
            broker_id=int,
            owner_id=int,
            ppt_id=int,
            last_update=int,
            status=int,
            pk="id",
            foreign_keys=fk,
        )
        lands.create(
            **UNIT_COMMON_FLDS,
            id=int,
            broker_id=int,
            owner_id=int,
            ppt_id=int,
            last_update=int,
            status=int,
            pk="id",
            foreign_keys=fk,
        )
        offices.create(
            **UNIT_COMMON_FLDS,
            id=int,
            broker_id=int,
            owner_id=int,
            ppt_id=int,
            last_update=int,
            status=int,
            pk="id",
            foreign_keys=fk,
        )
        shops.create(
            **UNIT_COMMON_FLDS,
            id=int,
            broker_id=int,
            owner_id=int,
            ppt_id=int,
            last_update=int,
            status=int,
            pk="id",
            foreign_keys=fk,
        )
        ppt_infrastructures.create(
            id=int,
            ppt_id=int,
            infr_id=int,
            pk="id",
            foreign_keys=[
                ("ppt_id", "properties", "id"),
                ("infr_id", "infrastructures", "id"),
            ],
        )
        ppt_infrastructures.create_index(
            ["ppt_id", "infr_id"],
            unique=True,
        )
        ppt_pdfs.create(
            id=int,
            name=str,
            ppt_id=int,
            pk="id",
            foreign_keys=[("ppt_id", "properties", "id")],
        )
    if comparisons not in db.t:
        comparisons.create(
            id=int,
            ppt_id=int,
            user_id=int,
            author_id=int,
            ad_type=int,
            status=int,
            date=str,
            pk="id",
            foreign_keys=[
                ("ppt_id", "properties", "id"),
                ("user_id", "users", "id"),
                ("author_id", "users", "id"),
            ],
        )
        warehouse_comparisons.create(
            id=int,
            comparison_id=int,
            unit_id=int,
            pk="id",
            foreign_keys=[
                ("comparison_id", "comparisons", "id"),
                ("warehouse_id", "warehouses", "id"),
            ],
        )
        land_comparisons.create(
            id=int,
            comparison_id=int,
            unit_id=int,
            pk="id",
            foreign_keys=[
                ("comparison_id", "comparisons", "id"),
                ("land_id", "lands", "id"),
            ],
        )
        office_comparisons.create(
            id=int,
            comparison_id=int,
            unit_id=int,
            pk="id",
            foreign_keys=[
                ("comparison_id", "comparisons", "id"),
                ("office_id", "offices", "id"),
            ],
        )
        shop_comparisons.create(
            id=int,
            comparison_id=int,
            unit_id=int,
            pk="id",
            foreign_keys=[
                ("comparison_id", "comparisons", "id"),
                ("shop_id", "shops", "id"),
            ],
        )
    if tasks not in db.t:
        tasks.create(
            **TSK_FLDS,
            id=int,
            start_date=str,
            end_date=str,
            status=int,
            pk="id",
            foreign_keys=[
                ("client_id", "users", "id"),
                ("broker_id", "users", "id"),
            ],
        )
        notes.create(
            id=int,
            task_id=int,
            descripton=str,
            date=str,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
            ],
        )
        task_cities.create(
            id=int,
            task_id=int,
            city_id=int,
            pk="id",
            foreign_keys=[("task_id", "tasks", "id"), ("city_id", "cities", "id")],
        )
        task_regions.create(
            id=int,
            task_id=int,
            region_id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
                ("region_id", "regions", "id"),
            ],
        )
        task_districts.create(
            id=int,
            task_id=int,
            district_id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
                ("district_id", "districts", "id"),
            ],
        )
        task_infrastructures.create(
            id=int,
            task_id=int,
            infr_id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
                ("infr_id", "infrastructures", "id"),
            ],
        )
        task_avcbs.create(
            id=int,
            task_id=int,
            avcb_id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
                ("avcb_id", "avcbs", "id"),
            ],
        )
        warehouse_tasks.create(
            **WH_PARAMS,
            task_id=int,
            id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
            ],
        )
        land_tasks.create(
            **U_PARAMS,
            task_id=int,
            id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
            ],
        )
        shop_tasks.create(
            **U_PARAMS,
            task_id=int,
            id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
            ],
        )
        office_tasks.create(
            **U_PARAMS,
            task_id=int,
            id=int,
            pk="id",
            foreign_keys=[
                ("task_id", "tasks", "id"),
            ],
        )


_initialize_db()

PPT_UNIT_TABLES = {
    PropertyType.WAREHOUSE: warehouses,
    PropertyType.LAND: lands,
    PropertyType.OFFICE: offices,
    PropertyType.SHOP: shops,
}

PPT_FRM_FLDS = {
    PropertyType.WAREHOUSE: WH_FLDS,
    PropertyType.LAND: UNIT_COMMON_FLDS,
    PropertyType.OFFICE: UNIT_COMMON_FLDS,
    PropertyType.SHOP: UNIT_COMMON_FLDS,
}

UNIT_TBL_FLDS = {
    PropertyType.WAREHOUSE: WH_FLDS,
    PropertyType.LAND: UNIT_COMMON_FLDS,
    PropertyType.OFFICE: UNIT_COMMON_FLDS,
    PropertyType.SHOP: UNIT_COMMON_FLDS,
}

PPT_TSK_TABLES = {
    PropertyType.WAREHOUSE: warehouse_tasks,
    PropertyType.LAND: land_tasks,
    PropertyType.OFFICE: office_tasks,
    PropertyType.SHOP: shop_tasks,
}

PPT_CMP_TABLES = {
    PropertyType.WAREHOUSE: warehouse_comparisons,
    PropertyType.LAND: land_comparisons,
    PropertyType.OFFICE: office_comparisons,
    PropertyType.SHOP: shop_comparisons,
}

FILE_TABLES = {"imgs": ppt_images, "pdfs": ppt_pdfs}

USER = users.dataclass()
PPT = properties.dataclass()
