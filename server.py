import decimal
import email
from operator import or_
from flask import Flask, request, jsonify, make_response, redirect, render_template
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
import requests


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
stripe.api_key = 'sk_test_51JMNGMBC2Ls8FQJScwZbebJ4QxAU4XIEpf7tHIQ6b2gOJ8piskUX5WAWi6TfKrMiTmv6pHuJr1rFQsgwdPeEmHjo00h9RzLUTz'

# This is your live secret API key.
# stripe.api_key = os.environ.get("STRIPE_LIVE_SECRET_KEY")

db = SQLAlchemy(app)
migrate = Migrate(app, db, compare_type=True)

from algoliasearch.search_client import SearchClient
# # API keys below contain actual values tied to your Algolia account
client = SearchClient.create('L7PFECEWC3', 'e03caa75dd335df7a8fefb1f0e3b6e27')
# index = client.init_index('syncy')

class CONTENT_PACK_BOOKING_STATUS:
    PENDING = 'PENDING',
    BOOKED = 'BOOKED',
    ACCEPTED = 'ACCEPTED',
    REJECTED = 'REJECTED',
    SUBMITTED = 'SUBMITTED',
    CANCELLED = 'CANCELLED',
    COMPLETED = 'COMPLETED'


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

@app.route('/update-algolia', methods=['GET', 'POST'])
def update_algolia_index():

    # get url from request
    url = request.args.get('url')
    # get objectID from request
    objectID = request.args.get('objectID')

    influencer = request.json["influencer"]

    print('here 2 **********',url, objectID)

    index = client.init_index('influencers')

    influencer["imageUrl"] = url

    res = index.save_object(influencer, {'autoGenerateObjectIDIfNotExist': True}).wait()

    # res = index.partial_update_object(
    #     {
    #         'objectID': objectID,
    #         'profilePicUrl': url,
    #     }
    # ).wait()

    print('here 3 **********', objectID, res.raw_responses)
    # record = index.get_object(objectID)
    # print(record)

    return jsonify({'success': True, 'message': 'updated algolia index'})


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
class BrandUserProfileModel(Base):
    __tablename__ = 'brand_user_profile'

    # First Name, Last Name, job title, company name, company website, company logo, company description, company address, company email, company instagram, linkedin url 
    email = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(200))
    last_name = db.Column(db.String(200))
    job_title = db.Column(db.String(200))
    company_name = db.Column(db.String(200))
    company_website = db.Column(db.String(200))
    company_description = db.Column(db.String(200))
    company_address = db.Column(db.String(200))
    company_email = db.Column(db.String(200))
    company_instagram = db.Column(db.String(200))
    company_linkedin = db.Column(db.String(200))
    company_logo = db.Column(db.String(200))
    book_call_info = db.Column(db.String(200))

    def __repr__(self):
        return '<id {}>'.format(self.id)


class InfluencerProfileModel(Base):
    __tablename__ = 'influencer_profile'

    # First Name, Last Name, job title, company name, company website, company logo, company description, company address, company email, company instagram, linkedin url 
    email = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(200))
    last_name = db.Column(db.String(200))
    bio = db.Column(db.String(500))
    city = db.Column(db.String(200))
    image_url = db.Column(db.String(200))
    calender_url = db.Column(db.String(200))

    # instagram username, followers count, rate, category, hashtags, top post url 1, top post url 2, top post url 3, sponsored post url 1, sponsored post url 2, sponsored post url 3
    instagram_username = db.Column(db.String(200))
    followers_count = db.Column(db.Integer)
    rate = db.Column(db.Integer)
    category = db.Column(db.String(200))
    hashtags = db.Column(db.String(200))
    top_post_url_1 = db.Column(db.String(200))
    top_post_url_2 = db.Column(db.String(200))
    top_post_url_3 = db.Column(db.String(200))
    sponsored_post_url_1 = db.Column(db.String(200))
    sponsored_post_url_2 = db.Column(db.String(200))
    sponsored_post_url_3 = db.Column(db.String(200))

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
    
class BrandInfluencerChannelMapModel(Base):
    __tablename__ = 'brand_influencer_channel_map'

    brand_email = db.Column(db.String(200), nullable=False)
    influencer_email = db.Column(db.String(200), nullable=False)
    channel_id = db.Column(db.String(200), nullable=False)

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
    
# campaigns model with name, description, status, email, type, logo
class CampaignsModel(Base):
    __tablename__ = 'campaigns'

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(100))
    email = db.Column(db.String(100))
    type = db.Column(db.String(100))
    logo = db.Column(db.String(100))

    def __repr__(self):
        return '<id {}>'.format(self.id)

# campaign proposal model with campaign id, influencer email, status, price, description
class CampaignProposalModel(Base):
    __tablename__ = 'campaign_proposal'

    campaign_id = db.Column(db.Integer, nullable=False)
    influencer_email = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(100))
    price = db.Column(db.Integer)
    description = db.Column(db.String(200))

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

