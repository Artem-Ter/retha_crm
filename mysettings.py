import os
from enum import IntEnum, auto

import fasthtml.common as fh

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = fh.database('data/test.db')

properties = db.t.properties
modules = db.t.modules
users = db.t.users
comparisons = db.t.comparisons
comparison_modules = db.t.comparison_modules
ppt_images = db.t.ppt_images
ppt_infrastructures = db.t.ppt_infrastructures
cities = db.t.cities
streets = db.t.streets
regions = db.t.regions
districts = db.t.districts
infrastructures = db.t.infrastructures

class Choice(IntEnum):
    YES = auto()
    NO = auto()
    BOTH = auto()

class Role(IntEnum):
    ADMIN = auto()
    USER = auto()
    BROKER = auto()
    OWNER = auto()

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

@fh.dataclass
class Comparison:
    user_id: str  # foreign key to users
    ppt_id: int  # foreing key to properties
    # author_id: str  # foreign key to users
    date: str
    ad_type: int = AdType.RENT
    status: int = Status.ACTIVE

@fh.dataclass
class ComparisonModule:
    comparison_id: int  # foreign key to comparisons
    module_id: int  # foreign key to modules

@fh.dataclass
class PropertyImage:
    ppt_id: int  # foreign key to Property
    img: str
    # cover: bool = False

class PropertyType(IntEnum):
    WAREHOUSE = auto()
    LAND = auto()
    OFFICE = auto()
    SHOP = auto()

@fh.dataclass
class Infrastructure:
    name: str

@fh.dataclass
class Region:
    name: str

@fh.dataclass
class District:
    name: str

@fh.dataclass
class City:
    name: str

@fh.dataclass
class Street:
    name: str

class Zone(IntEnum):
    NORTH = auto()
    EAST = auto()
    WEST = auto()
    SOUTH = auto()
    CENTER = auto()

@fh.dataclass
class Property:
    type: int  # Use PropertyType
    in_conodminium: bool
    on_site: bool
    name: str
    cep: str
    street_id: int  # foreign key to Street
    number: int
    district_id: int  # foreign key to District
    city_id: int  # foreign key to City
    region_id: int  # foreign key to Region
    zone: int  # use Zone
    retha_admin: bool
    under_construction: bool
    description: str
    location: str
    iptu: float
    condominium: float
    foro: float

@fh.dataclass
class PropertyInfrastructure:
    ppt_id: int
    infr_id: int

@fh.dataclass
class Module:
    ppt_id: int  # foreign key to property
    broker_id: str  # foreign key to user
    owner_id: str  # foreign key to user
    title: str
    flr_capacity: int
    hight: int
    width: str
    abl: int
    office_area: int
    docks: int
    rent: int
    sell: int
    energy: int
    available: str
    sprinklers: bool
    dock_leveler: bool
    refrigiration: bool

def _initialize_db():
    if cities not in db.t:
        db.create(cls=City,
                  name='cities')
    if districts not in db.t:
        db.create(cls=District,
                  name='districts')
    if regions not in db.t:
        db.create(cls=Region,
                  name='regions')
    if streets not in db.t:
        db.create(cls=Street,
                  name='streets')
    if properties not in db.t:
        db.create(cls=Property,
                  name='properties',
                  foreign_keys=[('city_id', 'cities', 'id'),
                                ('region_id', 'regions', 'id'),
                                ('district_id', 'districts', 'id'),
                                ('street_id', 'streets', 'id')])
    if users not in db.t:
        db.create(cls=User,
                  pk='email',
                  name='users')
    if modules not in db.t:
        db.create(cls=Module,
                  name='modules',
                  foreign_keys=[('ppt_id', 'properties', 'id'),
                                ('broker_id', 'users', 'email'),
                                ('owner_id', 'users', 'email')])
    if comparisons not in db.t:
        db.create(cls=Comparison,
                  name='comparisons')
    if comparison_modules not in db.t:
        db.create(cls=ComparisonModule,
                  name='comparison_modules',
                  foreign_keys=[('comparison_id','comparisons', 'id'),
                                ('module_id', 'modules', 'id')])
    if ppt_images not in db.t:
        db.create(cls=PropertyImage,
                  name='ppt_images',
                  foreign_keys=[('ppt_id', 'properties', 'id')])
    if infrastructures not in db.t:
        db.create(cls=Infrastructure,
                  name='infrastructures')
    if ppt_infrastructures not in db.t:
        db.create(cls=PropertyInfrastructure,
                  name='ppt_infrastructures',
                  foreign_keys=[('ppt_id', 'properties', 'id'),
                                ('infr_id', 'infrastructures', 'id')])

_initialize_db()
PPT_DC, MDL_DC, USER_DC = properties.dataclass(), modules.dataclass(), users.dataclass()
