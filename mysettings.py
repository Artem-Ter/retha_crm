import os
from enum import IntEnum, auto
from pathlib import Path

import fasthtml.common as fh
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API = os.getenv('GOOGLE_API')

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / 'images'
PDF_DIR = BASE_DIR / 'pdfs'

db = fh.database('data/test.db')

properties = db.t.properties
property_details = db.t.property_details
warehouses = db.t.warehouses
lands = db.t.lands
offices = db.t.offices
shops = db.t.shops
users = db.t.users
comparisons = db.t.comparisons
warehouse_comparisons = db.t.warehouse_comparisons
ppt_images = db.t.ppt_images
ppt_infrastructures = db.t.ppt_infrastructures
cities = db.t.cities
streets = db.t.streets
regions = db.t.regions
districts = db.t.districts
infrastructures = db.t.infrastructures
notes = db.t.notes
tasks = db.t.tasks

class Avcb(IntEnum):
    opt1 = auto()
    opt2 = auto()

class Choice(IntEnum):
    YES = auto()
    NO = auto()
    BOTH = auto()

class Role(IntEnum):
    ADMIN = auto()
    USER = auto()
    BROKER = auto()
    OWNER = auto()
    SECRETARY = auto()

@fh.dataclass
class User:
    name: str
    email: str
    pwd: str
    phone: str
    organization: str
    role: int = Role.USER

class AdType(IntEnum):
    RENT = auto()
    SELL = auto()

class Status(IntEnum):
    ACTIVE = auto()
    ARCHIVE = auto()

class PropertyType(IntEnum):
    WAREHOUSE = auto()
    LAND = auto()
    OFFICE = auto()
    SHOP = auto()

class Zone(IntEnum):
    NORTH = auto()
    EAST = auto()
    WEST = auto()
    SOUTH = auto()
    CENTER = auto()

@fh.dataclass
class Comparison:
    user_id: str  # foreign key to users
    pd_id: int  # foreing key to property_details
    # author_id: str  # foreign key to users
    date: str
    ad_type: int = AdType.RENT
    status: int = Status.ACTIVE

@fh.dataclass
class WarehouseComparison:
    comparison_id: int  # foreign key to comparisons
    warehouse_id: int  # foreign key to warehouses

@fh.dataclass
class Property:
    in_conodminium: bool
    on_site: bool
    name: str
    cep: str
    street_id: int  # foreign key to Street
    number: int
    district_id: int  # foreign key to District
    city_id: int  # foreign key to City
    region_id: int  # foreign key to Region
    retha_admin: bool
    under_construction: bool
    location: str

@fh.dataclass
class PropertyDetails:
    ppt_id: int  # foreign key to Property
    type: int  # Use PropertyType
    description: str
    iptu: float
    condominium: float
    foro: float

@fh.dataclass
class Task:
    client_id: int
    broker_id: int
    initial_dscr: str  # initial reqeust
    broker: int
    infrastructure: int
    name: int
    commercial: int
    type: int
    in_conodminium: int
    city: int
    region: int
    district: int
    zone: int
    price_min: int
    price_max: int
    area_min: int
    area_max: int
    height_min: int
    height_max: int
    efficiency_min: int
    efficiency_max: int
    abl_min: int
    abl_max: int
    doks_min: int
    doks_max: int
    flr_capacity_min: int
    flr_capacity_max: int
    office_area_min: int
    office_area_max: int
    energy_min: int
    energy_max: int
    avcb: int
    under_construction: int
    date: str

@fh.dataclass
class Note:
    task_id: int
    descripton: str
    date: str

@fh.dataclass
class Unit:
    pd_id: int  # foreign key to property_details
    broker_id: str  # foreign key to user
    owner_id: str  # foreign key to user
    title: str
    abl: int
    rent: int
    sell: int
    available: str
    date: str

@fh.dataclass
class Warehouse(Unit):
    flr_capacity: int
    height: int
    width: str
    office_area: int
    docks: int
    energy: int
    sprinklers: bool
    dock_leveler: bool
    refrigiration: bool

@fh.dataclass
class Land(Unit):
    ...

@fh.dataclass
class Office(Unit):
    ...

@fh.dataclass
class Shop(Unit):
    ...