class ContentPacksModel(Base):
    __tablename__ = 'contentpacks'

    title = db.Column(db.String(300))
    description = db.Column(db.String(1000))
    price = db.Column(db.Integer)
    platform = db.Column(db.String(300))
    examples = db.Column(db.String(10000))
    delivery = db.Column(db.Integer)

    def __repr__(self):
        return '<contentpack id {}>'.format(self.id)

class ContentPacksUserMapModel(Base):
    __tablename__ = 'contentpacks_user_map'

    user_email = db.Column(db.String, nullable=False)
    contentpack_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<id {}>'.format(self.id)

class ContentPackBookingsModel(Base):
    __tablename__ = 'contentpack_bookings'

    user_email = db.Column(db.String, nullable=False)
    contentpack_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, default=CONTENT_PACK_BOOKING_STATUS.PENDING)
    details = db.Column(db.String(20000))
    copy = db.Column(db.String(20000))
    script = db.Column(db.String(20000))

    def __repr__(self):
        return '<id {}>'.format(self.id)

"""routes"""

"""home route"""


@app.route('/')
def home():
    return jsonify({'message': 'Welcome to the API'}), 200

@app.route('/imageUpload', methods=['POST', 'GET'])
def imageUpload():
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

    # get imageUrl from request body
    image_url = request.json['imageUrl']
    username = request.args.get('username')

    # print(image_url)

    # download image

    # image = requests.get(image_url).content

    # import urllib.request

    # urllib.request.urlretrieve(image_url, username + '.jpg')

    import urllib
    resource = urllib.request.urlopen(image_url)
    output = open('-'.join(username.strip().replace('/', '').split(' ')) + '.jpg',"wb")
    output.write(resource.read())
    output.close()

    print('here++++++++++')
    # print(requests)
    # save image to local

    # f = open(username + '.jpg', 'wb')
    # f.write(image)
    # f.close()

    # upload image to imgur

    f = open('-'.join(username.strip().replace('/', '').split(' ')) + '.jpg', 'rb')
    res = upload_image_to_imgur(image=f)
    print(res)
    f.close()

    return {"url": res}
    # upload image to imgur
    files = dict(
        image=(None, image_url),
        name=(None, ''),
        type=(None, 'URL'),
        )

    return {"hello": "world"}


# save brand user profile
@app.route('/brand_user_profile', methods=['POST'])
def create_brand_user_profile():
    post_data = request.get_json()
    
    email = post_data.get('email')
    first_name = post_data.get('firstName')
    last_name = post_data.get('lastName')
    company_name = post_data.get('companyName')
    company_website = request.json['companyWebsite']
    company_logo = request.json['companyLogo']
    company_address = request.json['companyAddress']
    company_instagram = request.json['companyInstagram']
    company_linkedin = request.json['companyLinkedin']
    company_email = request.json['companyEmail']
    job_title = request.json['jobTitle']
    company_description = request.json['companyDescription']
    book_call_info = request.json['bookCallInfo']

    print(email, first_name, last_name, company_name, company_website, company_logo, company_address, company_instagram, company_linkedin, company_email, job_title, company_description, book_call_info)
    # check if user exists

    user = BrandUserProfileModel.query.filter_by(email=email).first()
    
    print(user)

    try:

        # if user exists, update user, else create user
        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.job_title = job_title
            user.company_name = company_name
            user.company_website = company_website
            user.company_logo = company_logo
            user.company_address = company_address
            user.company_instagram = company_instagram
            user.company_linkedin = company_linkedin
            user.company_email = company_email
            user.company_description = company_description
            user.book_call_info = book_call_info

            # save user
            db.session.add(user)
            db.session.commit()

            response_object = {
                'status': 'success',
                'message': 'Successfully updated.'
            }
            return jsonify(response_object), 201
            
        else:
            # create new user
            new_user = BrandUserProfileModel(
                email=email,
                first_name=first_name,
                last_name=last_name,
                job_title=job_title,
                company_name=company_name,
                company_website=company_website,
                company_logo=company_logo,
                company_address=company_address,
                company_instagram=company_instagram,
                company_linkedin=company_linkedin,
                company_email=company_email,
                company_description=company_description,
                book_call_info=book_call_info
            )

            # save user
            db.session.add(new_user)
            db.session.commit()

            response_object = {
                'status': 'success',
                'message': 'Successfully registered.'
            }
            return jsonify(response_object), 201
        
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': e.message
        }
        return jsonify(response_object), 501


# get brand user profile
@app.route('/brand_user_profile', methods=['GET'])
def get_brand_user_profile():
    email = request.args.get('email')
    user = BrandUserProfileModel.query.filter_by(email=email).first()

    if user:
        response_object = {
            'code': '200',
            'status': 'success',
            'message': 'User profile found.',
            'data': BrandUserProfileModel.serialize(user)
        }
        return jsonify(response_object), 200
    else:
        response_object = {
            'code': '400',
            'status': 'fail',
            'message': 'User profile not found.',
        }
        return jsonify(response_object), 400


