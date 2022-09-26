import decimal
import email
from operator import or_
from flask import Flask, request, jsonify, make_response, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import load_only
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import jsonpickle
from sqlalchemy import exc, Sequence
import csv
import json
import os
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv
load_dotenv()

from get_usd_price import get_usd_price

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# dev
# app.config['SQLALCHEMY_DATABASE_URI'] = 

# pool_pre_ping should help handle DB connection drops
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}  

# prod
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://admin:ISXCZMs8jsMbIueadzQzXqIiW2Jtxb1y@dpg-cc6886da49936rkaijgg-a.oregon-postgres.render.com/syncy'

# local
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///syncy'

# dynamic
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI")

print('################################', os.environ.get("DATABASE_URI"), os.environ.get("STRIPE_LIVE_SECRET_KEY"))
import stripe
# This is your test secret API key.
# stripe.api_key = 'sk_test_51JMNGMBC2Ls8FQJScwZbebJ4QxAU4XIEpf7tHIQ6b2gOJ8piskUX5WAWi6TfKrMiTmv6pHuJr1rFQsgwdPeEmHjo00h9RzLUTz'

# This is your live secret API key.
stripe.api_key = os.environ.get("STRIPE_LIVE_SECRET_KEY")

db = SQLAlchemy(app)
migrate = Migrate(app, db, compare_type=True)

from algoliasearch.search_client import SearchClient
# # API keys below contain actual values tied to your Algolia account
client = SearchClient.create('L7PFECEWC3', 'e03caa75dd335df7a8fefb1f0e3b6e27')
index = client.init_index('syncy')


YOUR_DOMAIN = 'https://syncy.net'

'''functions'''
# upload profile image to imgur and return url
def upload_image_to_imgur(image):
    import requests
    import json
    url = 'https://api.imgur.com/3/image'
    headers = {'Authorization': 'Client-ID 7e6d12bb05e5891'}
    files = {'image': image}
    r = requests.post(url, headers=headers, files=files)
    data = json.loads(r.text)
    print(data)
    return data['data']['link']

"""models"""

from sqlalchemy_serializer import SerializerMixin


