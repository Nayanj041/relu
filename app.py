from flask import Flask, render_template_string
from supabase import create_client, Client

SUPABASE_URL = "https://vpbjmgwqodhuprpovslh.supabase.co"
SUPABASE_KEY = "sb_publishable_iMCD5saQ85EaP6msbviM2g_XZ9DcV8t"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Nike Products</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { padding: 8px; border: 1px solid #ddd; }
        th { background: #111; color: white; }
    </style>
</head>
<body>
    <h2>Nike Scraped Products</h2>
    <table>
        <tr>
            <th>Name</th>
            <th>Discount Price</th>
            <th>Rating</th>
            <th>Reviews</th>
        </tr>
        {% for p in products %}
        <tr>
            <td>{{ p['product_name'] }}</td>
            <td>{{ p['discount_price'] }}</td>
            <td>{{ p['rating_score'] }}</td>
            <td>{{ p['review_count'] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/")
def home():
    data = supabase.table("products").select("*").limit(100).execute()
    products = data.data
    return render_template_string(HTML_TEMPLATE, products=products)

if __name__ == "__main__":
    app.run(debug=True)