# save influencer profile
@app.route('/influencer-profile-personal', methods=['POST'])
def create_influencer_profile_personal():
    post_data = request.get_json()
    
    email = post_data.get('email')
    first_name = post_data.get('firstName')
    last_name = post_data.get('lastName')
    image_url = post_data.get('imageUrl')
    city = post_data.get('city')
    bio = post_data.get('bio')
    calender_url = post_data.get('bookCallInfo')

    print(email, first_name, last_name, image_url, city, bio, calender_url)

    # check if user exists

    user = InfluencerProfileModel.query.filter_by(email=email).first()
    
    # if user exists, update user, else create user
    if user:
        try:
            user.first_name = first_name
            user.last_name = last_name
            user.image_url = image_url
            user.city = city
            user.bio = bio
            user.calender_url = calender_url

            # save user
            db.session.add(user)
            db.session.commit()

            # save to algolia index "influencers"
            index = client.init_index('influencers')
            index.partial_update_object({
                'objectID': user.id,
                'email': user.email,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'fullName': user.first_name + ' ' + user.last_name,
                'imageUrl': user.image_url,
                'city': user.city,
                'bio': user.bio,
                'bookCallInfo': user.calender_url,
            })

            response_object = {
                'status': 'success',
                'message': 'Successfully updated.'
            }
            return jsonify(response_object), 201
        except Exception as e:
            print(e)
            response_object = {
                'status': 'fail',
                'message': e.message
            }
            return jsonify(response_object), 401
    
    else:
        try:
            # create new user
            new_user = InfluencerProfileModel(
                email=email,
                first_name=first_name,
                last_name=last_name,
                image_url=image_url,
                city=city,
                bio=bio,
                calender_url=calender_url
            )

            print(new_user)

            # save user
            db.session.add(new_user)
            db.session.commit()

            # save to algolia index "influencers"
            index = client.init_index('influencers')
            index.save_object({
                'objectID': new_user.id,
                'email': new_user.email,
                'firstName': new_user.first_name,
                'lastName': new_user.last_name,
                'fullName': new_user.first_name + ' ' + new_user.last_name,
                'imageUrl': new_user.image_url,
                'city': new_user.city,
                'bio': new_user.bio,
                'bookCallInfo': new_user.calender_url,
            })

            response_object = {
                'status': 'success',
                'message': 'Successfully registered.'
            }
            return jsonify(response_object), 201

        except Exception as e:
            print(e)
            response_object = {
                'status': 'fail',
                'message': e.message
            }
            return jsonify(response_object), 401

# get influencer profile
@app.route('/influencer-profile-personal', methods=['GET'])
def get_influencer_profile_personal():
    email = request.args.get('email')
    user = InfluencerProfileModel.query.filter_by(email=email).first()

    if user:
        response_object = {
            'code': '200',
            'status': 'success',
            'message': 'User profile found.',
            'data': InfluencerProfileModel.serialize(user)
        }
        return jsonify(response_object), 200
    else:
        response_object = {
            'code': '400',
            'status': 'fail',
            'message': 'User profile not found.',
        }
        return jsonify(response_object), 400