# Define a base model for other database tables to inherit
class Base(db.Model, SerializerMixin):

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    date_modified = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    @classmethod
    def create(cls, **kwargs):
        """Create a new record and save it the database."""
        instance = cls(**kwargs)
        return instance.save()

    @classmethod
    def get_by_id(cls, record_id):
        """Get record by ID."""
        if any(
            (
                isinstance(record_id, (str, bytes)) and record_id.isdigit(),
                isinstance(record_id, (int, float)),
            )
        ):
            return cls.query.get(int(record_id))
        return None

    @classmethod
    def get_editable_column_names(cls):
        not_editable_columns = ["date_modified", "date_created", "id"]
        return [
            c.name for c in cls.__table__.columns if c.name not in not_editable_columns
        ]

    @classmethod
    def serialize(cls, obj):
        return {c.name: str(getattr(obj, c.name)) for c in cls.__table__.columns}

    @classmethod
    def serialize_all(cls, response):
        return [cls.serialize(obj) for obj in response]

    def save(self, commit=True):
        """Save the record."""
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def update(self, commit=True, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return commit and self.save() or self

    def delete(self, commit=True):
        """Remove the record from the database."""
        db.session.delete(self)
        return commit and db.session.commit()

# user profile model with name, linkedin url, calendly url, profile image url, city, country, bio and tags
class TargetUserProfileModel(Base):
    __tablename__ = 'target_user_profile'

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    linkedin_url = db.Column(db.String(255))
    calendly_url = db.Column(db.String(255), nullable=False)
    profile_image_url = db.Column(db.String(250), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.String(600), nullable=False)
    payment_info = db.Column(db.String(600))
    # referer name
    referer = db.Column(db.String(200))


    def __init__(self, name, email, linkedin_url, calendly_url, profile_image_url, city, country, bio, payment_info, referer):
        self.name = name
        self.email = email
        self.linkedin_url = linkedin_url
        self.calendly_url = calendly_url
        self.profile_image_url = profile_image_url
        self.city = city
        self.country = country
        self.bio = bio
        self.payment_info = payment_info
        self.referer = referer

    def __repr__(self):
        return '<id {}>'.format(self.id)


# tags model with name
class TagsModel(Base):
    __tablename__ = 'tags'

    name = db.Column(db.String(100), nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<id {}>'.format(self.id)

# tags and user map model with user id and tag id
class TagsUserMapModel(Base):
    __tablename__ = 'tags_user_map'

    user_id = db.Column(db.Integer, nullable=False)
    tag_id = db.Column(db.Integer, nullable=False)

    def __init__(self, user_id, tag_id):
        self.user_id = user_id
        self.tag_id = tag_id

    def __repr__(self):
        return '<id {}>'.format(self.id)

# school model with name
class SchoolModel(Base):
    __tablename__ = 'school'

    name = db.Column(db.String(100), nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<id {}>'.format(self.id)

# school and user map model with user id and school id
class SchoolUserMapModel(Base):
    __tablename__ = 'school_user_map'

    user_id = db.Column(db.Integer, nullable=False)
    school_id = db.Column(db.Integer, nullable=False)

    def __init__(self, user_id, school_id):
        self.user_id = user_id
        self.school_id = school_id

    def __repr__(self):
        return '<id {}>'.format(self.id)

# company model with name
class CompanyModel(Base):
    __tablename__ = 'company'

    name = db.Column(db.String(100), nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<id {}>'.format(self.id)

# company and user map model with user id and company id
class CompanyUserMapModel(Base):
    __tablename__ = 'company_user_map'

    user_id = db.Column(db.Integer, nullable=False)
    company_id = db.Column(db.Integer, nullable=False)

    def __init__(self, user_id, company_id):
        self.user_id = user_id
        self.company_id = company_id

    def __repr__(self):
        return '<id {}>'.format(self.id)

"""routes"""

"""home route"""


@app.route('/')
def hello():
    # products = ProductModel.query.order_by(ProductModel.date_modified.desc()).all()
    # products_dict = ProductModel.serialize_all(products)


    # for product in products_dict:
    #     # Make sure each object has an 'ObjectID' defined
    #     # We recommend keeping the 'ObjectID' analogous to your internal ID
    #     product['objectID'] = product['id']
    #     CATEGORIES = []
    #     # Index the product with Algolia
    #     for c in product['category'].split(','):
    #         CATEGORIES.append(c.strip())
    #     product['categories'] = CATEGORIES
    #     index.save_object(product)

    # print('##', index, products_dict)
    return {"hello": "world"}


"""target user profile routes"""
# create new target user profile
@app.route('/target_user_profile', methods=['POST'])
def create_target_user_profile():
    # data = request.get_json()
    data =dict()
    data['name'] = request.form.get('name')
    data['email'] = request.form.get('email')
    data['linkedin_url'] = request.form.get('linkedin')
    data['calendly_url'] = request.form.get('calendly')
    data['bio'] = request.form.get('bio-max-250-characters')
    data['city'] = request.form.get('city')
    data['country'] = request.form.get('country')
    data['tags'] = [tag.strip() for tag in request.form.get('tags-eg-doctor-parent-student-designer-etc-at-least-2-tags-comma-separated').split(',')]
    data['school'] = [tag.strip() for tag in request.form.get('schools-you-attended-eg-harvard-london-university-etc-comma-separated').split(',')]
    data['company'] = [tag.strip() for tag in request.form.get('companies-you-have-worked-for-eg-google-spotify-etc-comma-separated').split(',')]
    data['payment_info'] = request.form.get('payment-info-paypal-email-or-venmo-id')
    data['referer'] = request.form.get('referrer-name')

    # get profile image from request form
    profile_image = request.files['profile-image'] 
    #  upload profile image to imgur and get the url
    data['profile_image_url'] = upload_image_to_imgur(profile_image)
    print(data, profile_image)
    try:
        new_target_user_profile = TargetUserProfileModel.create(
            name=data['name'],
            email=data['email'],
            linkedin_url=data['linkedin_url'],
            calendly_url=data['calendly_url'],
            profile_image_url=data['profile_image_url'],
            city=data['city'],
            country=data['country'],
            bio=data['bio'],
            payment_info=data['payment_info'],
            referer=data['referer']
        )
        # create tags if dont exist and map them to user
        for tag in data['tags']:
            # check case and remove spaces
            tag = tag.strip().lower()
            # check if tag exists
            tag_exists = TagsModel.query.filter_by(name=tag).first()
            if tag_exists:
                # map tag to user
                TagsUserMapModel.create(
                    user_id=new_target_user_profile.id,
                    tag_id=tag_exists.id
                )
            else:
                # create tag and map to user
                new_tag = TagsModel.create(
                    name=tag
                )
                TagsUserMapModel.create(
                    user_id=new_target_user_profile.id,
                    tag_id=new_tag.id
                )

        # create schools if dont exist and map them to user
        for school in data['school']:
            # check case and remove spaces
            school = school.strip().lower()
            # check if school exists
            school_exists = SchoolModel.query.filter_by(name=school).first()
            if school_exists:
                # map school to user
                SchoolUserMapModel.create(
                    user_id=new_target_user_profile.id,
                    school_id=school_exists.id
                )
            else:
                # create school and map to user
                new_school = SchoolModel.create(
                    name=school
                )
                SchoolUserMapModel.create(
                    user_id=new_target_user_profile.id,
                    school_id=new_school.id
                )
        
        # create companies if dont exist and map them to user
        for company in data['company']:
            # check case and remove spaces
            company = company.strip().lower()
            # check if company exists
            company_exists = CompanyModel.query.filter_by(name=company).first()
            if company_exists:
                # map company to user
                CompanyUserMapModel.create(
                    user_id=new_target_user_profile.id,
                    company_id=company_exists.id
                )
            else:
                # create company and map to user
                new_company = CompanyModel.create(
                    name=company
                )
                CompanyUserMapModel.create(
                    user_id=new_target_user_profile.id,
                    company_id=new_company.id
                )
        

        
        # send to algolia
        new_target_user_profile_dict = TargetUserProfileModel.serialize(new_target_user_profile)
        print('##', new_target_user_profile_dict)
        new_target_user_profile_dict['objectID'] = new_target_user_profile_dict['id']
        print('## 2', new_target_user_profile_dict)
        
        CATEGORIES = []
        # Index the product with Algolia
        for c in data['tags']:
            CATEGORIES.append(c.strip())
        new_target_user_profile_dict['categories'] = CATEGORIES

        SCHOOLS = []
        # Index the product with Algolia
        for c in data['school']:
            SCHOOLS.append(c.strip())
        new_target_user_profile_dict['schools'] = SCHOOLS

        COMPANIES = []
        # Index the product with Algolia
        for c in data['company']:
            COMPANIES.append(c.strip())
        new_target_user_profile_dict['companies'] = COMPANIES
        
        print('## 3', new_target_user_profile_dict)
        index.save_object(new_target_user_profile_dict)
        print('## 4', new_target_user_profile_dict)
        # return new_target_user_profile_dict
        responseObject = {
            'status': 'success',
            'data': {
                'user': TargetUserProfileModel.serialize(new_target_user_profile),
            },
        }
        print('## 5', responseObject)
        # redirect to home page
        return redirect("https://syncy.net/#join-success", code=302)
        # return make_response(jsonify(responseObject)), 200
    except exc.IntegrityError as e:
        print(str(e))
        responseObject = {
            'status': 'fail',
            'message': 'Profile Already Exists.'
        }
        return (
            make_response(jsonify(responseObject)),
            500,
        )
    except Exception as e:
        print(str(e))
        responseObject = {
            'status': 'fail',
            'message': 'Something went wrong.'
        }
        return (
            make_response(jsonify(responseObject)),
            500,
        )

# get all target user profiles with pagination
@app.route('/target_user_profiles', methods=['GET'])
def get_target_user_profiles():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    target_user_profiles = TargetUserProfileModel.query.paginate(page, per_page, error_out=False)
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles.items)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
            'total': target_user_profiles.total,
            'pages': target_user_profiles.pages,
            'page': target_user_profiles.page,
            'per_page': target_user_profiles.per_page,
        },
    }
    return make_response(jsonify(responseObject)), 200

# get target user profile by id
@app.route('/target_user_profile/<int:id>', methods=['GET'])
def get_target_user_profile(id):
    target_user_profile = TargetUserProfileModel.query.get(id)
    if not target_user_profile:
        responseObject = {
            'status': 'fail',
            'message': 'Target User Profile does not exist.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profile': TargetUserProfileModel.serialize(target_user_profile),
        },
    }
    return make_response(jsonify(responseObject)), 200

