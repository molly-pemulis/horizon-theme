#!/usr/bin/env python3
"""
Generate product-metafields.liquid from Shopify metafield definitions.
Run by GitHub Action hourly, or manually.
"""
import requests
import os
from datetime import datetime

SHOP_URL = "7aa0b1-14.myshopify.com"
API_VERSION = "2024-01"
ACCESS_TOKEN = os.environ.get('SHOPIFY_ADMIN_TOKEN')
THEME_FILE = "blocks/product-metafields.liquid"

INCLUDE_NAMESPACES = ['custom', 'gato_heroi', 'reviews', 'descriptors']
EXCLUDE_KEYS = ['rating_value', 'review_count', 'rating', 'rating_count']

if not ACCESS_TOKEN:
    print("No SHOPIFY_ADMIN_TOKEN set, skipping")
    exit(0)

url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
query = """
{
  metafieldDefinitions(ownerType: PRODUCT, first: 100) {
    edges {
      node {
        namespace
        key
        name
        type { name }
      }
    }
  }
}
"""

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

response = requests.post(url, json={"query": query}, headers=headers)

if response.status_code != 200:
    print(f"API error: {response.status_code}")
    exit(1)

data = response.json()
edges = data.get('data', {}).get('metafieldDefinitions', {}).get('edges', [])

if not edges:
    print("No metafield definitions found")
    exit(0)

fields = []
for e in edges:
    node = e['node']
    ns = node['namespace']
    key = node['key']
    if ns in INCLUDE_NAMESPACES and key not in EXCLUDE_KEYS:
        fields.append({
            'namespace': ns,
            'key': key,
            'name': node['name'],
            'type': node['type']['name']
        })

print(f"Found {len(fields)} metafield definitions to include")

field_blocks = []
for f in fields:
    ns = f['namespace']
    key = f['key']
    name = f['name']
    ftype = f['type']
    
    if ftype == 'url':
        value_output = '<a href="{{ product.metafields.' + ns + '.' + key + '.value }}" target="_blank">View Guide</a>'
    elif ftype == 'multi_line_text_field':
        value_output = '{{ product.metafields.' + ns + '.' + key + '.value | newline_to_br }}'
    else:
        value_output = '{{ product.metafields.' + ns + '.' + key + '.value }}'
    
    block = '    {% if product.metafields.' + ns + '.' + key + '.value != blank %}\n'
    block += '      <div class="product-metafields__item">\n'
    block += '        <dt class="product-metafields__label">' + name + '</dt>\n'
    block += '        <dd class="product-metafields__value">' + value_output + '</dd>\n'
    block += '      </div>\n'
    block += '    {% endif %}'
    field_blocks.append(block)

fields_html = '\n'.join(field_blocks)
timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
namespaces_str = ', '.join(INCLUDE_NAMESPACES)

liquid = '''{% comment %}
  PRODUCT METAFIELDS - AUTO-GENERATED
  ====================================
  Generated: ''' + timestamp + '''
  Fields: ''' + str(len(fields)) + '''
  Namespaces: ''' + namespaces_str + '''
  
  DO NOT EDIT - This file is auto-generated from Shopify metafield definitions.
{% endcomment %}

{% liquid
  assign product = closest.product
  if product == blank and request.visual_preview_mode
    assign product = collections.all.products.first
  endif
%}

<div class="product-metafields" {{ block.shopify_attributes }}>
  {% if block.settings.show_heading and block.settings.heading != blank %}
    <h3 class="product-metafields__heading {{ block.settings.heading_size }}">
      {{ block.settings.heading }}
    </h3>
  {% endif %}
  
  <dl class="product-metafields__list">
''' + fields_html + '''
  </dl>
</div>

{% stylesheet %}
  .product-metafields { width: 100%; }
  .product-metafields__heading { margin-bottom: var(--margin-sm); }
  .product-metafields__list { display: grid; gap: var(--gap-xs); margin: 0; }
  .product-metafields__item {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--gap-md);
    padding: var(--padding-xs) 0;
    border-bottom: 1px solid rgb(var(--color-foreground-rgb) / var(--opacity-10));
  }
  .product-metafields__item:last-child { border-bottom: none; }
  .product-metafields__label {
    font-weight: var(--font-weight-semibold);
    color: rgb(var(--color-foreground-rgb) / var(--opacity-70));
    flex-shrink: 0;
  }
  .product-metafields__value { margin: 0; text-align: right; max-width: 65%; }
  .product-metafields__value a { color: var(--color-primary); text-decoration: underline; }
{% endstylesheet %}

{% schema %}
{
  "name": "Product specs",
  "tag": null,
  "settings": [
    { "type": "paragraph", "content": "Auto-generated from Shopify metafields." },
    { "type": "checkbox", "id": "show_heading", "label": "Show heading", "default": true },
    { "type": "text", "id": "heading", "label": "Heading", "default": "Specifications" },
    { "type": "select", "id": "heading_size", "label": "Heading size", "options": [
      { "value": "h4", "label": "Small" },
      { "value": "h3", "label": "Medium" },
      { "value": "h2", "label": "Large" }
    ], "default": "h4" },
    { "type": "range", "id": "padding-block-start", "label": "Top padding", "min": 0, "max": 100, "step": 1, "unit": "px", "default": 16 },
    { "type": "range", "id": "padding-block-end", "label": "Bottom padding", "min": 0, "max": 100, "step": 1, "unit": "px", "default": 16 }
  ],
  "presets": [{ "name": "Product specs", "category": "Product" }]
}
{% endschema %}'''

with open(THEME_FILE, 'w') as f:
    f.write(liquid)

print(f"Generated {THEME_FILE}")
