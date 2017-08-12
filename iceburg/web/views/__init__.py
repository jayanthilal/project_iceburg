import collections
import decimal
import logging

from flask import render_template, Blueprint, jsonify, request, Response, current_app, flash
import requests

from iceburg.web.config import Config

LOGGER = logging.getLogger(__name__)

app = Blueprint('web', __name__)


@app.route('/')
def index():
    login_result = requests.post(
        'https://apc.openbankproject.com/my/logins/direct',
        headers={'Authorization': 'DirectLogin username="Robert.Anz.01", password="X!f98b6237", consumer_key="n4giy0finiahltld12sfaq0c3wwak5qvpccpyojt"'}
    )
    if login_result.status_code == 200:
        token = login_result.json()['token']
        print(token)
    else:
        flash(login_result.json())
        render_template('index.html', api_url=Config.API_URL)
        return

    get_accounts_response = requests.get(
        '{}/my/accounts'.format(current_app.config['API_URL']),
        headers={'Authorization': 'DirectLogin token="{}"'.format(token)}
    )
    # Example list of accounts
    # [{
    #   "id":"42b530a5-75d0-4249-8243-7e9c5e519ed6",
    #   "label":"Robert.Anz.01 M35 11..258",
    #   "bank_id":"au.01.aum.anz",
    #   "account_routing":{
    #     "scheme":"OBP",
    #     "address":"42b530a5-75d0-4249-8243-7e9c5e519ed6"
    #   }
    # }
    accounts = get_accounts_response.json()
    transaction_results = []

    for account in accounts:
        get_transactions_url = '/banks/{bank_id}/accounts/{account_id}/owner/transactions'.format(
            bank_id=account['bank_id'], account_id=account['id']
        )
        get_transactions_response = requests.get(
            '{}{url}'.format(current_app.config['API_URL'], url=get_transactions_url),
            headers={'Authorization': 'DirectLogin token="{}"'.format(token)}
        )
        transaction_results.append(get_transactions_response.json())
        # print(get_transactions_response.json())

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

    # aggregate the transaction history..
    transactions = []
    for transaction_result in transaction_results:
        for transaction in transaction_result['transactions']:
            transactions.append(transaction)

    # summarise the costs..
    count = collections.defaultdict(decimal.Decimal)
    for item in transactions:
        count[item['other_account']['metadata']['more_info']] += decimal.Decimal(item['details']['value']['amount'])
    tran_summary = dict(count)
    print(tran_summary)

    return render_template('index.html', api_url=Config.API_URL, transactions=tran_summary)