# update target user profile by id
@app.route('/target_user_profile/<int:id>', methods=['PUT'])
def update_target_user_profile(id):
    target_user_profile = TargetUserProfileModel.query.get(id)
    if not target_user_profile:
        responseObject = {
            'status': 'fail',
            'message': 'Target User Profile does not exist.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    data = request.get_json()
    try:
        target_user_profile.name = data['name']
        target_user_profile.email = data['email']
        target_user_profile.linkedin_url = data['linkedin_url']
        target_user_profile.calendly_url = data['calendly_url']
        target_user_profile.profile_image_url = data['profile_image_url']
        target_user_profile.city = data['city']
        target_user_profile.country = data['country']
        target_user_profile.bio = data['bio']
        target_user_profile.tags = data['tags']
        db.session.commit()
        responseObject = {
            'status': 'success',
            'data': {
                'target_user_profile': TargetUserProfileModel.serialize(target_user_profile),
            },
        }
        return make_response(jsonify(responseObject)), 200
    except exc.IntegrityError as e:
        print(str(e))
        responseObject = {
            'status': 'fail',
            'message': 'Profile Already Exists.'
        }
        return (
            make_response(jsonify(responseObject)),
            500,
        )
    except Exception as e:
        print(str(e))
        responseObject = {
            'status': 'fail',
            'message': 'Something went wrong.'
        }
        return (
            make_response(jsonify(responseObject)),
            500,
        )

# delete target user profile by id
@app.route('/target_user_profile/<int:id>', methods=['DELETE'])
def delete_target_user_profile(id):
    target_user_profile = TargetUserProfileModel.query.get(id)
    if not target_user_profile:
        responseObject = {
            'status': 'fail',
            'message': 'Target User Profile does not exist.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    db.session.delete(target_user_profile)
    db.session.commit()
    responseObject = {
        'status': 'success',
        'message': 'Target User Profile deleted successfully.',
    }
    return make_response(jsonify(responseObject)), 200

# get all target user profiles by tag
@app.route('/target_user_profiles_by_tag', methods=['GET'])
def get_target_user_profiles_by_tag():
    tag = request.args.get('tag', None, type=str)
    if not tag:
        responseObject = {
            'status': 'fail',
            'message': 'Tag is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter(TargetUserProfileModel.tags.contains(tag)).all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
        },
    }
    return make_response(jsonify(responseObject)), 200

# get all target user profiles by city
@app.route('/target_user_profiles_by_city', methods=['GET'])
def get_target_user_profiles_by_city():
    city = request.args.get('city', None, type=str)
    if not city:
        responseObject = {
            'status': 'fail',
            'message': 'City is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter_by(city=city).all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
        },
    }
    return make_response(jsonify(responseObject)), 200