# save influencer profile instagram
@app.route('/influencer-profile-instagram', methods=['POST'])
def create_influencer_profile_instagram():
    post_data = request.get_json()

    email = post_data.get('email')
    instagram_username = post_data.get('username')
    followers_count = post_data.get('followersCount')
    rate = post_data.get('rate')
    category = post_data.get('category')
    hashtags = post_data.get('hashtags')
    top_post_url_1 = post_data.get('topPostUrl1')
    top_post_url_2 = post_data.get('topPostUrl2')
    top_post_url_3 = post_data.get('topPostUrl3')
    sponsored_post_url_1 = post_data.get('sponsoredPostUrl1')
    sponsored_post_url_2 = post_data.get('sponsoredPostUrl2')
    sponsored_post_url_3 = post_data.get('sponsoredPostUrl3')

    print(email, instagram_username, followers_count, rate, category, hashtags, top_post_url_1, top_post_url_2, top_post_url_3, sponsored_post_url_1, sponsored_post_url_2, sponsored_post_url_3)

    # check if user exists
    user = InfluencerProfileModel.query.filter_by(email=email).first()

    # if user exists, update user, else create user
    if user:
        user.instagram_username = instagram_username
        user.followers_count = followers_count if followers_count else 0
        user.rate = rate if rate else 0
        user.category = category if category else ''
        user.hashtags = hashtags if hashtags else ''
        user.top_post_url_1 = top_post_url_1 if top_post_url_1 else ''
        user.top_post_url_2 = top_post_url_2 if top_post_url_2 else ''
        user.top_post_url_3 = top_post_url_3 if top_post_url_3 else ''
        user.sponsored_post_url_1 = sponsored_post_url_1 if sponsored_post_url_1 else ''
        user.sponsored_post_url_2 = sponsored_post_url_2 if sponsored_post_url_2 else ''
        user.sponsored_post_url_3 = sponsored_post_url_3 if sponsored_post_url_3 else ''

        # save user
        db.session.add(user)
        db.session.commit()

        # save to algolia index "influencers"
        index = client.init_index('influencers')
        index.partial_update_object({
            'objectID': user.id,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'fullName': user.first_name + ' ' + user.last_name,
            'imageUrl': user.image_url,
            'city': user.city,
            'bio': user.bio,
            'bookCallInfo': user.calender_url,
            'instagramUsername': user.instagram_username,
            'followersCount': user.followers_count,
            'rate': user.rate,
            'category': user.category,
            'hashtags': user.hashtags,
            'topPostUrl1': user.top_post_url_1,
            'topPostUrl2': user.top_post_url_2,
            'topPostUrl3': user.top_post_url_3,
            'sponsoredPostUrl1': user.sponsored_post_url_1,
            'sponsoredPostUrl2': user.sponsored_post_url_2,
            'sponsoredPostUrl3': user.sponsored_post_url_3,
        })

        response_object = {
            'status': 'success',
            'message': 'Successfully updated.'
        }
        return jsonify(response_object), 201
    else:
        response_object = {
            'status': 'fail',
            'message': 'User not found.'
        }
        return jsonify(response_object), 401

# get influencer profile
@app.route('/influencer-profile', methods=['GET'])
def get_influencer_profile():
    email = request.args.get('email')
    user = InfluencerProfileModel.query.filter_by(email=email).first()

    if user:
        response_object = {
            'code': '200',
            'status': 'success',
            'message': 'User profile found.',
            'data': InfluencerProfileModel.serialize(user)
        }
        return jsonify(response_object), 200
    else:
        response_object = {
            'code': '400',
            'status': 'fail',
            'message': 'User profile not found.',
        }
        return jsonify(response_object), 400

# create brandinfluencerchannelmap
@app.route('/brand-influencer-channel-map', methods=['POST'])
def create_brand_influencer_channel_map():
    post_data = request.get_json()

    brand_email = post_data.get('brandEmail')
    influencer_email = post_data.get('influencerEmail')
    channel_id = post_data.get('channelId')

    print(brand_email, influencer_email, channel_id)

    # check if mapping exists
    mapping = BrandInfluencerChannelMapModel.query.filter_by(brand_email=brand_email, influencer_email=influencer_email, channel_id=channel_id).first()
    
    # if mapping exists, return success, else create mapping
    if mapping:
        response_object = {
            'status': 'success',
            'message': 'Mapping already exists.'
        }
        return jsonify(response_object), 201
    else:
        new_mapping = BrandInfluencerChannelMapModel(
            brand_email=brand_email,
            influencer_email=influencer_email,
            channel_id=channel_id
        )

        # save user
        db.session.add(new_mapping)
        db.session.commit()

        response_object = {
            'status': 'success',
            'message': 'Successfully created.'
        }
        return jsonify(response_object), 201

# get brandinfluencerchannelmap by influencer email and brand email
@app.route('/brand-influencer-channel-map', methods=['GET'])
def get_brand_influencer_channel_map():
    influencer_email = request.args.get('influencerEmail')
    brand_email = request.args.get('brandEmail')

    print(influencer_email, brand_email)
    # influencer_email = "influencer+imran@syncy.net"

    # check if mapping exists
    mapping = BrandInfluencerChannelMapModel.query.filter_by(brand_email=brand_email, influencer_email=influencer_email).first()

    # if mapping exists, return success, else return false
    if mapping:
        response_object = {
            'status': 'success',
            'message': 'Mapping exists.',
            'data': {
                'channelId': mapping.channel_id
            }
        }
        return jsonify(response_object), 201
    else:
        response_object = {
            'status': 'fail',
            'message': 'Mapping does not exist.'
        }
        return jsonify(response_object), 401

# delete brandinfluencerchannelmap by influencer email and brand email
@app.route('/brand-influencer-channel-map', methods=['DELETE'])
def delete_brand_influencer_channel_map():
    influencer_email = request.args.get('influencerEmail')
    brand_email = request.args.get('brandEmail')

    print(influencer_email, brand_email)
    # influencer_email = 

    # check if mapping exists
    mapping = BrandInfluencerChannelMapModel.query.filter_by(brand_email=brand_email, influencer_email=influencer_email).first()

    # if mapping exists, delete mapping, else return false
    if mapping:
        db.session.delete(mapping)
        db.session.commit()

        response_object = {
            'status': 'success',
            'message': 'Mapping deleted.'
        }
        return jsonify(response_object), 201
    else:
        response_object = {
            'status': 'fail',
            'message': 'Mapping does not exist.'
        }
        return jsonify(response_object), 401


