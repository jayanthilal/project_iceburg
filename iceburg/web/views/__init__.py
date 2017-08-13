from __future__ import division

import decimal
import logging
from multiprocessing.dummy import Pool as ThreadPool

import arrow
import pandas as pd
import requests
from flask import render_template, Blueprint, jsonify, current_app, flash, session
from pandas.io.json import json_normalize

from iceburg.web.config import Config
from iceburg.web.views.travelplan import TravelPlanForm

LOGGER = logging.getLogger(__name__)

app = Blueprint('web', __name__)

CATEGORY_FRAME = pd.DataFrame(data = {
    'detail_description': ['BT',
        'Bar',
        'Booking.com',
        'Business Rates',
        'Car Servicing',
        'Cash Withdrawals',
        'Cash withdrawal',
        'Cinema',
        'Coffee',
        'Council Tax',
        'Estate Agent',
        'Filling Station',
        'Filling station',
        'Flights',
        'Florist',
        'Gas/Elec',
        'Income',
        'London arttraction',
        'Mobile',
        'Mobile phone',
        'Monthly Golf membership',
        'Monthly Netflix Membership',
        'Paid in',
        'Parking',
        'Rent',
        'Resaurant',
        'Restaurant',
        'Restaurant/Takeway',
        'Restaurants',
        'Salary',
        'Saving',
        'Savings',
        'Shopping',
        'Spa',
        'Takeaway',
        'Telephone',
        'Tickets',
        'Transfer',
        'Water'
    ],
    'custom_category': [
        'Misc',
        'Leisure and Entertainment',
        'Travel',
        'Bills',
        'Bills',
        'Misc',
        'Misc',
        'Leisure and Entertainment',
        'Leisure and Entertainment',
        'Bills',
        'Misc',
        'Transport',
        'Transport',
        'Travel',
        'Misc',
        'Bills',
        'Misc',
        'Travel',
        'Bills',
        'Bills',
        'Leisure and Entertainment',
        'Leisure and Entertainment',
        'Misc',
        'Transport',
        'Bills',
        'Leisure and Entertainment',
        'Leisure and Entertainment',
        'Leisure and Entertainment',
        'Leisure and Entertainment',
        'Misc',
        'Misc',
        'Misc',
        'Groceries and shopping',
        'Leisure and Entertainment',
        'Leisure and Entertainment',
        'Bills',
        'Leisure and Entertainment',
        'Misc',
        'Bills'
    ]
})


def trans_to_obj(item):
    return({
        'spend_type' : item['other_account']['metadata']['more_info'],
        'amount' : decimal.Decimal(item['details']['value']['amount']),
        'new_balance' : decimal.Decimal(item['details']['new_balance']['amount']),
        'detail_description' : item['details']['description'],
        'date' : item['details']['completed']
        })


@app.route('/login')
def login():
    return render_template('login.html', api_url=Config.API_URL)

@app.route('/home')
def home():
    return render_template('home.html', api_url=Config.API_URL)

g_session = None


