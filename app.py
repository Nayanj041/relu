from flask import Flask, render_template_string
from supabase import create_client, Client

SUPABASE_URL = "https://vpbjmgwqodhuprpovslh.supabase.co"
SUPABASE_KEY = "sb_publishable_iMCD5saQ85EaP6msbviM2g_XZ9DcV8t"

assert SUPABASE_URL and SUPABASE_KEY, "Supabase env vars missing"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Nike Products - Supabase Catalog</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&family=Space+Grotesk:wght@400;500;600&display=swap" rel="stylesheet" />
    <style>
        :root {
            --ink: #0c0c0f;
            --ink-muted: #4b4d57;
            --surface: #ffffff;
            --surface-muted: #f4f2ee;
            --accent: #f05a28;
            --accent-2: #1b998b;
            --shadow: 0 20px 45px rgba(12, 12, 15, 0.12);
            --radius-lg: 24px;
            --radius-md: 14px;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: "Space Grotesk", sans-serif;
            color: var(--ink);
            background: radial-gradient(1200px 600px at 10% -10%, #ffe7d6, transparent 60%),
                radial-gradient(900px 500px at 90% 10%, #daf7f0, transparent 55%),
                #f9f6f2;
            min-height: 100vh;
        }

        .page {
            max-width: 1400px;
            margin: 0 auto;
            padding: 48px 24px 72px;
        }

        .hero {
            background: var(--surface);
            border-radius: var(--radius-lg);
            padding: 32px 36px;
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
        }

        .hero::before,
        .hero::after {
            content: "";
            position: absolute;
            border-radius: 999px;
            opacity: 0.3;
            z-index: 0;
        }

        .hero::before {
            width: 220px;
            height: 220px;
            background: var(--accent);
            top: -90px;
            right: -80px;
        }

        .hero::after {
            width: 180px;
            height: 180px;
            background: var(--accent-2);
            bottom: -80px;
            left: -40px;
        }

        .hero h1 {
            font-family: "Fraunces", serif;
            font-size: 36px;
            margin: 0 0 8px;
            position: relative;
            z-index: 1;
        }

        .hero p {
            margin: 0;
            color: var(--ink-muted);
            font-size: 16px;
            position: relative;
            z-index: 1;
        }

        .meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-top: 24px;
            position: relative;
            z-index: 1;
        }

        .meta-card {
            background: var(--surface-muted);
            padding: 16px 18px;
            border-radius: var(--radius-md);
        }

        .meta-card strong {
            display: block;
            font-size: 18px;
        }

        .table-wrap {
            margin-top: 32px;
            background: var(--surface);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .table-scroll {
            overflow-x: auto;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            min-width: 1200px;
        }

        thead {
            background: var(--ink);
            color: #fff;
            position: sticky;
            top: 0;
            z-index: 1;
        }

        th, td {
            padding: 12px 14px;
            border-bottom: 1px solid #ece8e2;
            text-align: left;
            vertical-align: top;
            font-size: 14px;
        }

        tbody tr:hover {
            background: #fff7ef;
        }

        .tag {
            display: inline-flex;
            gap: 6px;
            align-items: center;
            padding: 4px 10px;
            border-radius: 999px;
            background: #fff1e6;
            color: #9a3a12;
            font-size: 12px;
            font-weight: 600;
        }

        .thumb {
            width: 72px;
            height: 72px;
            border-radius: 12px;
            object-fit: cover;
            border: 1px solid #f0e8df;
            background: #f7f3ef;
        }

        .link {
            color: var(--accent-2);
            text-decoration: none;
            font-weight: 600;
        }

        .link:hover {
            text-decoration: underline;
        }

        .muted {
            color: var(--ink-muted);
        }

        @media (max-width: 900px) {
            .hero {
                padding: 28px 24px;
            }

            .hero h1 {
                font-size: 28px;
            }

            .meta {
                grid-template-columns: 1fr 1fr;
            }
        }

        @media (max-width: 600px) {
            .meta {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <section class="hero">
            <h1>Nike PH Product Catalog</h1>
            <p>Live table from Supabase. Filter, verify, and export as needed.</p>
            <div class="meta">
                <div class="meta-card">
                    <span class="muted">Records loaded</span>
                    <strong>{{ products|length }}</strong>
                </div>
                <div class="meta-card">
                    <span class="muted">Data source</span>
                    <strong>Supabase</strong>
                </div>
                <div class="meta-card">
                    <span class="muted">Marketplace</span>
                    <strong>Nike PH</strong>
                </div>
            </div>
        </section>

        <section class="table-wrap">
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Image</th>
                            <th>Name</th>
                            <th>Tagging</th>
                            <th>Description</th>
                            <th>Original Price</th>
                            <th>Discount Price</th>
                            <th>Sizes Available</th>
                            <th>Vouchers</th>
                            <th>Available Colors</th>
                            <th>Color Shown</th>
                            <th>Style Code</th>
                            <th>Rating Score</th>
                            <th>Review Count</th>
                            <th>Product URL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr>
                            <td>{{ p.get('id', '') }}</td>
                            <td>
                                {% if p.get('Product_Image_URL') %}
                                <img class="thumb" src="{{ p.get('Product_Image_URL') }}" alt="{{ p.get('Product_Name', '') }}" />
                                {% else %}
                                <div class="thumb"></div>
                                {% endif %}
                            </td>
                            <td>
                                <strong>{{ p.get('Product_Name', '') }}</strong>
                                <div class="muted">{{ p.get('Product_Tagging', '') }}</div>
                            </td>
                            <td>
                                {% if p.get('Product_Tagging') %}
                                <span class="tag">{{ p.get('Product_Tagging') }}</span>
                                {% else %}
                                <span class="muted">-</span>
                                {% endif %}
                            </td>
                            <td>{{ p.get('Product_Description', '') }}</td>
                            <td>{{ p.get('Original_Price', '') }}</td>
                            <td>{{ p.get('Discount_Price', '') }}</td>
                            <td>{{ p.get('Sizes_Available', '') }}</td>
                            <td>{{ p.get('Vouchers', '') }}</td>
                            <td>{{ p.get('Available_Colors', '') }}</td>
                            <td>{{ p.get('Color_Shown', '') }}</td>
                            <td>{{ p.get('Style_Code', '') }}</td>
                            <td>{{ p.get('Rating_Score', '') }}</td>
                            <td>{{ p.get('Review_Count', '') }}</td>
                            <td>
                                {% if p.get('Product_URL') %}
                                <a class="link" href="{{ p.get('Product_URL') }}" target="_blank" rel="noopener">Open</a>
                                {% else %}
                                <span class="muted">-</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </section>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    data = supabase.table("products").select("*").execute()
    products = data.data
    return render_template_string(HTML_TEMPLATE, products=products)


if __name__ == "__main__":
    app.run(debug=True)
                                                                                                                                                                                                            