# get brandinfluencerchannelmaps by influencer email
@app.route('/brand-influencer-channel-map-by-influencer', methods=['GET'])
def get_brand_influencer_channel_map_by_influencer():
    influencer_email = request.args.get('influencerEmail')

    print(influencer_email)
    # influencer_email = "

    # check if mapping exists
    mappings = BrandInfluencerChannelMapModel.query.filter_by(influencer_email=influencer_email)

    # if mapping exists, return success, else return false
    if mappings:
        response_object = {
            'status': 'success',
            'message': 'Mapping exists.',
            'data': {
                'mappings': BrandInfluencerChannelMapModel.serialize_all(mappings)
            }
        }
        return jsonify(response_object), 201
    else:
        response_object = {
            'status': 'fail',
            'message': 'Mapping does not exist.'
        }
        return jsonify(response_object), 401


# get invites by influencer email
@app.route('/influencer-invites', methods=['GET'])
def get_influencer_invites():
    email = request.args.get('email')
    print(email)

    # check if mapping exists
    mappings = BrandInfluencerChannelMapModel.serialize_all(BrandInfluencerChannelMapModel.query.filter_by(influencer_email=email))

    print("mappings", mappings)

    # if mapping exists, return success, else return false
    if mappings:
        invites = []
        for mapping in mappings:
            brand = BrandUserProfileModel.query.filter_by(email=mapping["brand_email"]).first()
            invite = {
                'brandName': brand.company_name,
                'brandEmail': brand.email,
                'bookCallInfo': brand.book_call_info,
                'channelId': mapping["channel_id"],
                'contactName': brand.first_name + " " + brand.last_name,
                "companyDescription": brand.company_description,
                "companyWebsite": brand.company_website,
                "companyLogo": brand.company_logo,
                "companyAddress": brand.company_address,
            }

            invites.append(invite)

        print("invites", invites)

        response_object = {
            'status': 'success',
            'message': 'Mapping exists.',
            'body': {
                'invites': invites
            }
        }

        return jsonify(response_object), 201
    
    else:
        response_object = {
            'status': 'fail',
            'message': 'Mapping does not exist.'
        }
        return jsonify(response_object), 404


# get brandinfluencerchannelmaps by brand email
@app.route('/brand-influencer-channel-map-by-brand', methods=['GET'])
def get_brand_influencer_channel_map_by_brand():
    brand_email = request.args.get('brandEmail')

    print(brand_email)
    # brand_email = 

    # check if mapping exists
    mappings = BrandInfluencerChannelMapModel.query.filter_by(brand_email=brand_email)

    # if mapping exists, return success, else return false
    if mappings:
        response_object = {
            'status': 'success',
            'message': 'Mapping exists.',
            'data': {
                'mappings': BrandInfluencerChannelMapModel.serialize_all(mappings)
            }
        }
        return jsonify(response_object), 201
    else:
        response_object = {
            'status': 'fail',
            'message': 'Mapping does not exist.'
        }
        return jsonify(response_object), 401


# create new campaign
@app.route('/admin/campaign', methods=['POST'])
def create_campaign():
    post_data = request.get_json()

    name = post_data.get('campaignName')
    email = post_data.get('campaignEmail')
    description = post_data.get('campaignDescription')
    status = post_data.get('campaignStatus')
    type = post_data.get('campaignType')
    logo = post_data.get('campaignLogo')

    print(name, email, description, status, type, logo)

    try:
        campaign = CampaignsModel(
            name=name,
            email=email,
            description=description,
            status=status,
            type=type,
            logo=logo
        )

        db.session.add(campaign)
        db.session.commit()
        
        response_object = {
            'status': 'success',
            'message': 'Successfully created.'
        }
        return jsonify(response_object), 201
    
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.'
        }
        return jsonify(response_object), 401
    
# get all campaigns
@app.route('/admin/campaigns', methods=['GET'])
def get_campaigns():
    campaigns = CampaignsModel.query.all()

    if campaigns:
        response_object = {
            'status': 'success',
            'message': 'Successfully created.',
            'body': {
                'campaigns': CampaignsModel.serialize_all(campaigns)
            }
        }
        return jsonify(response_object), 201
    else:
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.'
        }
        return jsonify(response_object), 401


# create proposal for campaign
@app.route('/campaign/apply', methods=['GET'])
def apply_campaign():
    campaign_id = request.args.get('campaignId')
    influencer_email = request.args.get('email')

    try:
        proposal = CampaignProposalModel(
            campaign_id=campaign_id,
            influencer_email=influencer_email,
            status="pending"
        )

        db.session.add(proposal)
        db.session.commit()
        
        response_object = {
            'status': 'success',
            'message': 'Successfully Applied.'
        }
        return jsonify(response_object), 201
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.'
        }
        return jsonify(response_object), 401