@app.route('/')
def index():
    global g_session

    goals = {'debits': 0, 'credits': 0}

    # get the token if not in session
    if not session.get('token'):
        login_result = requests.post(
            'https://apc.openbankproject.com/my/logins/direct',
            headers={'Authorization': 'DirectLogin username="Robert.Anz.01", password="X!f98b6237", consumer_key="n4giy0finiahltld12sfaq0c3wwak5qvpccpyojt"'}
        )
        if login_result.status_code == 200:
            session['token'] = login_result.json()['token']
            print(session['token'])
        else:
            flash('Unable to get access token {}'.format(login_result.status_code))
            return render_template('index.html', api_url=Config.API_URL, transactions={}, goals=goals)

    g_session = session['token']

    # Get the customers accounts
    get_accounts_response = requests.get(
        '{}/my/accounts'.format(current_app.config['API_URL']),
        headers={'Authorization': 'DirectLogin token="{}"'.format(session['token'])}
    )

    if get_accounts_response.status_code != 200:
        flash('Bad response from get accounts {}'.format(get_accounts_response.status_code))
        return render_template('index.html', api_url=Config.API_URL, transactions={}, goals=goals)

    # Example list of accounts
    # [{
    #   "id":"42b530a5-75d0-4249-8243-7e9c5e519ed6",
    #   "label":"Robert.Anz.01 M35 11..258",
    #   "bank_id":"au.01.aum.anz",
    #   "account_routing":{
    #     "scheme":"OBP",
    #     "address":"42b530a5-75d0-4249-8243-7e9c5e519ed6"
    #   }
    # }]

    accounts = get_accounts_response.json()

    #

    # now get the transactions
    transaction_urls = ['/banks/{bank_id}/accounts/{account_id}/owner/transactions'.format(
            bank_id=account['bank_id'], account_id=account['id']
        ) for account in accounts]

    # Make the pool of workers
    # global transaction_results
    pool = ThreadPool(3)
    transaction_results = pool.imap_unordered(get_transactions, transaction_urls)

    # transaction_results = []
    # for account in accounts:
    #     get_transactions_url = '/banks/{bank_id}/accounts/{account_id}/owner/transactions'.format(
    #         bank_id=account['bank_id'], account_id=account['id']
    #     )
    #     get_transactions_response = requests.get(
    #         '{}{url}'.format(current_app.config['API_URL'], url=get_transactions_url),
    #         headers={'Authorization': 'DirectLogin token="{}"'.format(session['token'])}
    #     )
    #     if get_accounts_response.status_code != 200:
    #         flash('Unable to retrieve transactions for account {}'.format(account['id']))
    #     else:
    #         transaction_results.append(get_transactions_response.json())

    # Example transaction data
    # {
    # "transactions": [{
    #     "id": "e6077987-7935-4bc7-9eb4-dae43d146274",
    #     "this_account": {
    #         "id": "42b530a5-75d0-4249-8243-7e9c5e519ed6",
    #         "bank_routing": {
    #             "scheme": "OBP",
    #             "address": "42b530a5-75d0-4249-8243-7e9c5e519ed6"
    #         },
    #         "account_routing": {
    #             "scheme": "OBP",
    #             "address": "42b530a5-75d0-4249-8243-7e9c5e519ed6"
    #         },
    #         "holders": [{
    #             "name": "Robert.Anz.01",
    #             "is_alias": false
    #         }],
    #         "kind": "CURRENT PLUS"
    #     },
    #     "other_account": {
    #         "id": "1c7e4e0c-36e0-4cd8-92ff-f7fca7420a40",
    #         "bank_routing": {
    #             "scheme": null,
    #             "address": null
    #         },
    #         "account_routing": {
    #             "scheme": null,
    #             "address": null
    #         },
    #         "kind": null,
    #         "metadata": {
    #             "public_alias": "ALIAS_B8BD43",
    #             "private_alias": null,
    #             "more_info": "Savings",
    #             "URL": "http://www.nab.com.au",
    #             "image_URL": "https://www.carloanworld.com.au/wp-content/uploads/2013/12/nab_logo.gif",
    #             "open_corporates_URL": null,
    #             "corporate_location": null,
    #             "physical_location": null
    #         }
    #     },
    #     "details": {
    #         "type": "10219",
    #         "description": "Savings",
    #         "posted": "2015-12-30T11:02:17Z",
    #         "completed": "2015-12-30T11:02:17Z",
    #         "new_balance": {
    #             "currency": "AUD",
    #             "amount": "16560.99"
    #         },
    #         "value": {
    #             "currency": "AUD",
    #             "amount": "-408.88"
    #         }
    #     },
    #     "metadata": {
    #         "narrative": null,
    #         "comments": [],
    #         "tags": [],
    #         "images": [],
    #         "where": null
    #     }
    # }

    # aggregate the transaction history for all accounts
    transactions = []
    for transaction_result in transaction_results:
        for transaction in transaction_result['transactions']:
            transactions.append(transaction)

    transaction_list = list()
    for item in transactions:
        transaction_list.append(trans_to_obj(item))

    transactions_df = json_normalize(transaction_list)
    # at this point we have a pandas dataframe in transactions_df
    # columns:
    #   spend_type: string
    #   amount: decimal
    #   detail_description: string
    #   date: datetime
    #   new_balance: decimal

    spend_summary = transactions_df[transactions_df['amount'] < 0]\
        .groupby(['detail_description'])['amount']\
        .sum().reset_index()

    spend_summary_recoded = spend_summary.merge(CATEGORY_FRAME, how = 'left', on = 'detail_description')\
      .fillna('Misc')\
      .groupby(['custom_category'])['amount']\
      .sum()


    credits = transactions_df[transactions_df['amount'] > 0]['amount'].sum()
    debits = transactions_df[transactions_df['amount'] < 0]['amount'].sum()
    goals = {'debits': round(debits,0), 'credits': round(credits,0)}
    return render_template('index.html', api_url=Config.API_URL, transactions = spend_summary_recoded.to_dict(), goals=goals)


def get_transactions(url):
    # global transaction_results
    print('{}{url}'.format('https://apc.openbankproject.com/obp/v3.0.0', url=url))
    get_transactions_response = requests.get(
        '{}{url}'.format('https://apc.openbankproject.com/obp/v3.0.0', url=url),
        headers={'Authorization': 'DirectLogin token="{}"'.format(g_session)}
    )
    if get_transactions_response.status_code == 200:
        return get_transactions_response.json()
    else:
        return {}


@app.route('/api/holiday_cost/<destination>/<rating>/<days>', methods=['GET'])
def api_holiday_cost_get(destination, rating, days):

    holiday_destination = {
        'Australia': (180, 330, 800),
        'Austria': (160, 440, 1200),
        'Bahamas': (180, 330, 3000),
        'United Kingdom': (88, 170, 2000),
        'United States': (45, 160, 1200),
        'Japan': (120, 330, 800),
    }

    if not holiday_destination.get(destination):
        return jsonify({'message': 'Unable to load location'}), 404
    rating = int(rating) - 1
    if rating > 2 or rating < 0:
        return jsonify({'message': 'Bad accom rating'}), 404
    days = int(days)

    return jsonify(
        {
            'cost': days * holiday_destination[destination][rating],
            'destination': destination,
            'rating': rating + 1,
            'days': days,
        }
    )


@app.route('/api/how_long_now/<cost>/<net_per_year>', methods=['GET'])
def api_goal_target_date_get(cost, net_per_year):
    cost = decimal.Decimal(cost)
    net_per_year = decimal.Decimal(net_per_year)

    return jsonify({'how_long_now': get_readable_duration(cost, net_per_year)})


def get_readable_duration(cost, net_per_year):
    days_to_save = int((cost/net_per_year) * 365)
    target_date = arrow.utcnow().shift(days=days_to_save)
    return target_date.humanize()


@app.route('/travelplans', methods=['GET', 'PUT'])
def travel_plan():
    form = TravelPlanForm()
    return render_template('travelplan.html', form=form)
