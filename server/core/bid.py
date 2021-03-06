from flask import Blueprint, g, make_response, abort, request
from core.permission import auth
from core.notification import send_bid_response_notification
import json

bid = Blueprint("bid", __name__)

@bid.route('/bid', methods=['GET'])
@auth.login_required
def get_my_bids():
    cur = g.db.cursor()
    cur.execute("SELECT Bid.BidId, Bid.ProductId, Bid.Price, Bid.Status, \
        unix_timestamp(Bid.CreateAt), Product.Name, Product.Price, Product.UserId, \
        User.Nickname, (SELECT COUNT(*) FROM Review WHERE Review.BidId = Bid.BidId) FROM Bid, Product, User WHERE Bid.ProductId = Product.ProductId \
        AND Bid.UserId = %s AND User.UserId = Product.UserId", (str(g.user_id),))
    bids_data = cur.fetchall()

    my_bids = []
    for bid_data in bids_data:
        my_bids.append({
            "bid_id": bid_data[0],
            "price": bid_data[2],
            "status": bid_data[3],
            "timestamp": bid_data[4],
            "is_reviewed": bid_data[9],
            "product": {
                "id": bid_data[1],
                "name": bid_data[5],
                "price": bid_data[6],
                "seller_user_id": bid_data[7],
                "seller_nickname": bid_data[8]
            }
        })

    cur.execute("SELECT Bid.BidId, Bid.UserId, Bid.ProductId, Bid.Price, Bid.Status, \
        unix_timestamp(Bid.CreateAt), Product.Name, Product.Price, User.Nickname FROM Bid, Product, User \
        WHERE Bid.ProductId = Product.ProductId AND Product.UserId = %s \
        AND User.UserId = Bid.UserId", (str(g.user_id),))
    sells_data = cur.fetchall()

    my_sells = []
    for sell_data in sells_data:
        my_sells.append({
            "bid_id": sell_data[0],
            "price": sell_data[3],
            "status": sell_data[4],
            "timestamp": sell_data[5],
            "product": {
                "id": sell_data[2],
                "name": sell_data[6],
                "price": sell_data[7]
            },
            "bidder": {
                "user_id": sell_data[1],
                "nickname": sell_data[8]
            }
        })

    resp_body = {
        "bids": my_bids,
        "sells": my_sells
    }

    resp = make_response(json.dumps(resp_body), 200)
    resp.headers["Content-Type"] = "application/json"
    return resp

@bid.route('/bid/<int:bid_id>', methods=['PUT'])
@auth.login_required
def respond_bid_request(bid_id):
    req_body = json.loads(request.data)
    cur = g.db.cursor()
    cur.execute("SELECT Bid.BidId, Bid.Status, Bid.UserId, Product.UserId FROM Bid, Product \
        WHERE Bid.BidId = %s AND Bid.ProductId = Product.ProductId", (str(bid_id),))
    bid_data = cur.fetchone()

    if bid_data is None:
        abort(404)

    if bid_data[3] != g.user_id:
        abort(403)

    new_status = "accepted" if req_body["accept"] == 1 else "rejected"

    cur.execute("UPDATE Bid SET Status = %s WHERE BidId = %s", (new_status, 
        str(bid_id)))

    send_bid_response_notification(bid_data[3], bid_data[2], bid_data[0], new_status)

    g.db.commit()

    return '', 200

@bid.route('/bid/<int:bid_id>', methods=['DELETE'])
@auth.login_required
def delete_bid(bid_id):
    cur = g.db.cursor()
    cur.execute("SELECT Bid.BidId, Bid.UserId FROM Bid \
        WHERE Bid.BidId = %s AND Bid.Status = 'new'", (str(bid_id),))
    bid_data = cur.fetchone()

    if bid_data is None:
        abort(404)

    if bid_data[1] != g.user_id:
        abort(403)

    cur.execute("DELETE FROM Bid WHERE BidId = %s", (str(bid_id),))

    g.db.commit()

    return '', 200