# create new content pack for ContentPacksModel
@app.route('/content-pack/<user_email>', methods=['POST'])
def create_content_pack(user_email):
    post_data = request.get_json()

    title = post_data.get('title')
    description = post_data.get('description')
    platform = post_data.get('platform')
    price = post_data.get('price')
    examples = post_data.get('examples')
    delivery = post_data.get('delivery')

    print(title, description, platform, price, examples, delivery)

    try:
        content_pack = ContentPacksModel(
            title=title,
            description=description,
            platform=platform,
            price=price,
            examples=examples,
            delivery=delivery
        )

        db.session.add(content_pack)
        db.session.commit()

        # create content packs user mapping
        content_pack_user_mapping = ContentPacksUserMapModel(
            contentpack_id=content_pack.id,
            user_email = user_email
        )

        db.session.add(content_pack_user_mapping)
        db.session.commit()
        
        response_object = {
            'status': 'success',
            'message': 'Successfully created.',
            'body': {
                'content_pack': ContentPacksModel.serialize(content_pack)
            }
        }
        return jsonify(response_object), 201
    
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.'
        }
        return jsonify(response_object), 500

# edit content pack for ContentPacksModel
@app.route('/content-pack/<user_email>/<content_pack_id>', methods=['PUT'])
def edit_content_pack(user_email, content_pack_id):
    post_data = request.get_json()

    title = post_data.get('title')
    description = post_data.get('description')
    platform = post_data.get('platform')
    price = post_data.get('price')
    examples = post_data.get('examples')
    delivery = post_data.get('delivery')

    print(title, description, platform, price, examples, delivery)

    try:
        content_pack = ContentPacksModel.query.filter_by(id=content_pack_id).first()

        content_pack.title = title
        content_pack.description = description
        content_pack.platform = platform
        content_pack.price = price
        content_pack.examples = examples
        content_pack.delivery = delivery

        db.session.commit()
        
        response_object = {
            'status': 'success',
            'message': 'Successfully updated.',
            'body': {
                'content_pack': ContentPacksModel.serialize(content_pack)
            }
        }
        return jsonify(response_object), 201
    
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.'
        }
        return jsonify(response_object), 500

# delete content pack for ContentPacksModel
@app.route('/content-pack/<user_email>/<content_pack_id>', methods=['DELETE'])
def delete_content_pack(user_email, content_pack_id):
    try:
        content_pack = ContentPacksModel.query.filter_by(id=content_pack_id).first()
        
        db.session.delete(content_pack)
        db.session.commit()
        
        content_pack_user_map = ContentPacksUserMapModel.query.filter_by(contentpack_id=content_pack_id).first()

        db.session.delete(content_pack_user_map)
        db.session.commit()
        
        response_object = {
            'status': 'success',
            'message': 'Successfully deleted.'
        }
        return jsonify(response_object), 201
    
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.'
        }
        return jsonify(response_object), 500

# get all content packs for an influencer
@app.route('/content-packs/<user_email>', methods=['GET'])
def get_content_packs(user_email):
    content_packs_list = ContentPacksUserMapModel.query.filter_by(user_email=user_email).all()

    print('content_packs_list', content_packs_list)

    content_packs = []
    
    if(len(content_packs_list) == 0):
        response_object = {
            'status': 'success',
            'message': 'No content packs yet.',
            'body': {
                'content_packs': [],
                'length': 0
            }
        }
        return jsonify(response_object), 201

    for c in content_packs_list:
        content_pack = ContentPacksModel.query.filter_by(id=c.contentpack_id).first()
        content_packs.append(content_pack)
    
    print('content_packs', content_packs)

    # print('kk', ContentPacksModel.serialize_all(content_packs))
    
    if content_packs:
        try:
            response_object = {
                'status': 'success',
                'message': 'Successfully fetched.',
                'body': {
                    'content_packs': ContentPacksModel.serialize_all(content_packs),
                    'length': len(content_packs)
                }
            }
            return jsonify(response_object), 201
        except Exception as e:
            print(e)
            response_object = {
                'status': 'fail',
                'message': 'Some error occurred. Please try again.'
            }
            return jsonify(response_object), 500
    else:
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.',
        }
        return jsonify(response_object), 401