def _initialize_db():
    if users not in db.t:
        db.create(
            cls=User,
            name='users'
        )
        users.create_index(
            ['email'],
            unique=True,
        )
        pwd = os.getenv('ADMIN_PWD')
        email = os.getenv('ADMIN_EMAIL')
        admin = {'email': email, 'pwd': pwd, 'role': Role.ADMIN, 'organization': 'Retha'}
        secretary = {'email': 'secretary@ya.ru', 'pwd': pwd, 'role': Role.SECRETARY, 'organization': 'Retha'}
        users.insert_all([
            admin,
            secretary
        ])
    if properties not in db.t:
        regions.create(id=int, name=str, pk='id')
        cities.create(id=int, name=str, pk='id')
        districts.create(id=int, name=str, pk='id')
        streets.create(id=int, name=str, pk='id')
        infrastructures.create(id=int, name=str, pk='id')
            
        # properties.create(
        #     id=int, in_conodminium=bool, on_site=bool, name=str,
        #     cep=str, street_id=int, number=int, district_id=int,
        #     city_id=int, region_id=int, zone=int,
        #     retha_admin=bool, under_construction=bool,
        #     description=str, location=str,
        #     iptu=float, condominium=float, foro=float,
        #     pk='id',
        #     foreign_keys=[
        #         ('city_id', 'cities', 'id'),
        #         ('region_id', 'regions', 'id'),
        #         ('district_id', 'districts', 'id'),
        #         ('street_id', 'streets', 'id')
        #     ],
        # )
        db.create(cls=Property,
                  name='properties',
                  foreign_keys=[('city_id', 'cities', 'id'),
                                ('region_id', 'regions', 'id'),
                                ('district_id', 'districts', 'id'),
                                ('street_id', 'streets', 'id')])
        db.create(cls=PropertyDetails,
                  name='property_details',
                  foreign_keys=[('ppt_id', 'properties', 'id')])
        ppt_images.create(
            id=int, pd_id=int, img=str, pk='id',
            foreign_keys=[('pd_id', 'property_details', 'id')]
        )
        db.create(
            cls=Warehouse,
            name='warehouses',
            foreign_keys=[
                ('pd_id', 'property_details', 'id'),
                ('broker_id', 'users', 'id'),
                ('owner_id', 'users', 'id')
            ]
        )
        db.create(
            cls=Land, 
            name='lands',
            foreign_keys=[
                ('pd_id', 'property_details', 'id'),
                ('broker_id', 'users', 'id'),
                ('owner_id', 'users', 'id')
            ]
        )
        db.create(
            cls=Office, 
            name='offices',
            foreign_keys=[
                ('pd_id', 'property_details', 'id'),
                ('broker_id', 'users', 'id'),
                ('owner_id', 'users', 'id')
            ]
        )
        db.create(
            cls=Shop, 
            name='shops',
            foreign_keys=[
                ('pd_id', 'property_details', 'id'),
                ('broker_id', 'users', 'id'),
                ('owner_id', 'users', 'id')
            ]
        )
        ppt_infrastructures.create(
            id=int, ppt_id=int, infr_id=int,
            pk='id',
            foreign_keys=[
                ('ppt_id', 'properties', 'id'),
                ('infr_id', 'infrastructures', 'id')
            ]
        )
    if comparisons not in db.t:
        db.create(
            cls=Comparison,
            name='comparisons',
            foreign_keys=[
                ('pd_id', 'property_details', 'id'),
                ('user_id', 'users', 'id')
            ]
        )
        warehouse_comparisons.create(
            id=int, comparison_id=int, warehouse_id=int,
            pk='id',
            foreign_keys=[
                ('comparison_id','comparisons', 'id'),
                ('warehouse_id', 'warehouses', 'id')
            ]
        )
    if tasks not in db.t:
        db.create(cls=Task,
                  name='tasks',
                  foreign_keys=[('client_id', 'users', 'id'),
                                ('broker_id', 'users', 'id')])

_initialize_db()
PPT_DC, WRH_DC, USER_DC = properties.dataclass(), warehouses.dataclass(), users.dataclass()
property_details.dataclass()
# users.drop()
print(ppt_infrastructures())
print(infrastructures())
print(property_details())
print(properties())


