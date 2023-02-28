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
# stripe.api_key = 'sk_test_51JMNGMBC2Ls8FQJScwZbebJ4QxAU4XIEpf7tHIQ6b2gOJ8piskUX5WAWi6TfKrMiTmv6pHuJr1rFQsgwdPeEmHjo00h9RzLUTz'

# This is your live secret API key.
stripe.api_key = os.environ.get("STRIPE_LIVE_SECRET_KEY")

db = SQLAlchemy(app)
migrate = Migrate(app, db, compare_type=True)

from algoliasearch.search_client import SearchClient
# # API keys below contain actual values tied to your Algolia account
client = SearchClient.create('L7PFECEWC3', 'e03caa75dd335df7a8fefb1f0e3b6e27')
# index = client.init_index('syncy')


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


@app.route('/', methods=['POST', 'GET'])
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

    # check if user exists

    user = BrandUserProfileModel.query.filter_by(email=email).first()
    
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
            company_description=company_description
        )

        # save user
        db.session.add(new_user)
        db.session.commit()

        response_object = {
            'status': 'success',
            'message': 'Successfully registered.'
        }
        return jsonify(response_object), 201

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
    rate = post_data.get('rate')
    rate = int(rate) if rate else 0

    # get user from the database by user id
    user = TargetUserProfileModel.query.filter_by(id=user_id).first()
    # print the post data
    print('post_data', post_data)

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': rate*100 if rate and rate!=25 else 2500,
                        'product_data': {
                            'name': 'Syncy 30 minute call with ' + name,
                            "description": "Please complete payment in order to confirm your Sync. Send questions or feedback to help@syncy.net.",
                            "images": [profile_image_url],
                            "metadata": {
                                "name": name,
                                "email" : email,
                                "linkedin": linkedin_url,
                                # truncate bio to 400 characters
                                "bio": bio[:400],
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
            success_url=user.calendly_url,
            cancel_url=YOUR_DOMAIN,
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

# return all target user profiles
@app.route('/all_target_user_profiles', methods=['GET'])
def get_all_target_user_profiles():
    target_user_profiles = TargetUserProfileModel.query.all()
    target_user_profiles_dict = TargetUserProfileModel.serialize_all(target_user_profiles)
    # responseObject = {
    #     'status': 'success',
    #     'data': {
    #         'target_user_profiles': target_user_profiles_dict,
    #     },
    # }
    return make_response(jsonify(target_user_profiles_dict)), 200

# api to render a page that calls /all_target_user_profiles and converts json to csv and downloads
@app.route('/download_all_target_user_profiles', methods=['GET'])
def download_all_target_user_profiles():
    return render_template('download_all_target_user_profiles.html') 

if __name__ == '__main__':
    app.run(port=8000, debug=True)