# /book-content-pack/${contentPack?.id}
@app.route('/book-content-pack/<contentpack_id>', methods=['POST'])
def book_content_pack(contentpack_id):
    post_data = request.get_json()
    user_email = post_data.get('userEmail')
    details = post_data.get('details')
    content_script = post_data.get('contentScript')
    copy = post_data.get('copy')

    print('contentpack_id', contentpack_id, 'user_email', user_email, 'details', details, 'content_script', content_script, 'copy', copy)

    try:
        new_booking = ContentPackBookingsModel(
            user_email=user_email,
            contentpack_id=contentpack_id,
            details=details,
            script=content_script,
            copy=copy
        )

        db.session.add(new_booking)
        db.session.commit()

        response_object = {
            'status': 'success',
            'message': 'Booking successfully saved.',
            'body': {
                'booking': ContentPackBookingsModel.serialize(new_booking)
            }
        }
        return jsonify(response_object), 201
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': 'Some error occurred. Please try again.'
        }
        return jsonify(response_object), 500

# book-pack-success?booking_id
@app.route('/book-pack-success', methods=['GET'])
def book_pack_success():
    booking_id = request.args.get('booking_id')
    booking = ContentPackBookingsModel.query.filter_by(id=booking_id).first()

    print('booking', booking)

    if booking:
        try:
            booking.status = CONTENT_PACK_BOOKING_STATUS.BOOKED
            booking.save()
            print('book pack status', booking.status)
        except Exception as e:
            print('error', str(e))
    else:
        print('booking not found')

    return redirect('http://localhost:3000/brand/booking/' + booking_id)

# get booking by id
@app.route('/booking/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    booking = ContentPackBookingsModel.query.filter_by(id=booking_id).first()

    print('booking', booking)

    if booking:
        try:
            influencer_email = ContentPacksUserMapModel.query.filter_by(contentpack_id=booking.contentpack_id).first().user_email
            influencer = InfluencerProfileModel.query.filter_by(email=influencer_email).first()
            response_object = {
                'status': 'success',
                'message': 'Successfully fetched.',
                'body': {
                    'booking': {
                        'id': booking.id,
                        'status': booking.status,
                        'user': BrandUserProfileModel.serialize(BrandUserProfileModel.query.filter_by(email=booking.user_email).first()),
                        'contentPack': ContentPacksModel.serialize(ContentPacksModel.query.filter_by(id=booking.contentpack_id).first()),
                        'influencer': InfluencerProfileModel.serialize(influencer),
                        'details': booking.details,
                        'contentScript': booking.script,
                        'copy': booking.copy,
                        'date': booking.date_created
                        }
                }
            }
            return jsonify(response_object), 201
        except Exception as e:
            print(e)
            response_object = {
                'status': 'fail',
                'message': 'Some error occurred. Please try again.'
            }
            return jsonify(response_object), 500
    else:
        response_object = {
            'status': 'fail',
            'message': f'''No booing with id {booking_id} found.'''
        }
        return jsonify(response_object), 404

# get all bookings of a user
# with pagination
@app.route('/bookings/<user_email>', methods=['GET'])
def get_bookings(user_email):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)

    bookings_list = ContentPackBookingsModel.query.filter_by(user_email=user_email).order_by(ContentPackBookingsModel.date_created.desc()).paginate(page=page, per_page=per_page, error_out=False).items

    print('bookings_list', bookings_list)

    bookings = []
    

    if(len(bookings_list) != 0):
        for b in bookings_list:
            influencer_email = ContentPacksUserMapModel.query.filter_by(contentpack_id=b.contentpack_id).first().user_email
            influencer = InfluencerProfileModel.query.filter_by(email=influencer_email).first()
            
            booking = {
                'id': b.id,
                'contentPack': ContentPacksModel.serialize(ContentPacksModel.query.filter_by(id=b.contentpack_id).first()),
                'status': b.status,
                'influencer': InfluencerProfileModel.serialize(influencer),
                'date': b.date_created,
            }

            bookings.append(booking)
    
    print('bookings', bookings)

    response_object = {
        'status': 'success',
        'message': 'Successfully fetched.',
        'body': {
            'bookings': bookings,
            'length': len(bookings)
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": len(bookings),
            "pages": 1
        }
    }

    return jsonify(response_object), 201


# create stream chat token
@app.route('/stream-chat-token', methods=['GET'])
def get_stream_chat_token():
    uid = request.args.get('uid')
    # pip install stream-chat
    import stream_chat

    server_client = stream_chat.StreamChat(api_key="6nrdgtzxm932", api_secret="s8zjf6hfvhsp6wgbeuusmm6uy4rn9vgkjjg2ryqe48fzhc3r2u3u9zf7nzm8uj9h")
    token = server_client.create_token(uid)
    print(token)

    response_object = {
        'status': 'success',
        'message': 'Successfully created.',
        'data': { 
            'token': token
        }
    }
    return jsonify(response_object), 201