# get all target user profiles by country
@app.route('/target_user_profiles_by_country', methods=['GET'])
def get_target_user_profiles_by_country():
    country = request.args.get('country', None, type=str)
    if not country:
        responseObject = {
            'status': 'fail',
            'message': 'Country is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter_by(country=country).all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
        },
    }
    return make_response(jsonify(responseObject)), 200

# get all target user profiles by city and country
@app.route('/target_user_profiles_by_city_and_country', methods=['GET'])
def get_target_user_profiles_by_city_and_country():
    city = request.args.get('city', None, type=str)
    country = request.args.get('country', None, type=str)
    if not city:
        responseObject = {
            'status': 'fail',
            'message': 'City is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    if not country:
        responseObject = {
            'status': 'fail',
            'message': 'Country is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter_by(city=city, country=country).all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
        },
    }
    return make_response(jsonify(responseObject)), 200

# get all target user profiles by city and country and tag
@app.route('/target_user_profiles_by_city_and_country_and_tag', methods=['GET'])
def get_target_user_profiles_by_city_and_country_and_tag():
    city = request.args.get('city', None, type=str)
    country = request.args.get('country', None, type=str)
    tag = request.args.get('tag', None, type=str)
    if not city:
        responseObject = {
            'status': 'fail',
            'message': 'City is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    if not country:
        responseObject = {
            'status': 'fail',
            'message': 'Country is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    if not tag:
        responseObject = {
            'status': 'fail',
            'message': 'Tag is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter_by(city=city, country=country).filter(TargetUserProfileModel.tags.contains(tag)).all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
        },
    }
    return make_response(jsonify(responseObject)), 200

# get all target user profiles by city and tag
@app.route('/target_user_profiles_by_city_and_tag', methods=['GET'])
def get_target_user_profiles_by_city_and_tag():
    city = request.args.get('city', None, type=str)
    tag = request.args.get('tag', None, type=str)
    if not city:
        responseObject = {
            'status': 'fail',
            'message': 'City is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    if not tag:
        responseObject = {
            'status': 'fail',
            'message': 'Tag is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter_by(city=city).filter(TargetUserProfileModel.tags.contains(tag)).all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
        },
    }
    return make_response(jsonify(responseObject)), 200


# get all target user profiles by country and tag
@app.route('/target_user_profiles_by_country_and_tag', methods=['GET'])
def get_target_user_profiles_by_country_and_tag():
    country = request.args.get('country', None, type=str)
    tag = request.args.get('tag', None, type=str)
    if not country:
        responseObject = {
            'status': 'fail',
            'message': 'Country is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    if not tag:
        responseObject = {
            'status': 'fail',
            'message': 'Tag is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter_by(country=country).filter(TargetUserProfileModel.tags.contains(tag)).all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
        },
    }
    return make_response(jsonify(responseObject)), 200

# search target user profiles by name or city or country or tag or bio with pagination
@app.route('/target_user_profiles_search', methods=['GET'])
def get_target_user_profiles_search():
    search = request.args.get('search', None, type=str)
    page = request.args.get('page', 1, type=int)
    if not search:
        responseObject = {
            'status': 'fail',
            'message': 'Search is required.'
        }
        return (
            make_response(jsonify(responseObject)),
            404,
        )
    target_user_profiles = TargetUserProfileModel.query.filter(
        or_(
            TargetUserProfileModel.name.like('%' + search + '%'),
            TargetUserProfileModel.city.like('%' + search + '%'),
            TargetUserProfileModel.country.like('%' + search + '%'),
            TargetUserProfileModel.tags.like('%' + search + '%'),
            TargetUserProfileModel.bio.like('%' + search + '%'),
        )
    ).paginate(page=page, per_page=10, error_out=False)
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles.items)
    responseObject = {
        'status': 'success',
        'data': {
            'target_user_profiles': target_user_profiles_dict,
            'total_pages': target_user_profiles.pages,
            'total_items': target_user_profiles.total,
        },
    }
    return make_response(jsonify(responseObject)), 200

