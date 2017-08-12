import collections
import decimal
import logging
import pprint
from multiprocessing.dummy import Pool as ThreadPool

from flask import render_template, Blueprint, jsonify, request, Response, current_app, flash, session
import requests

from iceburg.web.config import Config

LOGGER = logging.getLogger(__name__)

app = Blueprint('web', __name__)

@app.route('/login')
def login():
    return render_template('login.html', api_url=Config.API_URL)

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

    for transaction in transactions:
        if not transaction['details'].get('description'):
            pprint.pprint(transaction)

    # summarise the transaction by 'details.description' tag..
    count = collections.defaultdict(decimal.Decimal)
    for item in transactions:
        # count[item['other_account']['metadata']['more_info']] += decimal.Decimal(item['details']['value']['amount'])
        count[item['details']['description']] += decimal.Decimal(item['details']['value']['amount'])
    tran_summary = dict(count)
    print(tran_summary)

    # Work out current savings
    credits = sum([int(tran_summary[tran]*100) for tran in tran_summary if tran_summary[tran] > 0])
    print(credits)
    debits = sum([int(tran_summary[tran]*100) for tran in tran_summary if tran_summary[tran] <= 0])
    print(debits)
    goals = {'debits': debits/100, 'credits': credits/100}

    # OK, time to aggregate the categories into the following broad sections..
    # TODO - Brads's working on this..

    return render_template('index.html', api_url=Config.API_URL, transactions=tran_summary, goals=goals)


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