# update channel memebers in stream chat
@app.route('/stream-chat-update-channel-members', methods=['GET'])
def update_stream_chat_channel_members():
    channel_id = request.args.get('channelId')
    user_id = request.args.get('userId')
    email = request.args.get('email')

    print(email, user_id, channel_id)

    user = InfluencerProfileModel.query.filter_by(email=email).first()

    print(user)
    # pip install stream-chat
    try:
        import stream_chat
        
        server_client = stream_chat.StreamChat(api_key="6nrdgtzxm932", api_secret="s8zjf6hfvhsp6wgbeuusmm6uy4rn9vgkjjg2ryqe48fzhc3r2u3u9zf7nzm8uj9h")
        channel = server_client.channel('messaging', channel_id)

        print('channel', channel)

        # add members to channel
        channel.add_members([{'user_id': user_id, 'name': user.first_name + ' ' + user.last_name, 'image': user.image_url, 'text':  user.first_name + ' has joined the chat.',}])

        response_object = {
            'status': 'success',
            'message': 'Successfully updated.'
        }
        return jsonify(response_object), 201
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': str(e)
        }
        return jsonify(response_object), 405

# create channel in stream chat with channel name and channel id
@app.route('/stream-chat-create-channel', methods=['GET'])
def create_stream_chat_channel():
    channel_id = request.args.get('channelId')
    channel_name = request.args.get('channelName')
    user_id = request.args.get('userId')
    image_url = request.args.get('imageUrl')
    
    import stream_chat
    server_client = stream_chat.StreamChat(api_key="6nrdgtzxm932", api_secret="s8zjf6hfvhsp6wgbeuusmm6uy4rn9vgkjjg2ryqe48fzhc3r2u3u9zf7nzm8uj9h")

    print(channel_id, channel_name, user_id, image_url)

    # create channel
    channel = server_client.channel('messaging', channel_id, {'name': channel_name, 'image': image_url, 'members': [user_id]})
    # Note: query method creates a channel
    channel.create(user_id)

    print('channel created', channel)

    response_object = {
        'status': 'success',
        'message': 'Successfully created.',
        # "data": {"channel": channel},
    }
    return jsonify(response_object), 201
    

# send message to channel in stream chat
@app.route('/stream-chat-send-message', methods=['POST'])
def send_stream_chat_message():
    post_data = request.get_json()

    channel_id = post_data.get('channelId')
    user_id = post_data.get('userId')
    message = {"text": post_data.get('message')}

    # pip install stream-chat
    import stream_chat
    server_client = stream_chat.StreamChat(api_key="6nrdgtzxm932", api_secret="s8zjf6hfvhsp6wgbeuusmm6uy4rn9vgkjjg2ryqe48fzhc3r2u3u9zf7nzm8uj9h")
    channel = server_client.channel('messaging', channel_id)

    try:
        # send message to channel
        channel.send_message(message, user_id)

        response_object = {
            'status': 'success',
            'message': 'Successfully sent.'
        }
        return jsonify(response_object), 201
    except Exception as e:
        print(e)
        response_object = {
            'status': 'fail',
            'message': str(e)
        }
        return jsonify(response_object), 405


# Create a Checkout Session
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    print('create_checkout_session')
    # get the post data from the request
    post_data = request.get_json()
    booking_id = post_data.get('bookingId')
    user_email = post_data.get('userEmail')
    contentPack = post_data.get('contentPack')
    influencer = post_data.get('influencer')
    details = post_data.get('details')
    contentScript = post_data.get('contentScript')
    copy = post_data.get('copy')
    price = post_data.get('price')
    price = int(price) if price else 0

    # get user from the database by user id
    user = BrandUserProfileModel.query.filter_by(email=user_email).first()
    # print the post data
    print('post_data', post_data)

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': price*100 if price else 5000,
                        'product_data': {
                            'name': contentPack['title'] + ' by ' + influencer['fullName'],
                            "description": contentPack['description'],
                            "images": [influencer['imageUrl']],
                            "metadata": {
                                "bookingId": booking_id,
                                "contentPackId": contentPack['id'],
                                "influencer": str(influencer)[:400],
                                "platform": contentPack['platform'],
                                "delivery": contentPack['delivery'],
                                "name": user.first_name + ' ' + user.last_name,
                                "email" : user.email,
                                "company": user.company_name,
                                # truncate details to 400 characters
                                "details": str(details[:400]),
                                "contentScript": str(contentScript[:400]),
                                "copy": str(copy[:400]),
                            },
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            allow_promotion_codes=True,
            success_url='http://localhost:8000/book-pack-success?booking_id=' + booking_id,
            cancel_url='https://app.syncy.net/brand/discover',
        )
        
        print('checkout_session', checkout_session)
        responseObject = {
            'status': 'success',
            'body': {
                'url': checkout_session.url,
            },
        }
        return make_response(jsonify(responseObject)), 200
    except Exception as e:
        print('error', str(e))
        return str(e)

# api to render a page that calls /all_target_user_profiles and converts json to csv and downloads
@app.route('/download_all_target_user_profiles', methods=['GET'])
def download_all_target_user_profiles():
    return render_template('download_all_target_user_profiles.html') 

if __name__ == '__main__':
    app.run(port=8000, debug=True)