# Create a Checkout Session
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    print('create_checkout_session')
    # get the post data from the request
    post_data = request.get_json()
    # get user id, name, profile_image, email, city, country, tags, bio, success_url, cancel_url, linkedin from the post data
    user_id = post_data.get('user_id')
    name = post_data.get('name')
    profile_image_url = post_data.get('profile_image_url')
    email = post_data.get('email')
    city = post_data.get('city')
    country = post_data.get('country')
    tags = post_data.get('tags')
    bio = post_data.get('bio')
    linkedin_url = post_data.get('linkedin_url')
    calendly_url = post_data.get('calendly_url')

    # print the post data
    print('post_data', post_data)

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': 2500,
                        'product_data': {
                            'name': 'Syncy 30 minute call with ' + name,
                            "description": "Please complete payment in order to confirm your Sync. Send questions or feedback to help@syncy.net.",
                            "images": [profile_image_url],
                            "metadata": {
                                "name": name,
                                "email" : email,
                                "linkedin": linkedin_url,
                                "bio": bio,
                                "city": city,
                                "country": country,
                                "tags": tags,
                            },
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            allow_promotion_codes=True,
            # success_url='http://localhost:5500/book-call.html?id=' + user_id,
            success_url=YOUR_DOMAIN + '/?id=' + user_id + '#book-call',
            cancel_url=YOUR_DOMAIN + '/#match',
        )
        # print(checkout_session)
        responseObject = {
            'status': 'success',
            'data': {
                'url': checkout_session.url,
            },
        }
        return make_response(jsonify(responseObject)), 200
    except Exception as e:
        print('e', str(e))
        return str(e)

# import pandas
import pandas as pd
# import send_file
from flask import send_file


# get all target users and send csv file
@app.route('/target_users_csv', methods=['GET'])
def get_target_users_csv():
    target_user_profiles = TargetUserProfileModel.query.all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)

    # create a csv file with panda
    df = pd.DataFrame(target_user_profiles_dict)
    csv = df.to_csv('target_user_profiles', index=False)

    # sned csv file with send_file
    return send_file('target_user_profiles', mimetype='text/csv', attachment_filename='target_user_profiles.csv', as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
